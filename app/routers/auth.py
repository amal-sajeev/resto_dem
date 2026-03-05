"""
Authentication router: phone OTP for normal users, email+password for staff.
Establishment-scoped for staff login.
"""

import random
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_current_user, get_establishment_id
from app.config import settings
from app.database import get_db
from app.encryption import decrypt, encrypt, phone_hash
from app.models import OTPCode, User, UserRole
from app.schemas import AuthResponse, OTPRequest, OTPVerify, StaffLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=decrypt(user.encrypted_name),
        phone=decrypt(user.encrypted_phone) if user.encrypted_phone else None,
        email=decrypt(user.encrypted_email) if user.encrypted_email else None,
        role=user.role,
        establishment_id=user.establishment_id,
        restaurant_id=user.restaurant_id,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/otp/request", status_code=status.HTTP_200_OK)
async def request_otp(body: OTPRequest, db: AsyncSession = Depends(get_db)):
    ph = phone_hash(body.phone)

    await db.execute(
        select(OTPCode)
        .where(OTPCode.phone_hash == ph, OTPCode.is_used == False)  # noqa: E712
    )

    code = _generate_otp()
    expires = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

    otp = OTPCode(phone_hash=ph, code=code, expires_at=expires)
    db.add(otp)
    await db.flush()

    print(f"[OTP] Phone {body.phone} -> code {code} (expires {expires.isoformat()})")

    return {"message": "OTP sent", "expires_in_seconds": settings.OTP_EXPIRY_MINUTES * 60, "demo_code": code}


@router.post("/otp/verify", response_model=AuthResponse)
async def verify_otp(body: OTPVerify, db: AsyncSession = Depends(get_db)):
    ph = phone_hash(body.phone)

    result = await db.execute(
        select(OTPCode)
        .where(
            OTPCode.phone_hash == ph,
            OTPCode.is_used == False,  # noqa: E712
            OTPCode.expires_at > datetime.utcnow(),
        )
        .order_by(OTPCode.expires_at.desc())
        .limit(1)
    )
    otp = result.scalar_one_or_none()
    if otp is None or otp.code != body.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")

    otp.is_used = True

    user_result = await db.execute(select(User).where(User.phone_hash == ph))
    user = user_result.scalar_one_or_none()

    if user is None:
        name = body.name or "Guest"
        user = User(
            encrypted_name=encrypt(name),
            encrypted_phone=encrypt(body.phone),
            phone_hash=ph,
            role=UserRole.normal_user,
        )
        db.add(user)
        await db.flush()
    elif body.name:
        user.encrypted_name = encrypt(body.name)
        await db.flush()

    token = create_access_token(user.id, user.role, user.restaurant_id, user.establishment_id)
    return AuthResponse(access_token=token, user=_user_response(user))


@router.post("/login", response_model=AuthResponse)
async def staff_login(body: StaffLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """Email + password login for staff accounts. Scoped to the current establishment."""
    est_id = getattr(request.state, "establishment_id", None)

    q = select(User).where(
        User.role.in_([
            UserRole.establishment_admin,
            UserRole.restaurant_admin,
            UserRole.supervisor,
        ]),
        User.is_active == True,  # noqa: E712
    )
    if est_id is not None:
        q = q.where(User.establishment_id == est_id)

    result = await db.execute(q)
    users = result.scalars().all()

    matched_user = None
    for u in users:
        if u.encrypted_email:
            try:
                if decrypt(u.encrypted_email) == body.email:
                    matched_user = u
                    break
            except Exception:
                continue

    if matched_user is None or not matched_user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not pwd_context.verify(body.password, matched_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(
        matched_user.id, matched_user.role, matched_user.restaurant_id, matched_user.establishment_id
    )
    return AuthResponse(access_token=token, user=_user_response(matched_user))


@router.post("/superadmin-login", response_model=AuthResponse)
async def superadmin_login(body: StaffLogin, db: AsyncSession = Depends(get_db)):
    """Login endpoint for superadmins (not scoped to any establishment)."""
    result = await db.execute(
        select(User).where(User.role == UserRole.superadmin, User.is_active == True)  # noqa: E712
    )
    users = result.scalars().all()

    matched_user = None
    for u in users:
        if u.encrypted_email:
            try:
                if decrypt(u.encrypted_email) == body.email:
                    matched_user = u
                    break
            except Exception:
                continue

    if matched_user is None or not matched_user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not pwd_context.verify(body.password, matched_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(matched_user.id, matched_user.role)
    return AuthResponse(access_token=token, user=_user_response(matched_user))


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return _user_response(user)
