import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint, Index
)
from app.core.compat_types import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ProductStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    PAUSED = "paused"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(default=0)

    children: Mapped[list["Category"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    parent: Mapped["Category | None"] = relationship(back_populates="children", remote_side=[id])
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    """Producto raíz — agrupa una o más variantes transaccionables (SKUs)."""
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seller_profiles.id"), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(280), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    brand: Mapped[str | None] = mapped_column(String(150), nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"), default=ProductStatus.DRAFT
    )
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)  # atributos dinámicos por categoría

    rating_average: Mapped[float] = mapped_column(default=0.0)
    rating_count: Mapped[int] = mapped_column(default=0)
    sales_count: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category: Mapped["Category"] = relationship(back_populates="products")
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.display_order"
    )

    __table_args__ = (Index("ix_products_category_status", "category_id", "status"),)


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_order: Mapped[int] = mapped_column(default=0)

    product: Mapped["Product"] = relationship(back_populates="images")


class ProductVariant(Base):
    """
    Variante física transaccionable — posee SKU único global, código de barras,
    y las dimensiones/peso necesarias para el cálculo dinámico de envío.
    """
    __tablename__ = "product_variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)

    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)  # EAN-13 / UPC-A

    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    size: Mapped[str | None] = mapped_column(String(50), nullable=True)

    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    compare_at_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    cost_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)  # uso contable interno
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    weight_grams: Mapped[int] = mapped_column(nullable=False, default=0)
    length_cm: Mapped[float] = mapped_column(default=0)
    width_cm: Mapped[float] = mapped_column(default=0)
    height_cm: Mapped[float] = mapped_column(default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    product: Mapped["Product"] = relationship(back_populates="variants")
    inventory_items: Mapped[list["InventoryItem"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("product_id", "color", "size", name="uq_variant_product_color_size"),
    )
