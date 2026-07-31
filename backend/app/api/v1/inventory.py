import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_warehouse_staff
from app.core.database import get_db
from app.models.inventory import InventoryItem, StockMovement, StockMovementType, Warehouse
from app.models.user import User
from app.schemas.schemas import InventoryItemOut, StockAdjustment

router = APIRouter(prefix="/inventory", tags=["Inventario y Almacenes"])


@router.get("/warehouses/{warehouse_id}/stock", response_model=list[InventoryItemOut])
async def list_warehouse_stock(
    warehouse_id: uuid.UUID,
    low_stock_only: bool = False,
    user: User = Depends(require_warehouse_staff),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InventoryItem).where(InventoryItem.warehouse_id == warehouse_id)
    result = await db.execute(stmt)
    items = result.scalars().all()
    if low_stock_only:
        items = [i for i in items if i.quantity_available <= i.reorder_point]
    return items


@router.post("/adjust", status_code=status.HTTP_200_OK)
async def adjust_stock(
    payload: StockAdjustment,
    user: User = Depends(require_warehouse_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Ajuste manual de auditoría. Usa una transacción atómica: la fila de
    inventario se bloquea (SELECT ... FOR UPDATE) para evitar condiciones de
    carrera bajo alta concurrencia antes de aplicar el delta.
    """
    stmt = (
        select(InventoryItem)
        .where(
            InventoryItem.variant_id == payload.variant_id,
            InventoryItem.warehouse_id == payload.warehouse_id,
        )
        .with_for_update()
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if item is None:
        item = InventoryItem(
            variant_id=payload.variant_id,
            warehouse_id=payload.warehouse_id,
            quantity_on_hand=0,
        )
        db.add(item)
        await db.flush()

    new_quantity = item.quantity_on_hand + payload.quantity_delta
    if new_quantity < 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"El ajuste dejaría stock negativo (actual: {item.quantity_on_hand})",
        )

    item.quantity_on_hand = new_quantity

    db.add(
        StockMovement(
            inventory_item_id=item.id,
            movement_type=StockMovementType.ADJUSTMENT,
            quantity=abs(payload.quantity_delta),
            performed_by=user.id,
            notes=payload.reason,
        )
    )

    await db.commit()
    await db.refresh(item)
    return {
        "inventory_item_id": str(item.id),
        "quantity_on_hand": item.quantity_on_hand,
        "quantity_available": item.quantity_available,
    }


@router.get("/warehouses", response_model=list[dict])
async def list_warehouses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Warehouse).where(Warehouse.is_active.is_(True)))
    return [
        {
            "id": str(w.id),
            "code": w.code,
            "name": w.name,
            "country_code": w.country_code,
            "city": w.city,
        }
        for w in result.scalars().all()
    ]
