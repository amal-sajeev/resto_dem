from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_establishment_id
from app.database import get_db
from app.models import Room
from app.schemas import RoomCreate, RoomResponse

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomResponse])
async def list_rooms(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list[Room]:
    est_id = get_establishment_id(request)
    result = await db.execute(
        select(Room)
        .where(Room.establishment_id == est_id)
        .order_by(Room.room_number)
    )
    return list(result.scalars().all())


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room_by_number(
    room_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Room:
    est_id = get_establishment_id(request)
    result = await db.execute(
        select(Room).where(Room.room_number == room_id, Room.establishment_id == est_id)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.post("", response_model=RoomResponse)
async def create_room(
    body: RoomCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Room:
    est_id = get_establishment_id(request)
    existing = await db.execute(
        select(Room).where(Room.room_number == body.room_number, Room.establishment_id == est_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Room number already exists")
    room = Room(
        establishment_id=est_id,
        room_number=body.room_number,
        display_name=body.display_name,
    )
    db.add(room)
    await db.flush()
    await db.refresh(room)
    return room
