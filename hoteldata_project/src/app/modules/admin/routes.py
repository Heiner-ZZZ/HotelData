from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from src.app.modules.admin.service import (
    build_security_section_pdf,
    ensure_user_status_field,
    role_editor_payload,
    security_overview,
    toggle_user_active,
    update_role_definition,
    users_overview,
)
from src.app.security.dependencies import require_permission


router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))


@router.get("/security")
def security_dashboard(request: Request, current_user: dict = Depends(require_permission("users.manage"))):
    return templates.TemplateResponse(
        request,
        "admin/security.html",
        {
            "current_user": current_user,
            "overview": security_overview(),
        },
    )


@router.get("/users")
def users_dashboard(request: Request, current_user: dict = Depends(require_permission("users.manage"))):
    ensure_user_status_field()
    return templates.TemplateResponse(
        request,
        "admin/users.html",
        {
            "current_user": current_user,
            "overview": users_overview(),
            "message": request.query_params.get("message", ""),
            "error": request.query_params.get("error", ""),
        },
    )


@router.get("/roles/{role_name}")
def role_editor(request: Request, role_name: str, current_user: dict = Depends(require_permission("users.manage"))):
    payload = role_editor_payload(role_name)
    if payload is None:
        return RedirectResponse(url="/admin/security?error=Rol no encontrado.", status_code=303)
    return templates.TemplateResponse(
        request,
        "admin/role_edit.html",
        {
            "current_user": current_user,
            "payload": payload,
            "message": request.query_params.get("message", ""),
            "error": request.query_params.get("error", ""),
        },
    )


@router.post("/roles/{role_name}")
def role_editor_save(
    request: Request,
    role_name: str,
    description: str = Form(...),
    permission_codes: list[str] = Form(default=[]),
    current_user: dict = Depends(require_permission("users.manage")),
):
    result = update_role_definition(role_name, description, permission_codes, current_user)
    param = "message" if result["ok"] else "error"
    return RedirectResponse(url=f"/admin/roles/{role_name}?{urlencode({param: result['message']})}", status_code=303)


@router.get("/reports/{section}.pdf")
def security_report_pdf(section: str, current_user: dict = Depends(require_permission("users.manage"))):
    result = build_security_section_pdf(section)
    if result is None:
        return RedirectResponse(url="/admin/security?error=Sección de reporte no encontrada.", status_code=303)
    pdf_bytes, title = result
    filename = f"{section}_report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "X-Report-Title": title},
    )


def _toggle_user_active_redirect(user_id: str, current_user: dict) -> RedirectResponse:
    result = toggle_user_active(user_id, current_user)
    param = "message" if result["ok"] else "error"
    return RedirectResponse(url=f"/admin/users?{urlencode({param: result['message']})}", status_code=303)


@router.post("/users/{user_id}/toggle-active")
def users_toggle_active_post(user_id: str, request: Request, current_user: dict = Depends(require_permission("users.manage"))):
    return _toggle_user_active_redirect(user_id, current_user)


@router.get("/users/{user_id}/toggle-active")
def users_toggle_active_get(user_id: str, request: Request, current_user: dict = Depends(require_permission("users.manage"))):
    return _toggle_user_active_redirect(user_id, current_user)
