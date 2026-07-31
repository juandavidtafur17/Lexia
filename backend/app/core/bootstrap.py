import asyncio
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.config import settings
from app.core.database import Base, engine
from app.core.security import hash_password
from app.models.catalog import Category, Product, ProductStatus, ProductVariant
from app.models.finance import TaxRule
from app.models.inventory import InventoryItem, Warehouse
from app.models.order import Cart
from app.models.user import Permission, SellerProfile, User, UserRole

PERMISSIONS = [
    ("manage_users", "Gestionar cuentas de usuario"),
    ("manage_catalog", "Crear/editar productos y categorías"),
    ("manage_inventory", "Ajustar stock y almacenes"),
    ("manage_orders", "Cambiar estado de pedidos"),
    ("view_financial_reports", "Ver reportes contables y de ventas"),
    ("approve_sellers", "Aprobar perfiles de vendedor"),
]

TAX_RULES = [
    ("PE", "IGV", 0.18),
    ("US", "Sales Tax", 0.0725),
    ("MX", "IVA", 0.16),
    ("CO", "IVA", 0.19),
    ("ES", "IVA", 0.21),
]

WAREHOUSES = [
    ("WH-LIM-01", "Almacén Central Lima", "PE", "Lima", "America/Lima"),
]

CATEGORIES = [
    ("Electrónica", "electronica", "Componentes y dispositivos de alto rendimiento"),
    ("Hogar", "hogar", "Productos para el hogar y espacios de trabajo"),
    ("Belleza", "belleza", "Cuidado personal y bienestar"),
]


def _sync_engine():
    connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
    return create_engine(settings.SYNC_DATABASE_URL, connect_args=connect_args)


def _seed_data() -> None:
    sync_engine = _sync_engine()
    with Session(sync_engine) as session:
        Base.metadata.create_all(sync_engine)

        for code, desc in PERMISSIONS:
            if not session.get(Permission, code):
                session.add(Permission(code=code, description=desc))

        for country, name, rate in TAX_RULES:
            exists = session.query(TaxRule).filter_by(country_code=country, tax_name=name).first()
            if not exists:
                session.add(TaxRule(country_code=country, tax_name=name, rate=rate))

        for code, name, country, city, tz in WAREHOUSES:
            exists = session.query(Warehouse).filter_by(code=code).first()
            if not exists:
                session.add(Warehouse(code=code, name=name, country_code=country, city=city, timezone=tz))

        for name, slug, description in CATEGORIES:
            exists = session.query(Category).filter_by(slug=slug).first()
            if not exists:
                session.add(Category(name=name, slug=slug, description=description, is_active=True))

        session.commit()

        demo_user = session.query(User).filter_by(email="demo@lexia.test").first()
        if not demo_user:
            demo_user = User(
                email="demo@lexia.test",
                hashed_password=hash_password("Lexia123!"),
                full_name="Demo Lexia",
                role=UserRole.CUSTOMER,
                is_active=True,
                is_verified=True,
                preferred_currency="USD",
            )
            session.add(demo_user)
            session.flush()
            session.add(Cart(user_id=demo_user.id))

        seller_user = session.query(User).filter_by(email="seller@lexia.test").first()
        if not seller_user:
            seller_user = User(
                email="seller@lexia.test",
                hashed_password=hash_password("Lexia123!"),
                full_name="Vendedor Lexia",
                role=UserRole.SELLER,
                is_active=True,
                is_verified=True,
                preferred_currency="USD",
            )
            session.add(seller_user)
            session.flush()
            session.add(SellerProfile(user_id=seller_user.id, store_name="LEXIA Store", tax_id="999999999", is_approved=True))

        session.commit()

        seller_profile = session.query(SellerProfile).filter_by(user_id=seller_user.id).first() if seller_user else None
        category = session.query(Category).filter_by(slug="electronica").first()
        if seller_profile and category:
            product_exists = session.query(Product).filter_by(title="Kit de gestión LEXIA").first()
            if not product_exists:
                product = Product(
                    seller_id=seller_profile.id,
                    category_id=category.id,
                    title="Kit de gestión LEXIA",
                    slug=f"kit-gestion-lexia-{uuid.uuid4().hex[:8]}",
                    description="Herramienta operativa para gestionar ventas, inventario y pedidos en un solo lugar.",
                    brand="LEXIA",
                    tags=["gestion", "inventario", "pedidos"],
                    status=ProductStatus.ACTIVE,
                    rating_average=4.8,
                    rating_count=18,
                )
                session.add(product)
                session.flush()
                session.add(
                    ProductVariant(
                        product_id=product.id,
                        sku="LEXIA-001",
                        price=149.99,
                        currency="USD",
                        weight_grams=500,
                        is_active=True,
                    )
                )
                session.flush()
                warehouse = session.query(Warehouse).filter_by(code="WH-LIM-01").first()
                if warehouse:
                    variant = session.query(ProductVariant).filter_by(sku="LEXIA-001").first()
                    if variant:
                        session.add(
                            InventoryItem(
                                warehouse_id=warehouse.id,
                                variant_id=variant.id,
                                quantity_on_hand=12,
                                quantity_reserved=0,
                            )
                        )
                session.commit()


async def initialize_database() -> None:
    # For sqlite (aiosqlite) the sync DB API used by SQLAlchemy internals
    # may attempt operations unsupported by the async driver during early
    # connection setup. Use the synchronous engine to create schema and
    # seed data on a background thread for reliable local development.
    if settings.DATABASE_URL.startswith("sqlite"):
        sync_engine = _sync_engine()
        await asyncio.to_thread(lambda: Base.metadata.create_all(bind=sync_engine))
        await asyncio.to_thread(_seed_data)
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await asyncio.to_thread(_seed_data)
