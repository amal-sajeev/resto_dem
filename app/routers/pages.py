"""
Serve HTML pages. Templates live in project_root/templates.
"""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["pages"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def _read_html(name: str) -> str:
    path = TEMPLATES_DIR / name
    if not path.is_file():
        return f"<html><body><h1>Not found: {name}</h1></body></html>"
    return path.read_text(encoding="utf-8")


@router.get("/room/{room_id}", response_class=HTMLResponse)
async def room_page(room_id: str) -> HTMLResponse:
    return HTMLResponse(_read_html("room.html"))


@router.get("/kitchen", response_class=HTMLResponse)
async def kitchen_page() -> HTMLResponse:
    return HTMLResponse(_read_html("kitchen.html"))


@router.get("/login", response_class=HTMLResponse)
async def login_page() -> HTMLResponse:
    return HTMLResponse(_read_html("login.html"))


@router.get("/reserve", response_class=HTMLResponse)
async def reserve_page() -> HTMLResponse:
    return HTMLResponse(_read_html("reserve.html"))


@router.get("/admin", response_class=HTMLResponse)
async def admin_page() -> HTMLResponse:
    return HTMLResponse(_read_html("admin.html"))


@router.get("/scanner", response_class=HTMLResponse)
async def scanner_page() -> HTMLResponse:
    return HTMLResponse(_read_html("scanner.html"))


@router.get("/superadmin", response_class=HTMLResponse)
async def superadmin_page(request: Request) -> HTMLResponse:
    return HTMLResponse(_read_html("superadmin.html"))
