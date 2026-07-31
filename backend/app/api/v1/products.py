import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_seller
from app.core.database import get_db
from app.models.catalog import Category, Product, ProductStatus, ProductVariant
from app.models.user import SellerProfile, User
from app.schemas.schemas import CategoryOut, ProductCreate, ProductOut
from app.tasks.tasks import index_product_in_search

router = APIRouter(tags=["Catálogo"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return f"{text}-{uuid.uuid4().hex[:8]}"


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.is_active.is_(True)))
    return result.scalars().all()


@router.get("/products", response_model=list[ProductOut])
async def list_products(
    category_id: uuid.UUID | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    q: str | None = Query(default=None, description="Búsqueda de texto en título/descripción"),
    sort: str = Query(
        default="relevance",
        pattern="^(relevance|rating|newest|price_asc|price_desc)$",
        description=(
            "Orden del listado: relevance (por defecto), rating (mejor valorados, "
            "para carruseles de 'más vendidos'), newest (recién publicados), "
            "price_asc, price_desc."
        ),
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Product)
        .where(Product.status == ProductStatus.ACTIVE)
        .options(selectinload(Product.variants), selectinload(Product.images))
    )
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if q:
        stmt = stmt.where(Product.title.ilike(f"%{q}%"))

    if sort == "rating":
        stmt = stmt.order_by(Product.rating_average.desc(), Product.rating_count.desc())
    elif sort == "newest":
        stmt = stmt.order_by(Product.created_at.desc())

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    products = result.scalars().all()

    if sort in ("price_asc", "price_desc"):
        def _min_price(p: Product) -> float:
            prices = [float(v.price) for v in p.variants]
            return min(prices) if prices else float("inf")

        products = sorted(products, key=_min_price, reverse=(sort == "price_desc"))

    if min_price is not None:
        products = [p for p in products if any(float(v.price) >= min_price for v in p.variants)]
    if max_price is not None:
        products = [p for p in products if any(float(v.price) <= max_price for v in p.variants)]

    return products


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.variants), selectinload(Product.images))
    )
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return product


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    user: User = Depends(require_seller),
    db: AsyncSession = Depends(get_db),
):
    seller_result = await db.execute(select(SellerProfile).where(SellerProfile.user_id == user.id))
    seller = seller_result.scalar_one_or_none()
    if not seller:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El usuario no tiene perfil de vendedor activo")
    if not seller.is_approved:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El perfil de vendedor está pendiente de aprobación")

    category = await db.get(Category, payload.category_id)
    if not category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")

    product = Product(
        seller_id=seller.id,
        category_id=payload.category_id,
        title=payload.title,
        slug=slugify(payload.title),
        description=payload.description,
        brand=payload.brand,
        tags=payload.tags,
        attributes=payload.attributes,
        status=ProductStatus.ACTIVE,
    )
    db.add(product)
    await db.flush()

    for v in payload.variants:
        db.add(ProductVariant(product_id=product.id, **v.model_dump()))

    await db.commit()

    stmt = (
        select(Product)
        .where(Product.id == product.id)
        .options(selectinload(Product.variants), selectinload(Product.images))
    )
    result = await db.execute(stmt)
    product = result.scalar_one()

    # Indexación asíncrona en Elasticsearch — no bloquea la respuesta HTTP
    index_product_in_search.delay(str(product.id))

    return product


@router.patch("/products/{product_id}/status")
async def update_product_status(
    product_id: uuid.UUID,
    new_status: ProductStatus,
    user: User = Depends(require_seller),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    product.status = new_status
    await db.commit()
    index_product_in_search.delay(str(product.id))
    return {"id": str(product.id), "status": product.status.value}
