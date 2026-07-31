import uuid

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.finance import Payment, PaymentStatus
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.tasks.tasks import generate_invoice_pdf, send_order_confirmation

router = APIRouter(prefix="/payments", tags=["Pagos"])

stripe.api_key = settings.STRIPE_API_KEY


@router.post("/orders/{order_id}/create-intent")
async def create_payment_intent(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Crea un PaymentIntent real en Stripe por el total exacto del pedido
    (en la unidad mínima de la moneda, p. ej. centavos). El frontend usa el
    client_secret devuelto con Stripe.js para capturar el método de pago sin
    que los datos de tarjeta transiten nunca por nuestro backend (PCI-DSS SAQ-A).
    """
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    if order.status != OrderStatus.PENDING_PAYMENT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El pedido no está pendiente de pago")

    if not settings.STRIPE_API_KEY:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "La pasarela de pagos no está configurada (falta STRIPE_API_KEY)",
        )

    amount_minor_units = int(round(float(order.total_amount) * 100))

    intent = stripe.PaymentIntent.create(
        amount=amount_minor_units,
        currency=order.currency.lower(),
        metadata={"order_id": str(order.id), "order_number": order.order_number},
        automatic_payment_methods={"enabled": True},
    )

    payment = Payment(
        order_id=order.id,
        gateway="stripe",
        gateway_reference=intent.id,
        status=PaymentStatus.REQUIRES_ACTION,
        amount=order.total_amount,
        currency=order.currency,
        raw_gateway_payload={"created": intent.created},
    )
    db.add(payment)
    await db.commit()

    return {"client_secret": intent.client_secret, "payment_intent_id": intent.id}


@router.post("/webhook/stripe", include_in_schema=False)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receptor de webhooks de Stripe. La firma se verifica criptográficamente
    contra STRIPE_WEBHOOK_SECRET — solicitudes sin firma válida se rechazan,
    evitando que un tercero falsifique confirmaciones de pago.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Firma de webhook inválida")

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        result = await db.execute(select(Payment).where(Payment.gateway_reference == intent["id"]))
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = PaymentStatus.SUCCEEDED
            payment.raw_gateway_payload = intent
            order = await db.get(Order, payment.order_id)
            if order and order.status == OrderStatus.PENDING_PAYMENT:
                order.status = OrderStatus.PAID
                from datetime import datetime, timezone
                order.paid_at = datetime.now(timezone.utc)
                await db.commit()
                generate_invoice_pdf.delay(str(order.id))
                send_order_confirmation.delay(str(order.id))
            else:
                await db.commit()

    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        result = await db.execute(select(Payment).where(Payment.gateway_reference == intent["id"]))
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = PaymentStatus.FAILED
            await db.commit()

    return {"received": True}
