import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.catalog import ProductVariant
from app.models.engagement import Review
from app.models.order import Order, OrderItem, OrderStatus
from app.schemas.schemas import ReviewCreate, ReviewOut
from app.tasks.tasks import generate_review_sentiment_summary

router = APIRouter(tags=["Reseñas"])


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: ReviewCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Review:
    if payload.order_item_id:
        order_item = await db.get(OrderItem, payload.order_item_id)
        if not order_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ítem de pedido no encontrado")

        variant = await db.get(ProductVariant, order_item.variant_id)
        if not variant or variant.product_id != payload.product_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El ítem de pedido no coincide con el producto")
    else:
        order_item = None

    if order_item:
        order = await db.get(Order, order_item.order_id)
        if not order or order.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a este pedido")
        if order.status != OrderStatus.DELIVERED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden registrar reseñas de pedidos entregados",
            )
        existing = await db.execute(select(Review).where(Review.order_item_id == payload.order_item_id))
        if existing.scalars().first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una reseña para este ítem")
    else:
        items = await db.execute(
            select(OrderItem)
            .join(ProductVariant, ProductVariant.id == OrderItem.variant_id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.user_id == user.id,
                Order.status == OrderStatus.DELIVERED,
                ProductVariant.product_id == payload.product_id,
            )
            .order_by(OrderItem.id)
        )
        candidate = items.scalars().first()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se encontró un pedido entregado para este producto",
            )
        reviewed = await db.execute(select(Review).where(Review.order_item_id == candidate.id))
        if reviewed.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una reseña para este producto en este pedido entregado",
            )
        order_item = candidate

    variant = await db.get(ProductVariant, order_item.variant_id)
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variante de producto no encontrada")

    review = Review(
        product_id=variant.product_id,
        user_id=user.id,
        order_item_id=order_item.id,
        rating=payload.rating,
        title=payload.title,
        comment=payload.comment,
        is_verified_purchase=True,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    generate_review_sentiment_summary.delay(str(review.id))
    return review


@router.get("/products/{product_id}", response_model=list[ReviewOut])
async def list_product_reviews(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[Review]:
    result = await db.execute(
        select(Review).where(Review.product_id == product_id).order_by(Review.created_at.desc())
    )
    return result.scalars().all()
