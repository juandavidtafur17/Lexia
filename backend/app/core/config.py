"""
Configuración central del sistema.
Todas las credenciales y parámetros sensibles se leen exclusivamente desde
variables de entorno (.env) — nunca se hardcodean en el código fuente.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_private_key() -> str:
    path = Path("./keys/private.pem")
    if path.exists():
        return path.read_text()
    return "dev-private-key"


def _default_public_key() -> str:
    path = Path("./keys/public.pem")
    if path.exists():
        return path.read_text()
    return "dev-public-key"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Aplicación ---
    APP_NAME: str = "ERP Marketplace Core"
    APP_VERSION: str = "2.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # --- Base de datos ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    SYNC_DATABASE_URL: str = "sqlite:///./app.db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # --- Redis / Caché / Colas ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Elasticsearch ---
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # --- Seguridad / JWT ---
    SECRET_KEY: str = "dev-secret-key"
    JWT_PRIVATE_KEY_PATH: str = "./keys/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "./keys/public.pem"
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # --- Almacenamiento de objetos (S3 / MinIO) ---
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "erp-marketplace"
    S3_REGION: str = "us-east-1"

    # --- Pagos ---
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # --- Notificaciones ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMS_PROVIDER_API_KEY: str = ""
    PUSH_PROVIDER_API_KEY: str = ""

    # --- Reglas de negocio ---
    DEFAULT_CURRENCY: str = "USD"
    LOW_STOCK_THRESHOLD: int = 5
    ORDER_RESERVATION_MINUTES: int = 15
    MFA_ISSUER_NAME: str = "ERP-Marketplace"

    @property
    def jwt_private_key(self) -> str:
        path = Path(self.JWT_PRIVATE_KEY_PATH)
        if not path.exists():
            return _default_private_key()
        return path.read_text()

    @property
    def jwt_public_key(self) -> str:
        path = Path(self.JWT_PUBLIC_KEY_PATH)
        if not path.exists():
            return _default_public_key()
        return path.read_text()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
