"""
Inicializa el esquema de base de datos y carga datos semilla mínimos
indispensables para operar (no son "datos de prueba" ficticios de un
producto, sino configuración base real: almacén principal, permisos RBAC
por rol, y reglas de impuesto por país). Ejecutar una sola vez por entorno:

    python scripts/init_db.py

Para cambios de esquema posteriores use Alembic:
    cd database && alembic revision --autogenerate -m "descripcion" && alembic upgrade head
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402
import app.models  # noqa: E402
from app.models.finance import TaxRule  # noqa: E402
from app.models.inventory import Warehouse  # noqa: E402
from app.models.user import Permission, UserRole, role_permissions  # noqa: E402

engine = create_engine(settings.SYNC_DATABASE_URL)

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


def main() -> None:
    print(f"Creando esquema en {settings.SYNC_DATABASE_URL} ...")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
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

        session.commit()
    print("Esquema y datos base cargados correctamente.")


if __name__ == "__main__":
    main()
