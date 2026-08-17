"""Versioned legal documents (Términos y Condiciones, Política de Privacidad).

Los documentos legales viven en Mongo (colección ``legal_documents``), no
hardcodeados en el frontend. Cada ``doc_type`` tiene un histórico de
versiones; exactamente una versión está ``is_active`` y es la que se sirve
al público y la que los flujos de registro exigen aceptar.

Forma del documento:

    {
        "_id": ObjectId,
        "doc_type": "terms_guest" | "terms_hotel_partner" | "privacy_policy",
        "version": int,
        "title": str,
        "effective_date": datetime (UTC),
        "is_active": bool,
        "sections": [{"heading": str, "body": str}, ...],
        "created_at": datetime,
        "updated_by": str,
    }
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from pymongo import ASCENDING, IndexModel

from src.database.collections import ensure_collection
from src.database.connection import get_database

LEGAL_DOCUMENTS = "legal_documents"

# Doc types reconocidos por el sistema. El seed canónico vive en
# ``server/scripts/seed_legal_documents.py``.
VALID_DOC_TYPES: tuple[str, ...] = ("terms_guest", "terms_hotel_partner", "privacy_policy")

# Labels públicos por doc_type (para UI + mensajes de error).
DOC_TYPE_LABELS: dict[str, str] = {
    "terms_guest": "Términos y Condiciones",
    "terms_hotel_partner": "Términos y Condiciones para Anfitriones",
    "privacy_policy": "Política de Privacidad",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_legal_collections() -> None:
    """Ensure the legal_documents collection and its indexes exist."""
    ensure_collection(LEGAL_DOCUMENTS, [
        IndexModel(
            [("doc_type", ASCENDING), ("version", ASCENDING)],
            name="idx_legal_doc_type_version",
            unique=True,
        ),
        IndexModel(
            [("doc_type", ASCENDING), ("is_active", ASCENDING)],
            name="idx_legal_active",
        ),
    ])


def _to_public(doc: dict[str, Any]) -> dict[str, Any]:
    """Serialize a legal document for public/admin consumption."""
    return {
        "doc_type": doc.get("doc_type"),
        "version": doc.get("version"),
        "title": doc.get("title") or DOC_TYPE_LABELS.get(doc.get("doc_type", ""), "Documento legal"),
        "effective_date": (
            doc["effective_date"].isoformat()
            if isinstance(doc.get("effective_date"), datetime)
            else doc.get("effective_date")
        ),
        "is_active": bool(doc.get("is_active", False)),
        "sections": doc.get("sections") or [],
        "updated_by": doc.get("updated_by"),
    }


def get_active_document(db, doc_type: str) -> dict[str, Any] | None:
    """Return the active (published) version of a doc type, or None."""
    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de documento legal inválido.")
    doc = db[LEGAL_DOCUMENTS].find_one({"doc_type": doc_type, "is_active": True})
    return doc


def list_documents(db, doc_type: str | None = None) -> list[dict[str, Any]]:
    """List all documents (all versions), optionally filtered by doc_type."""
    query: dict[str, Any] = {}
    if doc_type:
        if doc_type not in VALID_DOC_TYPES:
            raise HTTPException(status_code=400, detail="Tipo de documento legal inválido.")
        query["doc_type"] = doc_type
    cursor = db[LEGAL_DOCUMENTS].find(query).sort([("doc_type", 1), ("version", -1)])
    return [_to_public(doc) for doc in cursor]


def publish_document(
    db,
    *,
    doc_type: str,
    title: str,
    sections: list[dict[str, str]],
    version: int | None = None,
    updated_by: str = "admin",
) -> dict[str, Any]:
    """Publish a new version of a legal document.

    - ``version`` auto-increments from the current max if not provided.
    - The previously active version is deactivated; the new one becomes active.
    - ``sections`` is the structured JSON content (heading + body paragraphs).
    """
    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de documento legal inválido.")
    title = (title or DOC_TYPE_LABELS.get(doc_type, "Documento legal")).strip()
    if not title:
        raise HTTPException(status_code=400, detail="El título del documento es requerido.")
    if not sections or not isinstance(sections, list):
        raise HTTPException(status_code=400, detail="El documento debe tener al menos una sección.")
    for section in sections:
        if not isinstance(section, dict) or not str(section.get("heading") or "").strip():
            raise HTTPException(status_code=400, detail="Cada sección debe tener un heading.")
        if not str(section.get("body") or "").strip():
            raise HTTPException(status_code=400, detail="Cada sección debe tener un body.")

    if version is None:
        last = db[LEGAL_DOCUMENTS].find_one(
            {"doc_type": doc_type}, sort=[("version", -1)], projection={"version": 1}
        )
        version = int(last["version"]) + 1 if last else 1
    else:
        version = int(version)
        if version < 1:
            raise HTTPException(status_code=400, detail="La versión debe ser mayor a 0.")
        existing = db[LEGAL_DOCUMENTS].find_one({"doc_type": doc_type, "version": version})
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"La versión {version} de {DOC_TYPE_LABELS.get(doc_type, doc_type)} ya existe.",
            )

    now = _now()
    # Desactivar la versión vigente.
    db[LEGAL_DOCUMENTS].update_many(
        {"doc_type": doc_type, "is_active": True},
        {"$set": {"is_active": False}},
    )
    doc = {
        "doc_type": doc_type,
        "version": version,
        "title": title,
        "effective_date": now,
        "is_active": True,
        "sections": [
            {"heading": str(s["heading"]).strip(), "body": str(s["body"]).strip()}
            for s in sections
        ],
        "created_at": now,
        "updated_by": updated_by,
    }
    db[LEGAL_DOCUMENTS].insert_one(doc)
    return _to_public(doc)


def validate_terms_acceptance(
    db,
    doc_type: str,
    accepted_version: int | None,
) -> None:
    """Validate that the accepted version matches the currently active one.

    Si el payload de registro trae ``accepted_terms_version``, debe coincidir
    con la versión activa publicada; si no, 400 con instrucciones claras. Si
    no se envía versión (back-compat con tests/seeds), el flujo continúa sin
    estampar aceptación.
    """
    if accepted_version is None:
        return
    active = get_active_document(db, doc_type)
    label = DOC_TYPE_LABELS.get(doc_type, "los términos")
    if active is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No hay una versión publicada de {label}. "
                "El administrador debe publicarla antes de aceptar el registro."
            ),
        )
    active_version = int(active.get("version"))
    try:
        accepted = int(accepted_version)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"La versión aceptada de {label} es inválida.")
    if accepted != active_version:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{label} fueron actualizados: aceptaste la v{accepted} pero la vigente es la "
                f"v{active_version}. Revisa y acepta la versión vigente para continuar."
            ),
        )
