"""
Admin router: staff account management (establishment admin only).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.database import get_db
from app.encryption import decrypt, encrypt
from app.models import User, UserRole
from app.schemas import StaffCreate, StaffResponse, StaffUpdate

router = APIRouter(prefix="/admin", tags=["admin"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _staff_response(user: User) -> StaffResponse:
    return StaffResponse(
        id=user.id,
        name=decrypt(user.encrypted_name),
        email=decrypt(user.encrypted_email) if user.encrypted_email else None,
        role=user.role,
        restaurant_id=user.restaurant_id,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/staff", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    body: StaffCreate,
    admin: User = Depends(require_role(UserRole.establishment_admin)),
    db: AsyncSession = Depends(get_db),
):
    if body.role == UserRole.normal_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use OTP signup for normal users")

    user = User(
        encrypted_name=encrypt(body.name),
        encrypted_email=encrypt(body.email),
        password_hash=pwd_context.hash(body.password),
        role=body.role,
        restaurant_id=body.restaurant_id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return _staff_response(user)


@router.get("/staff", response_model=list[StaffResponse])
async def list_staff(
    admin: User = Depends(require_role(UserRole.establishment_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.role.in_([
                UserRole.establishment_admin,
                UserRole.restaurant_admin,
                UserRole.supervisor,
            ])
        ).order_by(User.created_at)
    )
    return [_staff_response(u) for u in result.scalars().all()]


@router.patch("/staff/{user_id}", response_model=StaffResponse)
async def update_staff(
    user_id: UUID,
    body: StaffUpdate,
    admin: User = Depends(require_role(UserRole.establishment_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")

    if body.name is not None:
        user.encrypted_name = encrypt(body.name)
    if body.email is not None:
        user.encrypted_email = encrypt(body.email)
    if body.role is not None:
        user.role = body.role
    if body.restaurant_id is not None:
        user.restaurant_id = body.restaurant_id
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.flush()
    await db.refresh(user)
    return _staff_response(user)


@router.delete("/staff/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_staff(
    user_id: UUID,
    admin: User = Depends(require_role(UserRole.establishment_admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")

    user.is_active = False
    await db.flush()
