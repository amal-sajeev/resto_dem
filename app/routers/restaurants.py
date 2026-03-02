from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import MenuItem, Restaurant
from app.schemas import (
    MenuItemCreate,
    MenuItemResponse,
    RestaurantCreate,
    RestaurantResponse,
    RestaurantUpdate,
)

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("", response_model=list[RestaurantResponse])
async def list_restaurants(db: AsyncSession = Depends(get_db)) -> list[Restaurant]:
    result = await db.execute(select(Restaurant).order_by(Restaurant.name))
    return list(result.scalars().all())


@router.post("", response_model=RestaurantResponse)
async def create_restaurant(
    body: RestaurantCreate,
    db: AsyncSession = Depends(get_db),
) -> Restaurant:
    restaurant = Restaurant(
        name=body.name,
        description=body.description,
        image_url=body.image_url,
        open_from=body.open_from,
        open_until=body.open_until,
    )
    db.add(restaurant)
    await db.flush()
    await db.refresh(restaurant)
    return restaurant


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
async def get_restaurant(
    restaurant_id: UUID, db: AsyncSession = Depends(get_db)
) -> Restaurant:
    result = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    restaurant = result.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


@router.patch("/{restaurant_id}", response_model=RestaurantResponse)
async def update_restaurant(
    restaurant_id: UUID,
    body: RestaurantUpdate,
    db: AsyncSession = Depends(get_db),
) -> Restaurant:
    result = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    restaurant = result.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(restaurant, key, value)
    await db.flush()
    await db.refresh(restaurant)
    return restaurant


@router.get("/{restaurant_id}/menu", response_model=list[MenuItemResponse])
async def get_restaurant_menu(
    restaurant_id: UUID, db: AsyncSession = Depends(get_db)
) -> list[MenuItem]:
    result = await db.execute(
        select(MenuItem)
        .where(MenuItem.restaurant_id == restaurant_id)
        .order_by(MenuItem.category, MenuItem.name)
        .options(selectinload(MenuItem.options))
    )
    return list(result.scalars().all())


@router.post("/{restaurant_id}/menu-items", response_model=MenuItemResponse)
async def create_restaurant_menu_item(
    restaurant_id: UUID,
    body: MenuItemCreate,
    db: AsyncSession = Depends(get_db),
) -> MenuItem:
    r = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    restaurant = r.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    item = MenuItem(
        restaurant_id=restaurant_id,
        name=body.name,
        description=body.description,
        price=body.price,
        category=body.category,
        image_url=body.image_url,
        allergens=body.allergens,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item
