"""
Capa de persistencia — motor asíncrono SQLAlchemy 2.0 + sesión por request.
Garantiza pool de conexiones controlado y transacciones ACID por operación.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine_kwargs = {
    "echo": settings.DEBUG,
}

if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({"connect_args": {"check_same_thread": False}})
else:
    engine_kwargs.update(
        {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_pre_ping": True,
        }
    )

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos ORM."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de FastAPI: entrega una sesión por request y garantiza
    rollback automático ante excepción y cierre determinista de la conexión.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
