from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, status

from src.app.security.dependencies import require_login, require_permission, require_prop_permission
from src.app.security.hotel_filter import hotel_filter_from_user, user_can_access_hotel
from src.app.security.permissions import user_has_permission
from src.app.security.role_helpers import get_role_name
from src.database.connection import get_database
from src.app.modules.reviews.schemas import (
    ModuleStatus, ReviewCreate, ReviewListResponse, ReviewModeration,
    ReviewReportCreate, ReviewResponse, ReviewStaffResponse, ReviewUpdate,
)
from src.app.modules.reviews.service import (
    create_review,
    create_review_report,
    create_review_staff,
    create_review_guest,
    delete_review,
    get_hotel_reviews,
    get_reputation_dashboard,
    get_reputation_analytics,
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


# RF-006: Public endpoint — approved reviews for a hotel
@public_router.get("/{prop_id}/reviews")
def hotel_reviews_api(
    prop_id: int = Path(..., ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=5, ge=1, le=100),
):
    """Return approved reviews for a hotel (public, no auth required).

    Defaults to the first 5 most recent reviews; use page/page_size to paginate.
    """
    return get_hotel_reviews(prop_id, page=page, page_size=page_size)


def _require_review_same_hotel(db, review_id: str, prop_id: int | None) -> None:
    """404 (no 403) si la reseña pertenece a otro hotel — deny cross-hotel."""
    from bson import ObjectId
    from bson.errors import InvalidId
    try:
        query = {"_id": ObjectId(review_id)}
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada")
    doc = db.reviews.find_one(query, {"prop_id": 1})
    if doc is None or doc.get("prop_id") != prop_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada")


def _review_prop_id(db, review_id: str) -> int | None:
    """Resuelve el prop_id de una reseña (para gates inline de rutas mixtas)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    try:
        doc = db.reviews.find_one({"_id": ObjectId(review_id)}, {"prop_id": 1})
    except InvalidId:
        doc = None
    return int(doc.get("prop_id") or 0) if doc else None


@api_router.post("", status_code=201, response_model=ReviewResponse)
def create_review_api(payload: dict = Body(...), current_user: dict = Depends(require_login)):
    user_id = str(current_user.get("_id", ""))
    parsed = ReviewCreate(**payload)
    result = create_review(user_id, parsed)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear la reseña (booking inválido o ya reseñado)")
    return ReviewResponse.model_validate(result)


@api_router.post("/staff", status_code=201)
def create_review_staff_api(payload: dict = Body(...), current_user: dict = Depends(require_login)):
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


@api_router.get("", response_model=ReviewListResponse)
def list_reviews_api(
    request: Request,
    prop_id: int | None = Query(default=None),
    user_id: str | None = Query(default=None),
    moderation_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    # Endurecimiento de aislamiento (auditoría my-*): los filtros de staff
    # (user_id ajeno / estado de moderación) exigen reviews.read. Sin él, un
    # cliente podía enumerar reseñas de cualquier usuario y ver estados de
    # moderación que la vista pública no expone.
    db = get_database()
    # Migración E: con prop_id el staff gatea POR HOTEL (deny-by-default: el
    # rol global no basta). Sin prop_id (huésped multi-hotel) conserva el
    # comportamiento global.
    if prop_id is not None:
        from src.app.modules.hotels.service.operational import non_operational_hotel as _non_op
        if _non_op(db, prop_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El hotel {prop_id} no está operativo.",
            )
        if not user_can_access_hotel(current_user, prop_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sin acceso al hotel {prop_id}.",
            )
        is_staff = user_has_permission(db, current_user, "reviews.read", prop_id=prop_id)
    else:
        is_staff = user_has_permission(db, current_user, "reviews.read")
    if (user_id is not None or moderation_status is not None) and not is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permiso requerido: reviews.read",
        )
    # RBAC hotel filter: hotel_partner/gerente_hotel solo ven sus hoteles.
    # El prop_id explícito NUNCA reemplaza el alcance: se valida contra él y
    # 403 fuera de alcance (antes el override saltaba el RBAC cross-hotel).
    hotel_filter = hotel_filter_from_user(current_user)
    if prop_id is not None:
        if not user_can_access_hotel(current_user, prop_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sin acceso al hotel {prop_id}.",
            )
        hotel_filter = {"prop_id": prop_id}
    # Sin permiso staff y sin filtro de moderación: solo reseñas aprobadas
    # (paridad con GET /api/hotels/{prop_id}/reviews).
    if not is_staff and moderation_status is None:
        moderation_status = "approved"
    return ReviewListResponse.model_validate(list_reviews(
        hotel_filter=hotel_filter,
        prop_id=prop_id,
        user_id=user_id,
        moderation_status=moderation_status,
        page=page,
        page_size=page_size,
    ))


@api_router.patch("/{review_id}/moderate")
def moderate_review_api(
    review_id: str,
    payload: ReviewModeration = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reviews.moderate")),
):
    """RF-005: Moderate a review. Only marketing_hotelero and super_admin can moderate."""
    _require_review_same_hotel(get_database(), review_id, query_prop_id)
    result = moderate_review(review_id, payload, current_user)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo moderar la reseña")
    return result


@api_router.patch("/{review_id}/respond")
def respond_review_api(
    review_id: str,
    payload: ReviewStaffResponse = Body(...),
    current_user: dict = Depends(require_login),
):
    """RF-006: Respond to an approved review. Only hotel_partner of that hotel can respond."""
    # Migración E: gate por-hotel INLINE — la reseña debe pertenecer a un
    # hotel donde el rol del hotel porte reviews.read (deny-by-default).
    db = get_database()
    prop_id = _review_prop_id(db, review_id)
    if prop_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada")
    from src.app.modules.hotels.service.operational import non_operational_hotel as _non_op
    if _non_op(db, prop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"El hotel {prop_id} no está operativo.")
    if not user_can_access_hotel(current_user, prop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Sin acceso al hotel {prop_id}.")
    if not user_has_permission(db, current_user, "reviews.read", prop_id=prop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permiso requerido: reviews.read")
    # Verify the user is a hotel_partner or super_admin
    role = get_role_name(current_user)
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
    current_user: dict = Depends(require_login),
):
    """Edit a review by its author (only while moderation_status is 'pending')."""
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
    current_user: dict = Depends(require_login),
):
    """Report a review for inappropriate content. Any authenticated user can report."""
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
    current_user: dict = Depends(require_login),
):
    """List review reports (staff: marketing_hotelero, super_admin).

    Cola de moderación multi-hotel (vista de gerencia — excepción global
    documentada de la Migración E: el handler no filtra por prop_id).
    Requires authentication."""
    return list_review_reports(status=status, page=page, page_size=page_size)


@api_router.get("/reputation/analytics")
def reputation_analytics_api(
    prop_id: int | None = Query(default=None, ge=1),
    days: int = Query(default=30, ge=1, le=365),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    current_user: dict = Depends(require_prop_permission("reviews.read")),
):
    """Return the hourly ClickHouse reputation aggregate when available.

    Filtra ``kpi_review_daily`` por ``date_from``/``date_to`` (ambos límites);
    sin ellos usa los últimos ``days`` días hasta hoy.
    """
    try:
        return get_reputation_analytics(
            prop_id=prop_id,
            days=days,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@api_router.get("/reputation/dashboard")
def reputation_dashboard_api(
    prop_id: int | None = Query(default=None, ge=1),
    days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(require_prop_permission("reviews.read")),
):
    """Return reputation dashboard data: GRI, departmental sentiment, recent feedback."""
    return get_reputation_dashboard(prop_id=prop_id, days=days)


@api_router.get("/{review_id}")
def get_review_api(review_id: str, current_user: dict = Depends(require_login)):
    result = get_review(review_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada")
    return result


@api_router.delete("/{review_id}", status_code=204)
def delete_review_api(
    review_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reviews.moderate")),
):
    _require_review_same_hotel(get_database(), review_id, query_prop_id)
    deleted = delete_review(review_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reseña no encontrada")
