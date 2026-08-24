from __future__ import annotations

import json
import logging
from typing import Any

from src.app.ai.service import chat
from src.app.modules.hotels.service._helpers import (
    _country_display_name,
    _format_number,
    _hotel_display_name,
)
from src.app.modules.hotels.service.lookups import _country_lookup
from src.database.connection import get_database

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Eres un sistema de recomendación hotelera. Tu tarea es analizar hoteles y "
    "encontrar los más similares a un hotel de referencia en términos de:\n"
    "- Ubicacion geografica (mismo pais/region)\n"
    "- Categoria (estrellas)\n"
    "- Tipo y posicionamiento del hotel\n"
    "- Amenidades y servicios\n"
    "- Perfil de huespedes\n\n"
    "Responde SOLO con un objeto JSON valido, sin texto adicional ni marcas de codigo."
)

_USER_TEMPLATE = (
    "Hotel de referencia:\n"
    "{source_hotel}\n\n"
    "Hoteles candidatos:\n"
    "{candidates}\n\n"
    "Devuelve un JSON con el siguiente formato exacto (sin texto adicional):\n"
    '{{"similar_hotels": ['
    '{{"prop_id": 123, "similarity_score": 92, "reason": "explicacion corta en espanol"}}'
    "]}}\n\n"
    "Selecciona exactamente los {limit} hoteles mas similares de la lista. "
    "similarity_score debe ser un entero entre 0 y 100."
)


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        cleaned: list[str] = []
        for line in lines:
            if line.strip().startswith("```"):
                continue
            cleaned.append(line)
        text = "\n".join(cleaned).strip()
    return text


def _fetch_hotel(prop_id: int) -> dict[str, Any] | None:
    db = get_database()
    hotel = db.dim_hotels.find_one({"prop_id": prop_id}, {"_id": 0})
    if not hotel:
        return None
    # Gate operativo (Fase A): un hotel pendiente de aprobación no genera
    # recomendaciones públicas.
    if hotel.get("published") is False:
        return None
    content = db.hotel_content_pages.find_one(
        {"prop_id": prop_id},
        {"_id": 0, "description": 1, "amenities_text": 1},
    )
    images = list(
        db.hotel_images.find({"prop_id": prop_id}, {"_id": 0, "image_url": 1})
        .sort([("_id", 1)])
        .limit(1)
    )
    return {
        **hotel,
        "description": (content or {}).get("description") or "",
        "amenities_text": (content or {}).get("amenities_text") or "",
        "image_url": images[0]["image_url"] if images else "",
    }


def _prefilter_candidates(
    source: dict[str, Any],
    max_candidates: int = 30,
) -> list[dict[str, Any]]:
    db = get_database()
    prop_id = int(source["prop_id"])
    match: dict[str, Any] = {"prop_id": {"$ne": prop_id}}

    country_id = source.get("prop_country_id")
    if country_id is not None:
        match["prop_country_id"] = int(country_id)

    star = source.get("prop_starrating")
    if star is not None:
        match["prop_starrating"] = {
            "$gte": max(1, int(star) - 1),
            "$lte": min(5, int(star) + 1),
        }

    candidates = list(
        db.dim_hotels.find(match, {"_id": 0})
        .sort([("prop_review_score", -1)])
        .limit(max_candidates)
    )

    if not candidates:
        return []

    prop_ids = [int(c["prop_id"]) for c in candidates]

    contents = {
        int(d["prop_id"]): d
        for d in db.hotel_content_pages.find(
            {"prop_id": {"$in": prop_ids}},
            {"_id": 0, "description": 1, "amenities_text": 1},
        )
    }
    images_map: dict[int, str] = {}
    for d in (
        db.hotel_images.find(
            {"prop_id": {"$in": prop_ids}},
            {"_id": 0, "prop_id": 1, "image_url": 1},
        )
        .sort([("_id", 1)])
        .limit(len(prop_ids) * 2)
    ):
        pid = int(d["prop_id"])
        if pid not in images_map:
            images_map[pid] = d["image_url"]

    for c in candidates:
        pid = int(c["prop_id"])
        ct = contents.get(pid, {})
        c["description"] = ct.get("description") or ""
        c["amenities_text"] = ct.get("amenities_text") or ""
        c["image_url"] = images_map.get(pid, "")
        # Store raw country key for batched lookup later (no per-candidate DB query)
        c["_country_key"] = c.get("prop_country_id")
        c["_country_doc"] = {}

    return candidates


def _format_hotel_for_ai(h: dict[str, Any]) -> str:
    return (
        f"ID: {h.get('prop_id')}, "
        f"Nombre: {_hotel_display_name(h, int(h.get('prop_id', 0)))}, "
        f"Estrellas: {h.get('prop_starrating') or 'N/D'}/5, "
        f"Score: {h.get('prop_review_score') or 'N/D'}/10, "
        f"Amenidades: {(h.get('amenities_text') or 'N/D')[:100]}, "
        f"Descripcion: {(h.get('description') or 'N/D')[:200]}"
    )


def _call_ai(
    source: dict[str, Any],
    candidates: list[dict[str, Any]],
    limit: int = 6,
) -> list[dict[str, Any]]:
    source_text = _format_hotel_for_ai(source)
    candidates_text = "\n".join(
        _format_hotel_for_ai(c) for c in candidates
    )
    user_prompt = _USER_TEMPLATE.format(
        source_hotel=source_text,
        candidates=candidates_text,
        limit=limit,
    )

    response = chat(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
        thinking=False,
    )
    if not response:
        return []

    try:
        cleaned = _extract_json(response)
        data = json.loads(cleaned)
        return data.get("similar_hotels", [])
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning("Failed to parse AI response: %s", response[:200])
        return []


def _fallback(
    source: dict[str, Any],
    candidates: list[dict[str, Any]],
    limit: int = 6,
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for c in candidates:
        score = 0
        if (
            c.get("prop_starrating") is not None
            and source.get("prop_starrating") is not None
            and int(c["prop_starrating"]) == int(source["prop_starrating"])
        ):
            score += 30
        if (
            c.get("prop_review_score") is not None
            and source.get("prop_review_score") is not None
        ):
            diff = abs(float(c["prop_review_score"]) - float(source["prop_review_score"]))
            score += max(0, 10 - int(diff * 2))
        if (
            c.get("prop_country_id") is not None
            and source.get("prop_country_id") is not None
            and c["prop_country_id"] == source["prop_country_id"]
        ):
            score += 25
        scored.append({
            "prop_id": int(c["prop_id"]),
            "similarity_score": min(100, score + 35),
            "reason": "Coincidencia por ubicacion y categoria",
        })

    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored[:limit]


def _build_response(
    ranked: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidate_map = {int(c["prop_id"]): c for c in candidates}
    # El país se resuelve SIEMPRE por prop_country_id → dim_visitor_countries
    # (opción B: geo_catalog ya no es fuente de país para hoteles).
    all_country_keys: list[Any] = []
    for c in candidates:
        key = c.get("_country_key")
        if key is not None:
            all_country_keys.append(key)
    cl = _country_lookup(all_country_keys) if all_country_keys else {}

    results: list[dict[str, Any]] = []
    for item in ranked:
        pid = item.get("prop_id")
        if pid is None:
            continue
        pid = int(pid)
        c = candidate_map.get(pid)
        if not c:
            continue
        country_key = c.get("_country_key")
        country_doc = c.get("_country_doc", {})
        if country_key is not None:
            country_doc = cl.get(country_key, {})
        country_name = (
            _country_display_name(country_doc, country_key)
            if country_key is not None
            else "N/D"
        )
        results.append({
            "prop_id": pid,
            "hotel_label": _hotel_display_name(c, pid),
            "prop_starrating": c.get("prop_starrating"),
            "prop_review_score": c.get("prop_review_score"),
            "review_label": (
                _format_number(c["prop_review_score"])
                if c.get("prop_review_score") is not None
                else "N/D"
            ),
            "country_display_name": country_name,
            "similarity_score": int(item.get("similarity_score", 0)),
            "reason": item.get("reason", ""),
            "image_url": c.get("image_url", ""),
        })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results


def similar_hotels(prop_id: int, limit: int = 6) -> dict[str, Any]:
    source = _fetch_hotel(prop_id)
    if not source:
        return {"items": []}

    candidates = _prefilter_candidates(source)
    if not candidates:
        return {"items": []}

    try:
        ranked = _call_ai(source, candidates, limit=limit)
        if not ranked:
            ranked = _fallback(source, candidates, limit=limit)
    except Exception:
        logger.exception("AI similar hotels failed, using fallback")
        ranked = _fallback(source, candidates, limit=limit)

    return {"items": _build_response(ranked, candidates)}
