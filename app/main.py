from fastapi import FastAPI

from app.middleware import EstablishmentMiddleware
from app.routers import admin, auth, branding, kitchen, menu_items, orders, pages, reservations, restaurants, rooms, superadmin, tables

app = FastAPI(
    title="White-Label Multi-Restaurant Ordering API",
    description="Multi-tenant backend for QR-based in-room ordering. Each establishment runs on its own subdomain.",
    version="0.2.0",
)

app.add_middleware(EstablishmentMiddleware)

app.include_router(restaurants.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(kitchen.router, prefix="/api")
app.include_router(menu_items.router, prefix="/api")
app.include_router(rooms.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(tables.router, prefix="/api")
app.include_router(reservations.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(branding.router, prefix="/api")
app.include_router(superadmin.router, prefix="/api")

app.include_router(pages.router)


@app.get("/")
async def root() -> dict:
    return {
        "message": "White-label ordering API",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health")
async def health() -> dict:
    from sqlalchemy import text
    from app.database import engine
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
