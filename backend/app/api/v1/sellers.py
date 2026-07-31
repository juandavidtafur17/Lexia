from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import SellerProfile, User, UserRole

router = APIRouter(prefix="/sellers", tags=["Vendedores"])


class SellerApply(BaseModel):
    store_name: str = Field(min_length=2, max_length=150)
    tax_id: str = Field(min_length=5, max_length=50)


class SellerProfileOut(BaseModel):
    id: str
    store_name: str
    tax_id: str
    is_approved: bool
    commission_rate: float


@router.get("/me")
async def get_my_seller_profile(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SellerProfile).where(SellerProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El usuario aún no tiene perfil de vendedor")
    return {
        "id": str(profile.id),
        "store_name": profile.store_name,
        "tax_id": profile.tax_id,
        "is_approved": profile.is_approved,
        "commission_rate": profile.commission_rate,
    }


@router.post("/apply", status_code=status.HTTP_201_CREATED)
async def apply_as_seller(
    payload: SellerApply,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Alta de vendedor en la plataforma. La aprobación es inmediata (modelo de
    autoservicio, similar a Amazon Seller Central o Facebook Marketplace):
    el vendedor puede publicar productos apenas completa este paso. La
    moderación de contenido ocurre post-publicación (reportes, revisión de
    catálogo), no como bloqueo previo — decisión de producto documentada en
    el README.
    """
    existing = await db.execute(select(SellerProfile).where(SellerProfile.user_id == user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "El usuario ya tiene un perfil de vendedor")

    profile = SellerProfile(
        user_id=user.id,
        store_name=payload.store_name,
        tax_id=payload.tax_id,
        is_approved=True,
    )
    db.add(profile)

    if user.role == UserRole.CUSTOMER:
        user.role = UserRole.SELLER

    await db.commit()
    await db.refresh(profile)

    return {
        "id": str(profile.id),
        "store_name": profile.store_name,
        "tax_id": profile.tax_id,
        "is_approved": profile.is_approved,
        "commission_rate": profile.commission_rate,
    }
