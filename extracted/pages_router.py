"""
Add this router to app/routers/pages.py
Then register it in app/main.py with:

    from app.routers import pages
    app.include_router(pages.router)
    app.mount("/static", StaticFiles(directory="static"), name="static")

Also place room.html and kitchen.html inside a  templates/  folder at the project root.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["pages"])

TEMPLATES = Path(__file__).parent.parent.parent / "templates"


def _read(name: str) -> str:
    return (TEMPLATES / name).read_text()


@router.get("/room/{room_id}", response_class=HTMLResponse)
async def room_page(room_id: str) -> HTMLResponse:
    return HTMLResponse(_read("room.html"))


@router.get("/kitchen", response_class=HTMLResponse)
async def kitchen_page() -> HTMLResponse:
    return HTMLResponse(_read("kitchen.html"))
