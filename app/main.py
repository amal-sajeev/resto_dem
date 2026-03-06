from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import admin, auth, kitchen, menu_items, orders, pages, reservations, restaurants, rooms, tables

app = FastAPI(
    title="Royal Dine API",
    description="Backend for QR-based in-room ordering from multiple hotel restaurants.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent.parent / "static"), name="static")

app.include_router(restaurants.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(kitchen.router, prefix="/api")
app.include_router(menu_items.router, prefix="/api")
app.include_router(rooms.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(tables.router, prefix="/api")
app.include_router(reservations.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

# HTML pages
app.include_router(pages.router)


@app.get("/")
async def root() -> dict:
    return {
        "message": "Royal Dine API",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "guest": "/room/101",
        "kitchen": "/kitchen",
        "login": "/login",
        "reserve": "/reserve",
        "admin": "/admin",
        "scanner": "/scanner",
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
