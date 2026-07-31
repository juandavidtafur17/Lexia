import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class StockMovementType(str, enum.Enum):
    INBOUND = "inbound"           # recepción de proveedor
    OUTBOUND = "outbound"         # venta despachada
    RESERVATION = "reservation"   # reserva temporal por checkout en curso
    RELEASE = "release"           # liberación de reserva expirada/cancelada
    ADJUSTMENT = "adjustment"     # ajuste manual de auditoría
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"
    RETURN = "return"


class Warehouse(Base):
    """Almacén físico — soporta operación multizona/multi-país."""
    __tablename__ = "warehouses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    address_line: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(default=True)

    zones: Mapped[list["WarehouseZone"]] = relationship(
        back_populates="warehouse", cascade="all, delete-orphan"
    )


class WarehouseZone(Base):
    """Zona interna del almacén (recepción, picking, alto valor, refrigerado...)."""
    __tablename__ = "warehouse_zones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(30), default="standard")  # standard, cold, high_value

    warehouse: Mapped["Warehouse"] = relationship(back_populates="zones")
    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="zone")

    __table_args__ = (UniqueConstraint("warehouse_id", "code", name="uq_zone_per_warehouse"),)


class InventoryItem(Base):
    """
    Existencia de una variante (SKU) en una zona de un almacén específico.
    quantity_on_hand = físico real. quantity_reserved = comprometido en
    checkouts activos. Disponible = on_hand - reserved (nunca negativo).
    """
    __tablename__ = "inventory_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("warehouse_zones.id"), nullable=True)

    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, default=5)
    bin_location: Mapped[str | None] = mapped_column(String(50), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    variant: Mapped["ProductVariant"] = relationship(back_populates="inventory_items")
    zone: Mapped["WarehouseZone | None"] = relationship(back_populates="inventory_items")

    __table_args__ = (
        UniqueConstraint("variant_id", "warehouse_id", "zone_id", name="uq_stock_per_variant_location"),
    )

    @property
    def quantity_available(self) -> int:
        return max(self.quantity_on_hand - self.quantity_reserved, 0)


class StockMovement(Base):
    """Bitácora inmutable de todo movimiento de inventario — base de la auditoría forense."""
    __tablename__ = "stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inventory_items.id"), nullable=False)
    movement_type: Mapped[StockMovementType] = mapped_column(
        Enum(StockMovementType, name="stock_movement_type"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # siempre positivo; el tipo define el signo
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "order", "purchase_order"...
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    performed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    contact_email: Mapped[str] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2))
    payment_terms_days: Mapped[int] = mapped_column(default=30)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
