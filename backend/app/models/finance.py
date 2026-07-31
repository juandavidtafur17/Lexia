import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Boolean
from app.core.compat_types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PaymentStatus(str, enum.Enum):
    REQUIRES_ACTION = "requires_action"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class Payment(Base):
    """
    Registro de intento/transacción de pago. gateway_reference es el ID
    devuelto por la pasarela (p. ej. PaymentIntent de Stripe) — nunca se
    almacenan datos de tarjeta: la tokenización ocurre en el proveedor.
    """
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)

    gateway: Mapped[str] = mapped_column(String(30), default="stripe")
    gateway_reference: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"), default=PaymentStatus.REQUIRES_ACTION
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    payment_method_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    raw_gateway_payload: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TaxRule(Base):
    """Regla de impuesto por país/región — permite localización dinámica."""
    __tablename__ = "tax_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    region_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tax_name: Mapped[str] = mapped_column(String(50), nullable=False)  # IVA, IGV, VAT, GST...
    rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)  # 0.18 = 18%
    applies_to_shipping: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ExchangeRate(Base):
    """Tasas de cambio cacheadas para conversión multimoneda (actualizadas por tarea periódica)."""
    __tablename__ = "exchange_rates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Invoice(Base):
    """Factura contable generada de forma asíncrona (PDF) a partir de un pedido pagado."""
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)

    issuer_legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer_tax_id: Mapped[str] = mapped_column(String(50), nullable=False)
    buyer_legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    buyer_tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    subtotal_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    pdf_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)  # ruta en S3/MinIO
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    discount_type: Mapped[str] = mapped_column(String(20), default="percentage")  # percentage | fixed_amount
    discount_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    min_order_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    max_uses: Mapped[int | None] = mapped_column(nullable=True)
    times_used: Mapped[int] = mapped_column(default=0)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
