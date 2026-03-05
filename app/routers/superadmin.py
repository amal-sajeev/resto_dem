"""
Superadmin router: manage establishments, seed admins, view global stats.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_superadmin
from app.database import get_db
from app.encryption import encrypt
from app.models import Establishment, Order, Restaurant, User, UserRole
from app.schemas import (
    EstablishmentCreate,
    EstablishmentResponse,
    EstablishmentStats,
    EstablishmentUpdate,
    SeedAdminCreate,
    StaffResponse,
)

router = APIRouter(prefix="/superadmin", tags=["superadmin"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/establishments", response_model=list[EstablishmentResponse])
async def list_establishments(
    _: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Establishment).order_by(Establishment.created_at.desc()))
    return list(result.scalars().all())


@router.post("/establishments", response_model=EstablishmentResponse, status_code=status.HTTP_201_CREATED)
async def create_establishment(
    body: EstablishmentCreate,
    _: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Establishment).where(Establishment.slug == body.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")

    est = Establishment(name=body.name, slug=body.slug)
    db.add(est)
    await db.flush()
    await db.refresh(est)
    return est


@router.get("/establishments/{est_id}", response_model=EstablishmentResponse)
async def get_establishment(
    est_id: UUID,
    _: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Establishment).where(Establishment.id == est_id))
    est = result.scalar_one_or_none()
    if est is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Establishment not found")
    return est


@router.patch("/establishments/{est_id}", response_model=EstablishmentResponse)
async def update_establishment(
    est_id: UUID,
    body: EstablishmentUpdate,
    _: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Establishment).where(Establishment.id == est_id))
    est = result.scalar_one_or_none()
    if est is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Establishment not found")

    if body.name is not None:
        est.name = body.name
    if body.slug is not None:
        dup = await db.execute(
            select(Establishment).where(Establishment.slug == body.slug, Establishment.id != est_id)
        )
        if dup.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
        est.slug = body.slug
    if body.is_active is not None:
        est.is_active = body.is_active

    await db.flush()
    await db.refresh(est)
    return est


@router.post("/establishments/{est_id}/seed-admin", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def seed_admin(
    est_id: UUID,
    body: SeedAdminCreate,
    _: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Establishment).where(Establishment.id == est_id))
    est = result.scalar_one_or_none()
    if est is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Establishment not found")

    user = User(
        establishment_id=est.id,
        encrypted_name=encrypt(body.name),
        encrypted_email=encrypt(body.email),
        password_hash=pwd_context.hash(body.password),
        role=UserRole.establishment_admin,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return StaffResponse(
        id=user.id,
        name=body.name,
        email=body.email,
        role=user.role,
        establishment_id=user.establishment_id,
        restaurant_id=user.restaurant_id,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("/stats", response_model=EstablishmentStats)
async def get_stats(
    _: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    total_est = (await db.execute(select(func.count(Establishment.id)))).scalar() or 0
    active_est = (await db.execute(
        select(func.count(Establishment.id)).where(Establishment.is_active == True)  # noqa: E712
    )).scalar() or 0
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    total_restaurants = (await db.execute(select(func.count(Restaurant.id)))).scalar() or 0

    return EstablishmentStats(
        total_establishments=total_est,
        active_establishments=active_est,
        total_orders=total_orders,
        total_restaurants=total_restaurants,
    )
