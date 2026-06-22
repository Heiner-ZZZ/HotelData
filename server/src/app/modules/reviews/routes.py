from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Query, Request, status

from src.app.modules.reviews.schemas import ModuleStatus, ReviewCreate, ReviewModeration, ReviewStaffResponse
from src.app.modules.reviews.service import (
    create_review,
    delete_review,
    ensure_reviews_collections,
    get_review,
    list_reviews,
    moderate_review,
    module_status,
    respond_to_review,
)

router = APIRouter(prefix="/modules/reviews", tags=["modules-reviews"])
api_router = APIRouter(prefix="/api/reviews", tags=["reviews-api"])


@router.get("/status", response_model=ModuleStatus)
def reviews_module_status():
    return module_status()


@api_router.post("/", status_code=201)
def create_review_api(user_id: str = Query(...), payload: dict = Body(...)):
    parsed = ReviewCreate(**payload)
    result = create_review(user_id, parsed)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear la reseña (booking inválido o ya reseñado)")
    return result


@api_router.get("/")
def list_reviews_api(
    prop_id: int | None = Query(default=None),
    user_id: str | None = Query(default=None),
    moderation_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    return list_reviews(
        prop_id=prop_id,
        user_id=user_id,
        moderation_status=moderation_status,
        page=page,
        page_size=page_size,
    )


@api_router.get("/{review_id}")
def get_review_api(review_id: str):
    result = get_review(review_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada")
    return result


@api_router.patch("/{review_id}/moderate")
def moderate_review_api(review_id: str, payload: ReviewModeration = Body(...)):
    result = moderate_review(review_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo moderar la reseña")
    return result


@api_router.patch("/{review_id}/respond")
def respond_review_api(review_id: str, payload: ReviewStaffResponse = Body(...)):
    result = respond_to_review(review_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada")
    return result


@api_router.delete("/{review_id}", status_code=204)
def delete_review_api(review_id: str):
    deleted = delete_review(review_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada")
