from __future__ import annotations

from urllib.parse import quote

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

from src.app.modules.hotels.service.operational import (
    is_operational_gate_bypassed,
    non_operational_hotel,
)
from src.app.security.approval import (
    approval_gate_code,
    is_approval_allowlisted,
    maybe_apply_rejection_grace,
)
from src.app.security.navigation import (
    get_default_redirect_for_role,
    get_navigation_for_user,
)
from src.app.security.permissions import get_user_permission_codes
from src.app.security.role_helpers import get_role_name
from src.app.security.route_permissions import is_public_path
from src.app.security.session import SESSION_COOKIE_NAME, get_current_user
from src.database.connection import get_database


def _login_redirect(request: Request) -> RedirectResponse:
    next_path = request.url.path
    if request.url.query:
        next_path = f"{next_path}?{request.url.query}"
    return RedirectResponse(f"/login?next={quote(next_path, safe='/?=&')}", status_code=303)


async def role_access_middleware(request: Request, call_next):
    """Authentication-only middleware.

    Responsibilities:
    - Resolve the current user from the session cookie.
    - Redirect unauthenticated users to /login (HTML) or return 401 (API).
    - Inject ``request.state.current_user``, ``permission_codes``, and
      ``navigation`` so downstream handlers don't need to re-query.

    Authorization (who can do what) is handled exclusively by
    ``Depends(require_permission(...))`` at each endpoint — not here.
    """
    path = request.url.path
    is_api_request = path.startswith("/api/")

    # ── Public paths: no auth required ──────────────────────────────────
    if is_public_path(path):
        request.state.current_user = None
        request.state.navigation = get_navigation_for_user(None)
        return await call_next(request)

    # ── Resolve user from session ───────────────────────────────────────
    db = get_database()
    user, session = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    request.state.current_user = user
    request.state.current_session = session
    permission_codes = get_user_permission_codes(db, user) if user else set()
    request.state.permission_codes = permission_codes
    request.state.navigation = get_navigation_for_user(user, permission_codes)

    # ── Rejection grace (lazy): expired rejected accounts are deactivated
    #    on the first interaction — treat as unauthenticated. ────────────
    if user and maybe_apply_rejection_grace(db, user):
        if is_api_request:
            return JSONResponse(
                status_code=401,
                content={
                    "authenticated": False,
                    "detail": "Tu registro de alojamiento fue rechazado y la cuenta ya no está activa.",
                    "login_url": f"/login?next={quote(path, safe='/?=&')}",
                },
            )
        return _login_redirect(request)

    # ── Root redirect ───────────────────────────────────────────────────
    if path == "/":
        if not user:
            return RedirectResponse("/login", status_code=303)
        return RedirectResponse(get_default_redirect_for_role(get_role_name(user)), status_code=303)

    # ── Unauthenticated → 401 (API) or redirect (HTML) ──────────────────
    if not user:
        if is_api_request:
            return JSONResponse(
                status_code=401,
                content={
                    "authenticated": False,
                    "detail": "Authentication required",
                    "login_url": f"/login?next={quote(path, safe='/?=&')}",
                },
            )
        return _login_redirect(request)

    # ── Approval gate (UX-1): non-approved owner sessions are restricted
    #    to the registration-status allowlist. Everything else → 403. ────
    approval_status = user.get("approval_status") or "approved"
    if approval_status != "approved" and not is_approval_allowlisted(path):
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Tu alojamiento está pendiente de aprobación del administrador.",
                "code": approval_gate_code(approval_status),
                "approval_status": approval_status,
                "redirect": "/alojamiento-en-revision",
            },
        )

    # ── /auth/* paths manage their own auth (login, register, etc.) ─────
    if path.startswith("/auth/"):
        return await call_next(request)

    # ── Operational gate (Fase A) at middleware level ───────────────────
    # Extiende el gate de ``require_prop_permission`` a las rutas management
    # LEGADAS (billing/reservations/instay/housekeeping/expenses/hr/...) que
    # reciben ``prop_id`` como QUERY PARAM bajo ``require_permission`` global
    # (no pasaban por el dependency). Misma regla: si la fila de ``dim_hotels``
    # EXISTE con ``published=false`` explícito → 403. Sin fila o sin el campo
    # (legado) → pasa. Los prefijos del dueño/cola quedan exentos
    # (``is_operational_gate_bypassed``) porque operan sobre hoteles pendientes.
    #
    # Limitaciones conocidas (mismo alcance que pidió el usuario: query param):
    # - ``query_params.get`` devuelve SOLO el primer valor si hay varios
    #   ``?prop_id=a&prop_id=b`` (compare es público y no aplica; si un día una
    #   ruta management usa multi-prop_id, revisar aquí).
    # - Los POST con ``prop_id`` en el BODY (ej. ``POST /api/reservations``,
    #   ``cleanup-expired-folios``) NO pasan por este gate: leer el body en el
    #   middleware rompería el parseo de FastAPI. Riesgo práctico bajo (un hotel
    #   pendiente no tiene inventario/tarifas), pero es el hueco residual.
    if not is_operational_gate_bypassed(path):
        raw_prop_id = request.query_params.get("prop_id")
        if raw_prop_id is not None:
            try:
                prop_id = int(raw_prop_id)
            except (TypeError, ValueError):
                prop_id = None
            if prop_id is not None and non_operational_hotel(db, prop_id):
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": f"El hotel {prop_id} no está operativo.",
                        "code": "hotel_not_operational",
                        "prop_id": prop_id,
                    },
                )

    # ── All other routes: authorization is delegated to the endpoint ────
    # Each endpoint must use ``Depends(require_permission(...))`` to enforce
    # granular, DB-backed access control.
    return await call_next(request)
