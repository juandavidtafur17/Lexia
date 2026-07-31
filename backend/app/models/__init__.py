"""
Punto único de importación de todos los modelos ORM — garantiza que
Base.metadata conozca cada tabla antes de que Alembic genere migraciones
o de que se ejecute create_all() en entornos de prueba.
"""
from app.models.user import User, SellerProfile, Address, Permission, UserRole  # noqa: F401
from app.models.catalog import Category, Product, ProductImage, ProductVariant, ProductStatus  # noqa: F401
from app.models.inventory import (  # noqa: F401
    Warehouse, WarehouseZone, InventoryItem, StockMovement, Supplier, StockMovementType
)
from app.models.order import (  # noqa: F401
    Cart, CartItem, Order, OrderItem, OrderStatusHistory, OrderStatus
)
from app.models.finance import Payment, TaxRule, ExchangeRate, Invoice, Coupon, PaymentStatus  # noqa: F401
from app.models.engagement import Review, WishlistItem, Notification, NotificationChannel  # noqa: F401
