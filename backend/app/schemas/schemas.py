import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.order import OrderStatus
from app.models.user import UserRole


# ---------- Auth ----------
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10)
    full_name: str = Field(min_length=2, max_length=255)
    country_code: str = Field(min_length=2, max_length=2)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe incluir al menos una mayúscula y un número")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    mfa_code: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    created_at: datetime


# ---------- Catálogo ----------
class ProductVariantCreate(BaseModel):
    sku: str = Field(max_length=64)
    barcode: str | None = None
    color: str | None = None
    size: str | None = None
    price: float = Field(gt=0)
    compare_at_price: float | None = None
    currency: str = "USD"
    weight_grams: int = Field(ge=0)
    length_cm: float = 0
    width_cm: float = 0
    height_cm: float = 0


class ProductVariantOut(ProductVariantCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    is_active: bool


class ProductCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = ""
    category_id: uuid.UUID
    brand: str | None = None
    tags: list[str] = []
    attributes: dict = {}
    variants: list[ProductVariantCreate] = Field(min_length=1)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    slug: str
    description: str
    brand: str | None
    status: str
    rating_average: float
    rating_count: int
    variants: list[ProductVariantOut]


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    slug: str
    parent_id: uuid.UUID | None
    is_active: bool


# ---------- Carrito / Pedido ----------
class CartItemCreate(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(gt=0, le=100)


class CartItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    variant_id: uuid.UUID
    quantity: int


class AddressIn(BaseModel):
    recipient_name: str
    line1: str
    line2: str | None = None
    city: str
    state: str
    postal_code: str
    country_code: str = Field(min_length=2, max_length=2)
    phone_number: str | None = None


class OrderCreate(BaseModel):
    shipping_address: AddressIn
    billing_address: AddressIn
    coupon_code: str | None = None
    customer_notes: str | None = None


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_title_snapshot: str
    sku_snapshot: str
    unit_price_snapshot: float
    quantity: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    order_number: str
    status: OrderStatus
    subtotal_amount: float
    tax_amount: float
    shipping_amount: float
    discount_amount: float
    total_amount: float
    currency: str
    created_at: datetime
    items: list[OrderItemOut]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: str | None = None


# ---------- Inventario ----------
class StockAdjustment(BaseModel):
    variant_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity_delta: int
    reason: str = Field(min_length=3, max_length=500)


class InventoryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    variant_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity_on_hand: int
    quantity_reserved: int

    @property
    def quantity_available(self) -> int:
        return max(self.quantity_on_hand - self.quantity_reserved, 0)


# ---------- Reseñas ----------
class ReviewCreate(BaseModel):
    order_item_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    title: str | None = None
    comment: str = ""


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    rating: int
    title: str | None
    comment: str
    is_verified_purchase: bool
    created_at: datetime
