"""
Table management router: CRUD for restaurant tables (establishment-scoped).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_establishment_id, require_role
from app.database import get_db
from app.models import Restaurant, Table, User, UserRole
from app.schemas import TableCreate, TableResponse, TableUpdate

router = APIRouter(prefix="/tables", tags=["tables"])


@router.get("", response_model=list[TableResponse])
async def list_tables(
    request: Request,
    restaurant_id: UUID = Query(...),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    est_id = get_establishment_id(request)
    rest_check = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id, Restaurant.establishment_id == est_id)
    )
    if rest_check.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    q = select(Table).where(Table.restaurant_id == restaurant_id)
    if active_only:
        q = q.where(Table.is_active == True)  # noqa: E712
    q = q.order_by(Table.table_number)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
async def create_table(
    body: TableCreate,
    request: Request,
    user: User = Depends(require_role(UserRole.establishment_admin, UserRole.restaurant_admin)),
    db: AsyncSession = Depends(get_db),
):
    est_id = get_establishment_id(request)
    rest_check = await db.execute(
        select(Restaurant).where(Restaurant.id == body.restaurant_id, Restaurant.establishment_id == est_id)
    )
    if rest_check.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    if user.role == UserRole.restaurant_admin and user.restaurant_id != body.restaurant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot manage tables for another restaurant")

    table = Table(
        restaurant_id=body.restaurant_id,
        table_number=body.table_number,
        capacity=body.capacity,
    )
    db.add(table)
    await db.flush()
    await db.refresh(table)
    return table


@router.patch("/{table_id}", response_model=TableResponse)
async def update_table(
    table_id: UUID,
    body: TableUpdate,
    request: Request,
    user: User = Depends(require_role(UserRole.establishment_admin, UserRole.restaurant_admin)),
    db: AsyncSession = Depends(get_db),
):
    est_id = get_establishment_id(request)
    result = await db.execute(
        select(Table)
        .join(Restaurant, Table.restaurant_id == Restaurant.id)
        .where(Table.id == table_id, Restaurant.establishment_id == est_id)
    )
    table = result.scalar_one_or_none()
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")

    if user.role == UserRole.restaurant_admin and user.restaurant_id != table.restaurant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot manage tables for another restaurant")

    if body.table_number is not None:
        table.table_number = body.table_number
    if body.capacity is not None:
        table.capacity = body.capacity
    if body.is_active is not None:
        table.is_active = body.is_active

    await db.flush()
    await db.refresh(table)
    return table


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    table_id: UUID,
    request: Request,
    user: User = Depends(require_role(UserRole.establishment_admin, UserRole.restaurant_admin)),
    db: AsyncSession = Depends(get_db),
):
    est_id = get_establishment_id(request)
    result = await db.execute(
        select(Table)
        .join(Restaurant, Table.restaurant_id == Restaurant.id)
        .where(Table.id == table_id, Restaurant.establishment_id == est_id)
    )
    table = result.scalar_one_or_none()
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")

    if user.role == UserRole.restaurant_admin and user.restaurant_id != table.restaurant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot manage tables for another restaurant")

    table.is_active = False
    await db.flush()
