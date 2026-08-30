from __future__ import annotations

from typing import Any

from src.app.modules.partner.services._common import _resolve_country_label
from src.database.connection import get_database

from ._helpers import (
    _active_fact_collection,
    _country_display_name,
    _destination_display_name,
    _format_money,
    _metric_projection,
    _min_real_rate_for_prop,
    _site_display_name,
)
from .lookups import _country_lookup, _destination_lookup, _site_lookup
from .search import _enrich_hotel_metrics


def top_destinations_for_hotel(prop_id: int, limit: int = 8) -> list[dict[str, Any]]:
    collection, _ = _active_fact_collection()
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {"$group": {"_id": "$srch_destination_id", "events": {"$sum": 1}, "avg_price": {"$avg": "$price_usd"}}},
        {"$sort": {"events": -1}},
        {"$limit": limit},
    ]
    rows = list(collection.aggregate(pipeline, allowDiskUse=True))
    lookup = _destination_lookup([int(row["_id"]) for row in rows if row.get("_id") is not None])
    return [
        {
            "srch_destination_id": int(row["_id"]),
            "destination_label": _destination_display_name(lookup.get(int(row["_id"]), {}), int(row["_id"])),
            "events": int(row.get("events") or 0),
            "avg_price_label": _format_money(row.get("avg_price")),
        }
        for row in rows
        if row.get("_id") is not None
    ]


def _top_visitor_countries_for_hotel(prop_id: int, limit: int = 6) -> list[dict[str, Any]]:
    collection, _ = _active_fact_collection()
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {
            "$group": {
                "_id": "$visitor_location_country_id",
                "events": {"$sum": 1},
                "reservations": {"$sum": {"$cond": [{"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}, 1, 0]}},
            }
        },
        {"$sort": {"events": -1}},
        {"$limit": limit},
    ]
    rows = list(collection.aggregate(pipeline, allowDiskUse=True))
    lookup = _country_lookup([int(row["_id"]) for row in rows if row.get("_id") is not None])
    return [
        {
            "visitor_location_country_id": int(row["_id"]),
            "country_label": _country_display_name(lookup.get(int(row["_id"]), {}), int(row["_id"])),
            "events": int(row.get("events") or 0),
            "reservations": int(row.get("reservations") or 0),
        }
        for row in rows
        if row.get("_id") is not None
    ]


def _top_sites_for_hotel(prop_id: int, limit: int = 6) -> list[dict[str, Any]]:
    collection, _ = _active_fact_collection()
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {
            "$group": {
                "_id": "$site_id",
                "events": {"$sum": 1},
                "clicks": {"$sum": {"$cond": [{"$or": [{"$eq": ["$click_bool", 1]}, {"$eq": ["$click_bool", True]}]}, 1, 0]}},
                "reservations": {"$sum": {"$cond": [{"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}, 1, 0]}},
            }
        },
        {"$sort": {"events": -1}},
        {"$limit": limit},
    ]
    rows = list(collection.aggregate(pipeline, allowDiskUse=True))
    lookup = _site_lookup([int(row["_id"]) for row in rows if row.get("_id") is not None])
    return [
        {
            "site_id": int(row["_id"]),
            "site_label": _site_display_name(lookup.get(int(row["_id"]), {}), int(row["_id"])),
            "events": int(row.get("events") or 0),
            "clicks": int(row.get("clicks") or 0),
            "reservations": int(row.get("reservations") or 0),
        }
        for row in rows
        if row.get("_id") is not None
    ]


def _hotel_rates_for_detail(prop_id: int, limit: int = 12) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.hotel_rate_calendar.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("date", 1), ("rate_plan_id", 1)])
        .limit(limit)
    )
    return [{**item, "rate_amount_label": _format_money(item.get("rate_amount"))} for item in items]


def _room_types_for_detail(prop_id: int, limit: int = 12) -> list[dict[str, Any]]:
    db = get_database()
    room_types = list(
        db.room_types.find(
            {"prop_id": prop_id},
            {"_id": 0, "room_type_id": 1, "name": 1, "base_capacity": 1, "max_adults": 1, "max_children": 1, "is_active": 1, "description": 1, "features": 1, "image_url": 1},
        )
        .sort([("is_active", -1), ("name", 1)])
        .limit(limit)
    )
    # Enriquecer con imágenes locales múltiples (room_type_images) — mismo
    # principio híbrido que hotel_images: locales primero, luego loremflickr.
    try:
        images_map: dict[str, list[str]] = {}
        for doc in db.room_type_images.find(
            {"prop_id": prop_id},
            {"_id": 0, "room_type_id": 1, "image_url": 1, "sort_order": 1},
        ).sort([("sort_order", 1), ("_id", 1)]):
            rt_id = str(doc.get("room_type_id") or "")
            url = str(doc.get("image_url") or "").strip()
            if rt_id and url:
                images_map.setdefault(rt_id, []).append(url)
        for rt in room_types:
            rt_id = str(rt.get("room_type_id") or "")
            local_images = images_map.get(rt_id, [])
            # Mantener compat: image_url = primera local si existe, si no la de room_types
            if local_images:
                rt["image_url"] = local_images[0]
            # Lista completa de locales para la galería híbrida del detalle
            rt["images"] = [{"image_url": u} for u in local_images]
    except Exception:
        # Si la colección no existe o hay error, no bloquear el detalle
        for rt in room_types:
            rt.setdefault("images", [])
    return room_types


def _hotel_rooms_for_detail(prop_id: int) -> list[dict[str, Any]]:
    db = get_database()
    return list(
        db.hotel_rooms.find(
            {"prop_id": prop_id},
            {"_id": 0, "hotel_room_id": 1, "room_label": 1, "room_type_id": 1, "floor": 1, "is_active": 1},
        )
        .sort([("room_label", 1)])
    )


def _hotel_policies_for_detail(prop_id: int) -> dict[str, Any] | None:
    db = get_database()
    return db.hotel_policies.find_one({"prop_id": prop_id}, {"_id": 0})


def _hotel_images_for_detail(prop_id: int) -> list[dict[str, Any]]:
    db = get_database()
    return list(db.hotel_images.find({"prop_id": prop_id}, {"_id": 0, "image_url": 1}).sort([("_id", 1)]).limit(20))


def _hotel_content_for_detail(prop_id: int) -> dict[str, Any] | None:
    db = get_database()
    return db.hotel_content_pages.find_one(
        {"prop_id": prop_id},
        {"_id": 0, "description": 1, "highlights": 1, "amenities_text": 1, "facilities": 1, "latitude": 1, "longitude": 1},
    )


def _hotel_reviews_for_detail(prop_id: int, limit: int = 5) -> list[dict[str, Any]]:
    """Reseñas verificadas para la ficha pública del hotel.

    Solo ``moderation_status=approved``, ordenadas por fecha real de
    creación (más recientes primero) con desempate por ``_id`` para no
    depender de timestamps idénticos del seed. Cada documento se enriquece
    con ``reviewer_name`` (display_name del usuario), ``review_score``,
    ``review_text`` y fechas ISO, para que el mapper del frontend
    (``hotel-detail.mapper.ts``) no caiga en ``Anónimo``/``0``.
    """
    from datetime import datetime, timezone

    from bson import ObjectId

    db = get_database()
    raw = list(
        db.reviews.find({"prop_id": prop_id, "moderation_status": "approved"})
        .sort([("created_at", -1), ("_id", -1)])
        .limit(limit)
    )
    out: list[dict[str, Any]] = []
    for doc in raw:
        # --- resolver nombre del huésped ---
        reviewer_name = "Huésped"
        user_id = doc.get("user_id")
        if user_id:
            try:
                oid = ObjectId(str(user_id))
                user = db.users.find_one({"_id": oid}, {"display_name": 1, "username": 1})
                if user:
                    reviewer_name = user.get("display_name") or user.get("username") or "Huésped"
            except Exception:
                reviewer_name = "Huésped"

        # --- normalizar fechas a ISO (robusto ante string "YYYY-MM-DD HH:MM:SS.mmmmmm") ---
        def _to_iso(val: Any) -> str:
            if isinstance(val, datetime):
                return val.astimezone(timezone.utc).isoformat() if val.tzinfo else val.replace(tzinfo=timezone.utc).isoformat()
            if isinstance(val, str) and val:
                # "2026-07-24 03:18:22.221000" → "2026-07-24T03:18:22.221000+00:00"
                try:
                    # intenta parsear como ISO con espacio
                    dt = datetime.fromisoformat(val.replace(" ", "T"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.isoformat()
                except Exception:
                    return val
            return ""

        created_iso = _to_iso(doc.get("created_at"))
        updated_iso = _to_iso(doc.get("updated_at"))

        rating = doc.get("rating")
        try:
            review_score = int(rating) if rating is not None else 0
        except Exception:
            review_score = 0

        title = (doc.get("title") or "").strip()
        comment = (doc.get("comment") or "").strip()
        # Texto público: comentario si existe, si no título; nunca vacío si hay título
        review_text = comment or title

        out.append({
            "review_id": str(doc.get("_id", "")),
            "prop_id": doc.get("prop_id"),
            "reviewer_name": reviewer_name,
            "user_display_name": reviewer_name,
            "review_score": review_score,
            "rating": review_score,
            "review_text": review_text,
            "comment": comment,
            "title": title,
            "created_at": created_iso,
            "updated_at": updated_iso,
            "moderation_status": doc.get("moderation_status"),
            "staff_response": doc.get("staff_response"),
        })
    return out


def get_hotel_detail_view(prop_id: int) -> dict[str, Any] | None:
    collection, source_collection = _active_fact_collection()
    db = get_database()
    hotel = db.dim_hotels.find_one({"prop_id": prop_id}, {"_id": 0}) or {}
    # Gate operativo (Fase A): un hotel pendiente de aprobación (published=false)
    # no es consultable públicamente — se comporta como inexistente (404) para
    # no filtrar su existencia.
    if hotel.get("published") is False:
        return None
    resolved_country = _resolve_country_label(hotel)
    hotel = {**hotel, "country_display_name": resolved_country}
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {"$group": {"_id": "$prop_id", "prop_id": {"$first": "$prop_id"}, **_metric_projection()}},
    ]
    metrics = next(collection.aggregate(pipeline, allowDiskUse=True), None)
    if not hotel and not metrics:
        return None

    item = _enrich_hotel_metrics([metrics or {"prop_id": prop_id, "events": 0, "reservations": 0, "clicks": 0, "destinations": []}])[0]
    item["source_collection"] = source_collection
    # Use the same country resolution logic as the management API
    item["country_display_name"] = hotel["country_display_name"]
    item["hotel"] = hotel
    item["min_rate_label"] = _min_real_rate_for_prop(prop_id)
    item["top_destinations"] = top_destinations_for_hotel(prop_id)
    item["top_visitor_countries"] = _top_visitor_countries_for_hotel(prop_id)
    item["top_sites"] = _top_sites_for_hotel(prop_id)
    item["hotel_rates"] = _hotel_rates_for_detail(prop_id)
    item["room_types"] = _room_types_for_detail(prop_id)
    item["hotel_rooms"] = _hotel_rooms_for_detail(prop_id)
    item["hotel_policies"] = _hotel_policies_for_detail(prop_id)
    item["hotel_images"] = _hotel_images_for_detail(prop_id)
    item["hotel_content"] = _hotel_content_for_detail(prop_id)
    item["reviews"] = _hotel_reviews_for_detail(prop_id)
    # Contador público: solo reseñas verificadas (approved), coherente con
    # GET /api/hotels/{prop_id}/reviews y con la ficha pública.
    item["review_count"] = db.reviews.count_documents({"prop_id": prop_id, "moderation_status": "approved"})
    return item


def hotel_detail(prop_id: int) -> dict[str, Any] | None:
    return get_hotel_detail_view(prop_id)
