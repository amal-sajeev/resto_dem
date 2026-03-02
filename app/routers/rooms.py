from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Room
from app.schemas import RoomCreate, RoomResponse

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomResponse])
async def list_rooms(db: AsyncSession = Depends(get_db)) -> list[Room]:
    result = await db.execute(select(Room).order_by(Room.room_number))
    return list(result.scalars().all())


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room_by_number(
    room_id: str,
    db: AsyncSession = Depends(get_db),
) -> Room:
    result = await db.execute(select(Room).where(Room.room_number == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.post("", response_model=RoomResponse)
async def create_room(
    body: RoomCreate,
    db: AsyncSession = Depends(get_db),
) -> Room:
    existing = await db.execute(select(Room).where(Room.room_number == body.room_number))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Room number already exists")
    room = Room(room_number=body.room_number, display_name=body.display_name)
    db.add(room)
    await db.flush()
    await db.refresh(room)
    return room
