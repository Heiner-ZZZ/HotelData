from __future__ import annotations

from fastapi import APIRouter


router = APIRouter()


@router.get("/company")
def company():
    return {"ok": True, "message": "Company page"}
