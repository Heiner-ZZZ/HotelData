from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.app.features.collections.service import collection_counts


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))
templates.env.cache = None


@router.get("/collections")
def collections(request: Request):
    return templates.TemplateResponse(
        request,
        "collections/index.html",
        {"counts": collection_counts()},
    )
