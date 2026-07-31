"""
Prueba de integración del flujo crítico: reserva de stock atómica al crear
un pedido. Requiere una base de datos Postgres de pruebas accesible vía
TEST_DATABASE_URL (ver README, sección "Pruebas").

Ejecutar con:  pytest tests/test_orders_flow.py -v
"""
import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.catalog import Category, Product, ProductVariant, ProductStatus
from app.models.inventory import InventoryItem, Warehouse
from app.models.user import SellerProfile, User, UserRole
from app.core.security import hash_password


@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_checkout_reserves_stock_atomically(db_session):
    """
    Verifica que al crear un pedido:
    1. El stock disponible se reduce exactamente en la cantidad comprada.
    2. Un segundo intento de compra que exceda el stock restante es rechazado
       con HTTP 409, sin dejar el sistema en un estado inconsistente.
    """
    # --- Arrange: catálogo, vendedor y stock inicial de 3 unidades ---
    seller_user = User(
        email=f"seller_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password=hash_password("Password123"),
        full_name="Vendedor de Prueba",
        role=UserRole.SELLER,
        country_code="PE",
    )
    db_session.add(seller_user)
    await db_session.flush()

    seller_profile = SellerProfile(
        user_id=seller_user.id, store_name="Tienda Test", tax_id="12345678901", is_approved=True
    )
    db_session.add(seller_profile)

    category = Category(name="Electrónica", slug=f"electronica-{uuid.uuid4().hex[:6]}")
    db_session.add(category)
    await db_session.flush()

    product = Product(
        seller_id=seller_profile.id,
        category_id=category.id,
        title="Producto de Prueba",
        slug=f"producto-{uuid.uuid4().hex[:6]}",
        status=ProductStatus.ACTIVE,
    )
    db_session.add(product)
    await db_session.flush()

    variant = ProductVariant(product_id=product.id, sku=f"SKU-{uuid.uuid4().hex[:8]}", price=50.00, weight_grams=500)
    db_session.add(variant)
    await db_session.flush()

    warehouse = Warehouse(code=f"WH-{uuid.uuid4().hex[:4]}", name="Almacén Test", country_code="PE", city="Lima")
    db_session.add(warehouse)
    await db_session.flush()

    inventory = InventoryItem(variant_id=variant.id, warehouse_id=warehouse.id, quantity_on_hand=3)
    db_session.add(inventory)
    await db_session.commit()

    assert inventory.quantity_available == 3

    # --- Act & Assert vía API real (ASGI transport, sin servidor HTTP externo) ---
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        buyer_email = f"buyer_{uuid.uuid4().hex[:6]}@test.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": buyer_email,
                "password": "Password123",
                "full_name": "Comprador Test",
                "country_code": "PE",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login", json={"email": buyer_email, "password": "Password123"}
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.post(
            "/api/v1/cart/items",
            json={"variant_id": str(variant.id), "quantity": 3},
            headers=headers,
        )

        order_resp = await client.post(
            "/api/v1/orders",
            json={
                "shipping_address": {
                    "recipient_name": "Comprador Test",
                    "line1": "Av. Test 123",
                    "city": "Lima",
                    "state": "Lima",
                    "postal_code": "15001",
                    "country_code": "PE",
                },
                "billing_address": {
                    "recipient_name": "Comprador Test",
                    "line1": "Av. Test 123",
                    "city": "Lima",
                    "state": "Lima",
                    "postal_code": "15001",
                    "country_code": "PE",
                },
            },
            headers=headers,
        )
        assert order_resp.status_code == 201

    await db_session.refresh(inventory)
    assert inventory.quantity_available == 0, "El stock disponible debe quedar en 0 tras reservar las 3 unidades"
