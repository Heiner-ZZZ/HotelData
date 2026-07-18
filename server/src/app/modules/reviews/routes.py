from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, status

from src.app.security.dependencies import get_current_user, require_permission
from src.app.security.hotel_filter import hotel_filter_from_user
from src.app.modules.reviews.schemas import (
    ModuleStatus, ReviewCreate, ReviewModeration,
    ReviewReportCreate, ReviewStaffResponse, ReviewUpdate,
)
from src.app.modules.reviews.service import (
    create_review,
    create_review_report,
    create_review_staff,
    create_review_guest,
    delete_review,
    get_hotel_reviews,
    get_reputation_dashboard,
    get_review,
    list_review_reports,
    list_reviews,
    moderate_review,
    module_status,
    respond_to_review,
    update_review,
)

router = APIRouter(prefix="/modules/reviews", tags=["modules-reviews"])
api_router = APIRouter(prefix="/api/reviews", tags=["reviews-api"])
public_router = APIRouter(prefix="/api/hotels", tags=["hotels-public"])


@router.get("/status", response_model=ModuleStatus)
def reviews_module_status():
    return module_status()


# RF-006: Public endpoint — top 5 approved reviews for a hotel
@public_router.get("/{prop_id}/reviews")
def hotel_reviews_api(prop_id: int = Path(..., ge=1)):
    """Return top 5 approved reviews for a hotel (public, no auth required)."""
    return get_hotel_reviews(prop_id, limit=5)


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
def moderate_review_api(
    review_id: str,
    payload: ReviewModeration = Body(...),
    current_user: dict = Depends(require_permission("reviews.moderate")),
):
    """RF-005: Moderate a review. Only marketing_hotelero and super_admin can moderate."""
    result = moderate_review(review_id, payload, current_user)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo moderar la reseña")
    return result


@api_router.patch("/{review_id}/respond")
def respond_review_api(
    review_id: str,
    payload: ReviewStaffResponse = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """RF-006: Respond to an approved review. Only hotel_partner of that hotel can respond."""
    # First check user is logged in
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Debe iniciar sesión")
    # Verify the user is a hotel_partner or super_admin
    role = current_user.get("primary_role", "")
    if role not in ("hotel_partner", "super_admin", "admin_sistema"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo hotel_partner puede responder reseñas",
        )
    result = respond_to_review(review_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada o no se puede responder (solo reseñas aprobadas)")
    return result


@api_router.put("/{review_id}")
def update_review_api(
    review_id: str,
    payload: ReviewUpdate = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """Edit a review by its author (only while moderation_status is 'pending')."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Debe iniciar sesión")
    user_id = str(current_user.get("_id", ""))
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no identificado")
    result = update_review(review_id, user_id, payload)
    if result is None:
        # Determine why it failed (not found, not owner, not pending)
        from bson import ObjectId
        from src.database.connection import get_database
        db = get_database()
        try:
            existing = db.reviews.find_one({"_id": ObjectId(review_id)}, {"user_id": 1, "moderation_status": 1})
        except Exception:
            existing = None
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada")
        if str(existing.get("user_id", "")) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el autor puede editar esta reseña")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo se puede editar una reseña en estado 'pending'")
    return result


@api_router.post("/{review_id}/report", status_code=201)
def create_review_report_api(
    review_id: str,
    payload: ReviewReportCreate = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """Report a review for inappropriate content. Any authenticated user can report."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Debe iniciar sesión")
    user_id = str(current_user.get("_id", ""))
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no identificado")
    result = create_review_report(review_id, user_id, payload)
    if result is None:
        # Determine why it failed
        from bson import ObjectId
        from src.database.connection import get_database
        db = get_database()
        try:
            existing = db.reviews.find_one({"_id": ObjectId(review_id)}, {"_id": 1})
        except Exception:
            existing = None
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada")
        # Already reported by this user
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya has reportado esta reseña anteriormente",
        )
    return result


@api_router.get("/reports")
def list_review_reports_api(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """List review reports (staff: marketing_hotelero, super_admin). Requires authentication."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Debe iniciar sesión")
    return list_review_reports(status=status, page=page, page_size=page_size)


@api_router.get("/reputation/dashboard")
def reputation_dashboard_api(
    prop_id: int | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
):
    """Return reputation dashboard data: GRI, departmental sentiment, recent feedback."""
    return get_reputation_dashboard(prop_id=prop_id, days=days)


@api_router.delete("/{review_id}", status_code=204)
def delete_review_api(review_id: str):
    deleted = delete_review(review_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada")
