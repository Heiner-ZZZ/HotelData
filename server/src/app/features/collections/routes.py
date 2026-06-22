from __future__ import annotations

from fastapi import APIRouter, Request
from src.app.template_utils import templates

from src.app.features.collections.service import collection_counts


router = APIRouter()


@router.get("/collections")
def collections(request: Request):
    return templates.TemplateResponse(
        request,
        "collections/index.html",
        {"counts": collection_counts()},
    )
