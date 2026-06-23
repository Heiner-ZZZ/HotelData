from __future__ import annotations

from fastapi import APIRouter

from src.app.features.quality.service import quality_summary


router = APIRouter()


@router.get("/problems")
def problems():
    return {"quality": quality_summary()}
