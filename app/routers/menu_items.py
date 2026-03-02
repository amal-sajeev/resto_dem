from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import MenuItem
from app.schemas import MenuItemResponse, MenuItemUpdate

router = APIRouter(prefix="/menu-items", tags=["menu-items"])


@router.get("", response_model=list[MenuItemResponse])
async def list_menu_items(
    restaurant_id: Optional[UUID] = Query(None, description="Filter by restaurant"),
    db: AsyncSession = Depends(get_db),
) -> list[MenuItem]:
    q = select(MenuItem).options(selectinload(MenuItem.options)).order_by(MenuItem.category, MenuItem.name)
    if restaurant_id is not None:
        q = q.where(MenuItem.restaurant_id == restaurant_id)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.patch("/{menu_item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    menu_item_id: UUID,
    body: MenuItemUpdate,
    db: AsyncSession = Depends(get_db),
) -> MenuItem:
    result = await db.execute(select(MenuItem).where(MenuItem.id == menu_item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/{menu_item_id}", status_code=204)
async def delete_menu_item(
    menu_item_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(MenuItem).where(MenuItem.id == menu_item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    await db.delete(item)
    await db.flush()
