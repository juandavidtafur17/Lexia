import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.catalog import ProductVariant
from app.models.order import Cart, CartItem
from app.models.user import User
from app.schemas.schemas import CartItemCreate, CartItemOut

router = APIRouter(prefix="/cart", tags=["Carrito"])


async def _get_or_create_cart(user_id: uuid.UUID, db: AsyncSession) -> Cart:
    result = await db.execute(select(Cart).where(Cart.user_id == user_id))
    cart = result.scalar_one_or_none()
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.flush()
    return cart


@router.get("", response_model=list[CartItemOut])
async def get_cart(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cart = await _get_or_create_cart(user.id, db)
    result = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
    return result.scalars().all()


@router.post("/items", response_model=CartItemOut, status_code=status.HTTP_201_CREATED)
async def add_item(
    payload: CartItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    variant = await db.get(ProductVariant, payload.variant_id)
    if not variant or not variant.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante de producto no disponible")

    cart = await _get_or_create_cart(user.id, db)

    result = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.variant_id == payload.variant_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.quantity += payload.quantity
        await db.commit()
        await db.refresh(existing)
        return existing

    item = CartItem(cart_id=cart.id, variant_id=payload.variant_id, quantity=payload.quantity)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/items/{item_id}", response_model=CartItemOut)
async def update_item_quantity(
    item_id: uuid.UUID,
    quantity: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if quantity <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La cantidad debe ser mayor a cero")
    cart = await _get_or_create_cart(user.id, db)
    result = await db.execute(select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ítem no encontrado en el carrito")
    item.quantity = quantity
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cart = await _get_or_create_cart(user.id, db)
    result = await db.execute(select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id))
    item = result.scalar_one_or_none()
    if item:
        await db.delete(item)
        await db.commit()
