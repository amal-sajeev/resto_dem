"""
Serve guest and kitchen HTML pages. Templates live in project_root/templates.
"""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["pages"])

# From app/routers/pages.py -> app/routers -> app -> project root -> templates
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def _read_html(name: str) -> str:
    path = TEMPLATES_DIR / name
    if not path.is_file():
        return f"<html><body><h1>Not found: {name}</h1></body></html>"
    return path.read_text(encoding="utf-8")


@router.get("/room/{room_id}", response_class=HTMLResponse)
async def room_page(room_id: str) -> HTMLResponse:
    """Guest ordering page for a room. URL is /room/{room_id} so the page can read room from path."""
    return HTMLResponse(_read_html("room.html"))


@router.get("/kitchen", response_class=HTMLResponse)
async def kitchen_page() -> HTMLResponse:
    """Kitchen display: orders by restaurant, status updates."""
    return HTMLResponse(_read_html("kitchen.html"))
