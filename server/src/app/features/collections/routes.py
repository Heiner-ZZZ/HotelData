from __future__ import annotations

from fastapi import APIRouter

from src.app.features.collections.service import collection_counts


router = APIRouter()


@router.get("/collections")
def collections():
    return {"counts": collection_counts()}
