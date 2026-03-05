"""
JWT token creation and FastAPI dependencies for authentication / authorization.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User, UserRole

_bearer = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


def create_access_token(
    user_id: UUID,
    role: UserRole,
    restaurant_id: Optional[UUID] = None,
    establishment_id: Optional[UUID] = None,
) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "exp": expire,
    }
    if restaurant_id:
        payload["rid"] = str(restaurant_id)
    if establishment_id:
        payload["eid"] = str(establishment_id)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


async def get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Returns the current user if a valid token is present, otherwise None."""
    if creds is None:
        return None
    try:
        payload = jwt.decode(creds.credentials, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


async def get_current_superadmin(
    user: User = Depends(get_current_user),
) -> User:
    """Dependency that ensures the current user is a superadmin."""
    if user.role != UserRole.superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")
    return user


def require_role(*roles: UserRole):
    """Dependency factory: ensures the current user has one of the given roles.
    Superadmins are always allowed."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role == UserRole.superadmin:
            return user
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return _check


def get_establishment_id(request: Request) -> UUID:
    """Extract establishment_id from the request state (set by middleware).
    Raises 400 if not resolved."""
    eid = getattr(request.state, "establishment_id", None)
    if eid is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Establishment context required (use a valid subdomain or X-Establishment-Slug header)",
        )
    return eid
