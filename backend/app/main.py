import time
import uuid

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import auth, cart, inventory, orders, payments, products, reports, sellers
from app.core.bootstrap import initialize_database
from app.core.config import settings
from app.websocket.manager import inventory_ws_endpoint, notifications_ws_endpoint
from starlette.concurrency import run_in_threadpool
from app.core.database import Base, AsyncSessionLocal, engine
from app.models.user import Permission
from app.models.finance import TaxRule
from app.models.inventory import Warehouse
from sqlalchemy import select

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ERP Comercial y Marketplace de Alta Concurrencia — API v1",
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
)


@app.on_event("startup")
async def startup_event() -> None:
    await initialize_database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Asigna un ID de correlación por request y mide latencia — base de la auditoría/observabilidad."""
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-ms"] = f"{duration_ms:.2f}"
    return response


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(products.router, prefix=API_PREFIX)
app.include_router(cart.router, prefix=API_PREFIX)
app.include_router(orders.router, prefix=API_PREFIX)
app.include_router(inventory.router, prefix=API_PREFIX)
app.include_router(payments.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(sellers.router, prefix=API_PREFIX)


@app.websocket("/ws/inventory/{warehouse_id}")
async def ws_inventory(websocket: WebSocket, warehouse_id: str):
    await inventory_ws_endpoint(websocket, warehouse_id)


@app.websocket("/ws/notifications/{user_id}")
async def ws_notifications(websocket: WebSocket, user_id: uuid.UUID):
    await notifications_ws_endpoint(websocket, user_id)


@app.get("/health", tags=["Sistema"])
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.post("/dev/init", include_in_schema=False)
async def dev_init_db():
    """Crea tablas y datos base mínimos para desarrollo.
    Ejecutable solo en entornos no productivos.
    """
    if settings.ENVIRONMENT == "production":
        from fastapi import HTTPException

        raise HTTPException(403, "Not allowed in production")

    # Crear esquema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Insertar datos base mínimos (permissions, tax rules, warehouses)
    async with AsyncSessionLocal() as session:
        # permisos
        perms = [
            ("manage_users", "Gestionar cuentas de usuario"),
            ("manage_catalog", "Crear/editar productos y categorías"),
            ("manage_inventory", "Ajustar stock y almacenes"),
            ("manage_orders", "Cambiar estado de pedidos"),
            ("view_financial_reports", "Ver reportes contables y de ventas"),
            ("approve_sellers", "Aprobar perfiles de vendedor"),
        ]
        for code, desc in perms:
            q = await session.execute(select(Permission).where(Permission.code == code))
            if not q.scalar_one_or_none():
                session.add(Permission(code=code, description=desc))

        # reglas de impuesto
        tax_rules = [
            ("PE", "IGV", 0.18),
            ("US", "Sales Tax", 0.0725),
            ("MX", "IVA", 0.16),
        ]
        for country, name, rate in tax_rules:
            q = await session.execute(select(TaxRule).where(TaxRule.country_code == country, TaxRule.tax_name == name))
            if not q.scalars().first():
                session.add(TaxRule(country_code=country, tax_name=name, rate=rate))

        # almacenes
        warehouses = [
            ("WH-LIM-01", "Almacén Central Lima", "PE", "Lima", "America/Lima"),
        ]
        for code, name, country, city, tz in warehouses:
            q = await session.execute(select(Warehouse).where(Warehouse.code == code))
            if not q.scalars().first():
                session.add(Warehouse(code=code, name=name, country_code=country, city=city, timezone=tz))

        await session.commit()

    return {"status": "ok", "detail": "db initialized"}
