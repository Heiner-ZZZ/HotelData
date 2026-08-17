"""Endpoints for versioned legal documents.

- Public: ``GET /api/public/legal`` — serves the ACTIVE version of a doc type
  (no auth): powers the terms dialog + the acceptance checkbox on both
  registration flows.
- Admin: ``/api/admin/legal`` (``users.manage``) — publish new versions and
  inspect the full history.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from src.app.modules.legal.schemas import LegalPublishRequest
from src.app.modules.legal.service import (
    DOC_TYPE_LABELS,
    get_active_document,
    list_documents,
    publish_document,
)
from src.app.security.dependencies import require_permission
from src.database.connection import get_database

public_router = APIRouter(prefix="/api/public", tags=["legal-public"])
admin_router = APIRouter(prefix="/api/admin/legal", tags=["legal-admin"])


@public_router.get("/legal")
def public_legal_document(
    doc_type: str = Query(default="terms_guest"),
) -> dict:
    """Return the ACTIVE version of a legal document.

    Public — no auth required. Terms are meant to be shown inside the
    registration flow BEFORE the account is created, so they cannot live
    behind the session cookie. Version + sections are served so the UI never
    hardcodes legal text.
    """
    db = get_database()
    doc = get_active_document(db, doc_type)
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No hay una versión publicada de "
                f"{DOC_TYPE_LABELS.get(doc_type, doc_type)}."
            ),
        )
    return {
        "doc_type": doc["doc_type"],
        "version": doc["version"],
        "title": doc["title"],
        "effective_date": (
            doc["effective_date"].isoformat()
            if hasattr(doc.get("effective_date"), "isoformat")
            else doc.get("effective_date")
        ),
        "sections": doc["sections"],
    }


@admin_router.get("")
def admin_list_legal(
    doc_type: str | None = Query(default=None),
    current_user: dict = Depends(require_permission("users.manage")),
) -> dict:
    """List all documents (all versions) for the platform admin."""
    db = get_database()
    return {"items": list_documents(db, doc_type=doc_type)}


@admin_router.post("/publish")
def admin_publish_legal(
    body: LegalPublishRequest,
    current_user: dict = Depends(require_permission("users.manage")),
) -> dict:
    """Publish a new version of a legal document (deactivates the previous one)."""
    db = get_database()
    username = current_user.get("username") or current_user.get("display_name") or "admin"
    doc = publish_document(
        db,
        doc_type=body.doc_type,
        title=body.title,
        sections=[s.model_dump() for s in body.sections],
        version=body.version,
        updated_by=username,
    )
    return {"ok": True, "document": doc}
