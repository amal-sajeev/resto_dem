"""
Branding router: public GET for theme/logo, admin PATCH to update branding.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_establishment_id, require_role
from app.database import get_db
from app.models import Establishment, User, UserRole
from app.schemas import BrandingResponse, BrandingUpdate

router = APIRouter(prefix="/branding", tags=["branding"])

VALID_ROOM_THEMES = {"noir-gold", "ivory-elegance", "midnight-blue", "clean-minimal", "emerald-dark", "custom"}
VALID_KITCHEN_THEMES = {"kds-classic", "kds-bright", "kds-midnight", "kds-paper", "custom"}


@router.get("", response_model=BrandingResponse)
async def get_branding(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    est_id = get_establishment_id(request)
    result = await db.execute(select(Establishment).where(Establishment.id == est_id))
    est = result.scalar_one_or_none()
    if est is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Establishment not found")
    return BrandingResponse(
        name=est.name,
        logo_url=est.logo_url,
        room_theme=est.room_theme,
        kitchen_theme=est.kitchen_theme,
        custom_room_colors=est.custom_room_colors,
        custom_kitchen_colors=est.custom_kitchen_colors,
    )


@router.patch("", response_model=BrandingResponse)
async def update_branding(
    body: BrandingUpdate,
    request: Request,
    user: User = Depends(require_role(UserRole.establishment_admin)),
    db: AsyncSession = Depends(get_db),
):
    est_id = get_establishment_id(request)
    result = await db.execute(select(Establishment).where(Establishment.id == est_id))
    est = result.scalar_one_or_none()
    if est is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Establishment not found")

    if user.role != UserRole.superadmin and user.establishment_id != est_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify another establishment's branding")

    if body.name is not None:
        est.name = body.name
    if body.logo_url is not None:
        est.logo_url = body.logo_url
    if body.room_theme is not None:
        if body.room_theme not in VALID_ROOM_THEMES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid room theme. Choose from: {VALID_ROOM_THEMES}")
        est.room_theme = body.room_theme
    if body.kitchen_theme is not None:
        if body.kitchen_theme not in VALID_KITCHEN_THEMES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid kitchen theme. Choose from: {VALID_KITCHEN_THEMES}")
        est.kitchen_theme = body.kitchen_theme
    if body.custom_room_colors is not None:
        est.custom_room_colors = body.custom_room_colors
    if body.custom_kitchen_colors is not None:
        est.custom_kitchen_colors = body.custom_kitchen_colors

    await db.flush()
    await db.refresh(est)
    return BrandingResponse(
        name=est.name,
        logo_url=est.logo_url,
        room_theme=est.room_theme,
        kitchen_theme=est.kitchen_theme,
        custom_room_colors=est.custom_room_colors,
        custom_kitchen_colors=est.custom_kitchen_colors,
    )
