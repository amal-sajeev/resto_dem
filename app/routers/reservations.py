"""
Reservation router: create, list, confirm (QR), cancel, update status, QR image, slots.
"""

import io
import secrets
from datetime import date, datetime, time
from typing import Optional
from uuid import UUID

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, get_optional_user, require_role
from app.database import get_db
from app.encryption import decrypt
from app.models import Reservation, ReservationStatus, Restaurant, Table, User, UserRole
from app.schemas import ReservationCreate, ReservationResponse, ReservationStatusUpdate, SlotsResponse

router = APIRouter(prefix="/reservations", tags=["reservations"])


def _reservation_response(r: Reservation) -> ReservationResponse:
    user_name = None
    if r.user:
        try:
            user_name = decrypt(r.user.encrypted_name)
        except Exception:
            user_name = "Unknown"
    return ReservationResponse(
        id=r.id,
        user_id=r.user_id,
        restaurant_id=r.restaurant_id,
        table_id=r.table_id,
        reservation_date=r.reservation_date,
        reservation_time=r.reservation_time,
        party_size=r.party_size,
        status=r.status,
        confirmation_code=r.confirmation_code,
        notes=r.notes,
        created_at=r.created_at,
        user_name=user_name,
        restaurant_name=r.restaurant.name if r.restaurant else None,
        table_number=r.table.table_number if r.table else None,
    )


def _generate_slots(open_from: time, open_until: time) -> list[str]:
    """Generate 1-hour slot labels from opening to closing (last slot starts before close)."""
    start_hour = open_from.hour
    end_hour = open_until.hour
    if open_until.minute > 0:
        end_hour += 1
    # Cap at 23 so we don't generate hour 24
    end_hour = min(end_hour, 24)
    return [f"{h:02d}:00" for h in range(start_hour, end_hour)]


@router.get("/slots", response_model=SlotsResponse)
async def get_slots(
    restaurant_id: UUID = Query(...),
    date_val: date = Query(..., alias="date"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    restaurant = result.scalar_one_or_none()
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    if not restaurant.open_from or not restaurant.open_until:
        return SlotsResponse(slots=[], booked={})

    slots = _generate_slots(restaurant.open_from, restaurant.open_until)

    # Find all active reservations for this restaurant on this date
    res = await db.execute(
        select(Reservation).where(
            Reservation.restaurant_id == restaurant_id,
            Reservation.reservation_date == date_val,
            Reservation.status.notin_([ReservationStatus.cancelled, ReservationStatus.no_show]),
        )
    )
    reservations = res.scalars().all()

    booked: dict[str, list[UUID]] = {}
    for r in reservations:
        slot_key = f"{r.reservation_time.hour:02d}:00"
        booked.setdefault(slot_key, []).append(r.table_id)

    return SlotsResponse(slots=slots, booked=booked)


@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    body: ReservationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify table exists and belongs to the restaurant
    result = await db.execute(select(Table).where(Table.id == body.table_id, Table.is_active == True))  # noqa: E712
    table = result.scalar_one_or_none()
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found or inactive")
    if table.restaurant_id != body.restaurant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Table does not belong to this restaurant")
    if body.party_size > table.capacity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Party size exceeds table capacity")

    # Validate the slot falls within restaurant operating hours
    rest_result = await db.execute(select(Restaurant).where(Restaurant.id == body.restaurant_id))
    restaurant = rest_result.scalar_one_or_none()
    if restaurant and restaurant.open_from and restaurant.open_until:
        valid_slots = _generate_slots(restaurant.open_from, restaurant.open_until)
        slot_str = f"{body.reservation_time.hour:02d}:00"
        if slot_str not in valid_slots:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Time slot {slot_str} is outside operating hours ({restaurant.open_from.strftime('%H:%M')}–{restaurant.open_until.strftime('%H:%M')})",
            )

    # Exact slot conflict: same table + date + hour
    existing = await db.execute(
        select(Reservation).where(
            Reservation.table_id == body.table_id,
            Reservation.reservation_date == body.reservation_date,
            Reservation.reservation_time == body.reservation_time,
            Reservation.status.notin_([ReservationStatus.cancelled, ReservationStatus.no_show]),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Table is already reserved for this time slot")

    confirmation_code = secrets.token_urlsafe(16)

    reservation = Reservation(
        user_id=user.id,
        restaurant_id=body.restaurant_id,
        table_id=body.table_id,
        reservation_date=body.reservation_date,
        reservation_time=body.reservation_time,
        party_size=body.party_size,
        confirmation_code=confirmation_code,
        notes=body.notes,
    )
    db.add(reservation)
    await db.flush()

    result = await db.execute(
        select(Reservation)
        .where(Reservation.id == reservation.id)
        .options(selectinload(Reservation.user), selectinload(Reservation.restaurant), selectinload(Reservation.table))
    )
    reservation = result.scalar_one()
    return _reservation_response(reservation)


@router.get("", response_model=list[ReservationResponse])
async def list_reservations(
    restaurant_id: Optional[UUID] = Query(None),
    reservation_date: Optional[date] = Query(None),
    status_filter: Optional[ReservationStatus] = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Reservation).options(
        selectinload(Reservation.user),
        selectinload(Reservation.restaurant),
        selectinload(Reservation.table),
    )

    if user.role == UserRole.normal_user:
        q = q.where(Reservation.user_id == user.id)
    elif user.role == UserRole.restaurant_admin and user.restaurant_id:
        q = q.where(Reservation.restaurant_id == user.restaurant_id)
    elif user.role == UserRole.supervisor and user.restaurant_id:
        q = q.where(Reservation.restaurant_id == user.restaurant_id)

    if restaurant_id:
        q = q.where(Reservation.restaurant_id == restaurant_id)
    if reservation_date:
        q = q.where(Reservation.reservation_date == reservation_date)
    if status_filter:
        q = q.where(Reservation.status == status_filter)

    q = q.order_by(Reservation.reservation_date.desc(), Reservation.reservation_time.desc())
    result = await db.execute(q)
    return [_reservation_response(r) for r in result.scalars().all()]


@router.get("/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .options(selectinload(Reservation.user), selectinload(Reservation.restaurant), selectinload(Reservation.table))
    )
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if user.role == UserRole.normal_user and reservation.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your reservation")

    return _reservation_response(reservation)


@router.patch("/{reservation_id}/cancel", response_model=ReservationResponse)
async def cancel_reservation(
    reservation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .options(selectinload(Reservation.user), selectinload(Reservation.restaurant), selectinload(Reservation.table))
    )
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if user.role == UserRole.normal_user and reservation.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your reservation")

    reservation.status = ReservationStatus.cancelled
    await db.flush()
    return _reservation_response(reservation)


@router.post("/confirm/{confirmation_code}", response_model=ReservationResponse)
async def confirm_reservation(
    confirmation_code: str,
    user: User = Depends(require_role(UserRole.supervisor, UserRole.restaurant_admin, UserRole.establishment_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reservation)
        .where(Reservation.confirmation_code == confirmation_code)
        .options(selectinload(Reservation.user), selectinload(Reservation.restaurant), selectinload(Reservation.table))
    )
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if reservation.status != ReservationStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reservation is already {reservation.status.value}",
        )

    reservation.status = ReservationStatus.confirmed
    await db.flush()
    return _reservation_response(reservation)


@router.patch("/{reservation_id}/status", response_model=ReservationResponse)
async def update_reservation_status(
    reservation_id: UUID,
    body: ReservationStatusUpdate,
    user: User = Depends(require_role(UserRole.supervisor, UserRole.restaurant_admin, UserRole.establishment_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .options(selectinload(Reservation.user), selectinload(Reservation.restaurant), selectinload(Reservation.table))
    )
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    reservation.status = body.status
    await db.flush()
    return _reservation_response(reservation)


@router.get("/{reservation_id}/qr")
async def get_reservation_qr(
    reservation_id: UUID,
    request: Request,
    token: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    # Browsers can't send Authorization headers on <img src>, so accept token as query param
    if user is None and token:
        from jose import JWTError, jwt as jose_jwt
        from app.config import settings as _settings
        try:
            payload = jose_jwt.decode(token, _settings.JWT_SECRET_KEY, algorithms=["HS256"])
            uid = payload.get("sub")
            if uid:
                res = await db.execute(select(User).where(User.id == UUID(uid)))
                user = res.scalar_one_or_none()
        except JWTError:
            pass
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if user.role == UserRole.normal_user and reservation.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your reservation")

    base_url = str(request.base_url).rstrip("/")
    qr_data = f"{base_url}/api/reservations/confirm/{reservation.confirmation_code}"

    img = qrcode.make(qr_data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")
