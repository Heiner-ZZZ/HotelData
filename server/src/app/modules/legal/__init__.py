from __future__ import annotations

from src.app.modules.legal.routes import admin_router, public_router
from src.app.modules.legal.service import (
    DOC_TYPE_LABELS,
    VALID_DOC_TYPES,
    ensure_legal_collections,
    get_active_document,
    list_documents,
    publish_document,
    validate_terms_acceptance,
)

__all__ = [
    "admin_router",
    "public_router",
    "ensure_legal_collections",
    "get_active_document",
    "list_documents",
    "publish_document",
    "validate_terms_acceptance",
    "VALID_DOC_TYPES",
    "DOC_TYPE_LABELS",
]
