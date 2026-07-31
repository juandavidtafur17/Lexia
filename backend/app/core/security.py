"""
Seguridad perimetral: hashing de contraseñas (bcrypt), emisión y verificación
de JWT firmados con RS256 (asimétrico — la llave privada nunca sale del
backend), y soporte de Multi-Factor Authentication (TOTP, RFC 6238).
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import pyotp
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_token(
    subject: str,
    token_type: TokenType,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    if token_type == "access":
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_private_key, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_public_key, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError(f"Token inválido o expirado: {exc}") from exc


def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def get_mfa_provisioning_uri(secret: str, account_email: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=account_email, issuer_name=settings.MFA_ISSUER_NAME
    )


def verify_mfa_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)
