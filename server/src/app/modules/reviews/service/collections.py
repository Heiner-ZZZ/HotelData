from __future__ import annotations

from pymongo import IndexModel, ASCENDING, DESCENDING

from src.database.collections import ensure_collection

COLLECTION = "reviews"
FACT_COLLECTION = "fact_reviews"

INDEXES = [
    IndexModel([("booking_id", ASCENDING)], name="idx_reviews_booking"),
    IndexModel([("prop_id", ASCENDING), ("created_at", DESCENDING)], name="idx_reviews_prop_created"),
    IndexModel([("user_id", ASCENDING)], name="idx_reviews_user"),
    IndexModel([("moderation_status", ASCENDING)], name="idx_reviews_moderation"),
]


def ensure_reviews_collections() -> None:
    ensure_collection(COLLECTION, INDEXES)
    ensure_collection(FACT_COLLECTION, INDEXES)


def module_status() -> ModuleStatus:
    from src.app.modules.reviews.schemas import ModuleStatus
    return ModuleStatus(
        module="reviews",
        status="active",
        description="Reseñas de huéspedes con moderación y respuesta del hotel. CU-O22/O23.",
    )
