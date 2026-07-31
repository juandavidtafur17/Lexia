from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_token,
    decode_token,
    generate_mfa_secret,
    get_mfa_provisioning_uri,
    hash_password,
    verify_mfa_code,
    verify_password,
)
from app.models.order import Cart
from app.models.user import User
from app.schemas.schemas import TokenPair, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/auth", tags=["Autenticación"])

_redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        country_code=payload.country_code.upper(),
    )
    db.add(user)
    await db.flush()

    # Todo usuario nuevo recibe un carrito persistente vacío
    db.add(Cart(user_id=user.id))

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    lock_key = f"login_lock:{payload.email}"
    attempts_key = f"login_attempts:{payload.email}"

    if await _redis.get(lock_key):
        raise HTTPException(
            status.HTTP_423_LOCKED,
            f"Cuenta bloqueada temporalmente por múltiples intentos fallidos. "
            f"Intente de nuevo en {LOCKOUT_MINUTES} minutos.",
        )

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        attempts = await _redis.incr(attempts_key)
        await _redis.expire(attempts_key, LOCKOUT_MINUTES * 60)
        if attempts >= MAX_FAILED_ATTEMPTS:
            await _redis.set(lock_key, "1", ex=LOCKOUT_MINUTES * 60)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cuenta desactivada")

    if user.mfa_enabled:
        if not payload.mfa_code or not verify_mfa_code(user.mfa_secret, payload.mfa_code):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código MFA inválido o ausente")

    await _redis.delete(attempts_key)
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    access = create_token(str(user.id), "access", {"role": user.role.value})
    refresh = create_token(str(user.id), "refresh")
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token inválido")

    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tipo de token incorrecto")

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no válido")

    access = create_token(str(user.id), "access", {"role": user.role.value})
    new_refresh = create_token(str(user.id), "refresh")
    return TokenPair(access_token=access, refresh_token=new_refresh)


@router.post("/mfa/setup")
async def setup_mfa(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    secret = generate_mfa_secret()
    user.mfa_secret = secret
    await db.commit()
    return {
        "secret": secret,
        "provisioning_uri": get_mfa_provisioning_uri(secret, user.email),
    }


@router.post("/mfa/confirm")
async def confirm_mfa(code: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user.mfa_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Primero ejecute /mfa/setup")
    if not verify_mfa_code(user.mfa_secret, code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código incorrecto")
    user.mfa_enabled = True
    await db.commit()
    return {"mfa_enabled": True}


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return user
