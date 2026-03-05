"""
Subdomain-based tenant resolution middleware.

Extracts the establishment slug from the Host header subdomain and loads
the corresponding Establishment into request.state for downstream use.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.models import Establishment


_SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class EstablishmentMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.establishment = None
        request.state.establishment_id = None
        request.state.is_superadmin_panel = False

        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        slug = self._extract_slug(request)

        if slug is None:
            return await call_next(request)

        if slug == settings.SUPERADMIN_SUBDOMAIN:
            request.state.is_superadmin_panel = True
            return await call_next(request)

        if slug in ("www", ""):
            return await call_next(request)

        async with async_session_maker() as session:
            result = await session.execute(
                select(Establishment).where(Establishment.slug == slug)
            )
            establishment = result.scalar_one_or_none()

        if establishment is None:
            return JSONResponse(
                status_code=404,
                content={"detail": f"Establishment '{slug}' not found"},
            )
        if not establishment.is_active:
            return JSONResponse(
                status_code=403,
                content={"detail": "This establishment is currently inactive"},
            )

        request.state.establishment = establishment
        request.state.establishment_id = establishment.id
        return await call_next(request)

    def _extract_slug(self, request: Request):
        dev_slug = request.headers.get("x-establishment-slug")
        if dev_slug:
            return dev_slug.lower().strip()

        host = request.headers.get("host", "")
        host = host.split(":")[0]

        base = settings.BASE_DOMAIN.lower()
        if not host.endswith(base):
            return None

        prefix = host[: -len(base)].rstrip(".")
        if not prefix:
            return None

        parts = prefix.split(".")
        return parts[0] if parts else None
