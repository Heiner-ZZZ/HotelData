from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status

from src.app.security.dependencies import get_current_user
from src.app.security.hotel_filter import hotel_filter_from_user
from src.app.modules.reviews.schemas import ModuleStatus, ReviewCreate, ReviewModeration, ReviewStaffResponse
from src.app.modules.reviews.service import (
    create_review,
    create_review_staff,
    create_review_guest,
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


@api_router.post("", status_code=201)
def create_review_api(user_id: str = Query(...), payload: dict = Body(...)):
    parsed = ReviewCreate(**payload)
    result = create_review(user_id, parsed)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear la reseña (booking inválido o ya reseñado)")
    return result


@api_router.post("/staff", status_code=201)
def create_review_staff_api(payload: dict = Body(...)):
    """Create a review on behalf of a guest (staff-assisted, e.g. during check-out).
    Resolves the guest's user_id from the booking automatically.
    """
    parsed = ReviewCreate(**payload)
    result = create_review_staff(parsed)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear la reseña (booking inválido o ya reseñado)")
    return result


@api_router.post("/guest", status_code=201)
def create_review_guest_api(payload: dict = Body(...)):
    """Create a review on behalf of an unauthenticated guest."""
    parsed = ReviewCreate(**payload)
    result = create_review_guest(parsed)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear la reseña (booking inválido o ya reseñado)")
    return result


@api_router.get("")
def list_reviews_api(
    request: Request,
    prop_id: int | None = Query(default=None),
    user_id: str | None = Query(default=None),
    moderation_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict | None = Depends(get_current_user),
):
    # Apply RBAC hotel filter: hotel_partner/gerente_hotel only see their hotels
    hotel_filter = hotel_filter_from_user(current_user)
    # If the user explicitly passed a prop_id that doesn't match their filter, override
    if prop_id is not None:
        hotel_filter = {"prop_id": prop_id}
    return list_reviews(
        hotel_filter=hotel_filter,
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
