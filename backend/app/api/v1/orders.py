import random
import string
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.catalog import ProductVariant
from app.models.finance import Coupon, TaxRule
from app.models.inventory import InventoryItem, StockMovement, StockMovementType
from app.models.order import Cart, CartItem, Order, OrderItem, OrderStatus, OrderStatusHistory
from app.models.user import User
from app.schemas.schemas import OrderCreate, OrderOut, OrderStatusUpdate
from app.tasks.tasks import generate_invoice_pdf, send_order_confirmation

router = APIRouter(prefix="/orders", tags=["Pedidos"])


def _generate_order_number() -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    rand_part = "".join(random.choices(string.digits, k=6))
    return f"ORD-{date_part}-{rand_part}"


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirma el checkout de forma transaccional:
    1. Bloquea (FOR UPDATE) cada fila de inventario involucrada para evitar
       sobreventa bajo concurrencia.
    2. Verifica disponibilidad real (on_hand - reserved).
    3. Reserva el stock (quantity_reserved += qty) — no descuenta on_hand
       todavía; el descuento físico ocurre al despachar.
    4. Congela precios server-side (nunca confía en el precio del cliente).
    5. Aplica impuestos por país de envío y cupón si corresponde.
    Si cualquier paso falla, toda la transacción hace rollback (ACID).
    """
    cart_result = await db.execute(
        select(Cart).where(Cart.user_id == user.id).options(selectinload(Cart.items))
    )
    cart = cart_result.scalar_one_or_none()
    if not cart or not cart.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El carrito está vacío")

    subtotal = 0.0
    order_items_to_create: list[dict] = []

    for cart_item in cart.items:
        variant_result = await db.execute(
            select(ProductVariant)
            .where(ProductVariant.id == cart_item.variant_id)
            .options(selectinload(ProductVariant.product))
        )
        variant = variant_result.scalar_one_or_none()
        if not variant or not variant.is_active:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"La variante {cart_item.variant_id} ya no está disponible"
            )

        inv_result = await db.execute(
            select(InventoryItem)
            .where(InventoryItem.variant_id == variant.id)
            .with_for_update()
            .limit(1)
        )
        inventory_item = inv_result.scalar_one_or_none()
        if not inventory_item or inventory_item.quantity_available < cart_item.quantity:
            available = inventory_item.quantity_available if inventory_item else 0
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Stock insuficiente para SKU {variant.sku}: disponible {available}, "
                f"solicitado {cart_item.quantity}",
            )

        inventory_item.quantity_reserved += cart_item.quantity
        db.add(
            StockMovement(
                inventory_item_id=inventory_item.id,
                movement_type=StockMovementType.RESERVATION,
                quantity=cart_item.quantity,
                reference_type="order_pending",
                performed_by=user.id,
            )
        )

        line_total = float(variant.price) * cart_item.quantity
        subtotal += line_total
        order_items_to_create.append(
            {
                "variant_id": variant.id,
                "seller_id": variant.product.seller_id,
                "product_title_snapshot": variant.product.title,
                "sku_snapshot": variant.sku,
                "unit_price_snapshot": variant.price,
                "quantity": cart_item.quantity,
                "commission_rate_snapshot": 0.10,
            }
        )

    # --- Impuestos por país de destino ---
    tax_result = await db.execute(
        select(TaxRule).where(
            TaxRule.country_code == payload.shipping_address.country_code.upper(),
            TaxRule.is_active.is_(True),
        )
    )
    tax_rule = tax_result.scalars().first()
    tax_rate = float(tax_rule.rate) if tax_rule else 0.0
    tax_amount = round(subtotal * tax_rate, 2)

    # --- Cupón ---
    discount_amount = 0.0
    if payload.coupon_code:
        coupon_result = await db.execute(
            select(Coupon).where(Coupon.code == payload.coupon_code, Coupon.is_active.is_(True))
        )
        coupon = coupon_result.scalar_one_or_none()
        if not coupon:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cupón inválido")
        if coupon.max_uses and coupon.times_used >= coupon.max_uses:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cupón agotado")
        if subtotal < float(coupon.min_order_amount):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"El cupón requiere un mínimo de {coupon.min_order_amount}",
            )
        if coupon.discount_type == "percentage":
            discount_amount = round(subtotal * float(coupon.discount_value) / 100, 2)
        else:
            discount_amount = min(float(coupon.discount_value), subtotal)
        coupon.times_used += 1

    shipping_amount = 0.0 if subtotal >= 100 else 9.99
    total_amount = round(subtotal + tax_amount + shipping_amount - discount_amount, 2)

    order = Order(
        order_number=_generate_order_number(),
        user_id=user.id,
        status=OrderStatus.PENDING_PAYMENT,
        subtotal_amount=round(subtotal, 2),
        tax_amount=tax_amount,
        shipping_amount=shipping_amount,
        discount_amount=discount_amount,
        total_amount=total_amount,
        currency=user.preferred_currency,
        shipping_address_snapshot=payload.shipping_address.model_dump(),
        billing_address_snapshot=payload.billing_address.model_dump(),
        coupon_code=payload.coupon_code,
        customer_notes=payload.customer_notes,
    )
    db.add(order)
    await db.flush()

    for oi in order_items_to_create:
        db.add(OrderItem(order_id=order.id, **oi))

    db.add(OrderStatusHistory(order_id=order.id, status=OrderStatus.PENDING_PAYMENT, changed_by=user.id))

    # Vaciar el carrito tras confirmar la reserva
    for cart_item in cart.items:
        await db.delete(cart_item)

    await db.commit()

    stmt = select(Order).where(Order.id == order.id).options(selectinload(Order.items))
    result = await db.execute(stmt)
    order = result.scalar_one()

    send_order_confirmation.delay(str(order.id))
    return order


@router.get("", response_model=list[OrderOut])
async def list_my_orders(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Order)
        .where(Order.user_id == user.id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order or order.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: uuid.UUID,
    payload: OrderStatusUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    old_status = order.status
    order.status = payload.status
    now = datetime.now(timezone.utc)

    if payload.status == OrderStatus.SHIPPED:
        order.shipped_at = now
    elif payload.status == OrderStatus.DELIVERED:
        order.delivered_at = now
    elif payload.status == OrderStatus.CANCELLED and old_status != OrderStatus.CANCELLED:
        order.cancelled_at = now
        # liberar reservas de inventario
        for item in order.items:
            inv_result = await db.execute(
                select(InventoryItem)
                .where(InventoryItem.variant_id == item.variant_id)
                .with_for_update()
                .limit(1)
            )
            inv = inv_result.scalar_one_or_none()
            if inv:
                inv.quantity_reserved = max(0, inv.quantity_reserved - item.quantity)
                db.add(
                    StockMovement(
                        inventory_item_id=inv.id,
                        movement_type=StockMovementType.RELEASE,
                        quantity=item.quantity,
                        reference_type="order",
                        reference_id=order.id,
                        performed_by=user.id,
                    )
                )
    elif payload.status == OrderStatus.PAID and old_status == OrderStatus.PENDING_PAYMENT:
        order.paid_at = now
        generate_invoice_pdf.delay(str(order.id))

    db.add(
        OrderStatusHistory(
            order_id=order.id, status=payload.status, note=payload.note, changed_by=user.id
        )
    )
    await db.commit()
    await db.refresh(order)
    return order
