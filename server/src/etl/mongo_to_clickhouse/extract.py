"""Extracción MongoDB → KPIs ClickHouse (sin réplica de dimensiones).

Los catálogos se consultan solo para resolver labels durante la extracción.
Los KPIs se agregan con ``$group`` en Mongo: solo viajan filas agregadas y
livianas a ClickHouse.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from config.settings import get_settings
from src.etl.mongo_to_clickhouse.config import OPERATIONAL_COLLECTIONS


def _mongo_client(client, settings):
    if client is not None:
        return client, False
    from pymongo import MongoClient

    return MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=8000), True


def _parse_day(value: Any) -> str:
    """Normaliza un día a ``YYYY-MM-DD`` (str, datetime o date_key entero)."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    text = str(value)
    text = text.split("T")[0]
    if text.isdigit() and len(text) == 8:
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def _operational_prop_ids(db) -> list[Any]:
    """Prop_ids con datos reales en las colecciones operacionales.

    Evita consultar el catálogo sintético completo de ``dim_hotels`` (94K
    props GA03); solo conserva las claves de hoteles que producen datos
    operacionales para resolver sus labels en los KPI.
    """
    ids: set[Any] = set()
    for collection in OPERATIONAL_COLLECTIONS:
        try:
            ids.update(db[collection].distinct("prop_id"))
        except Exception:
            continue
    # Los datasets históricos pueden mezclar ``1`` y ``"1"``. Conservamos
    # ambas representaciones para que el filtro Mongo no descarte el label.
    expanded = set(ids)
    for value in tuple(ids):
        if isinstance(value, int) and not isinstance(value, bool):
            expanded.add(str(value))
        elif isinstance(value, str) and value.strip().isdigit():
            expanded.add(int(value.strip()))
    return sorted(expanded, key=lambda v: (v is None, str(v)))



def extract_kpi_booking_daily(client, db_name: str) -> list[dict[str, Any]]:
    """Agrega ``booking_orders`` por día × prop × room_type × source × status.

    La fecha se deriva de ``check_in_date`` (la noche de entrada determina el día
    de ocupación inicial). Cálculo: bookings (conteo), nights (suma total_nights),
    revenue_usd (suma total_price), adults, children, cancelled (conteo de
    estados cancelados).
    """
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        return _extract_kpi_booking(db)
    finally:
        if owns:
            mongo.close()


def _extract_kpi_booking(db) -> list[dict[str, Any]]:
    pipeline = [
        {
            "$group": {
                "_id": {
                    "date": {"$ifNull": ["$check_in_date", ""]},
                    "prop_id": "$prop_id",
                    "room_type_id": {"$ifNull": ["$room_type_id", ""]},
                    "booking_source": {"$ifNull": ["$booking_source", ""]},
                    "status": {"$ifNull": ["$status", ""]},
                },
                "bookings": {"$sum": 1},
                "nights": {"$sum": {"$ifNull": ["$total_nights", 1]}},
                "revenue_usd": {"$sum": {"$ifNull": ["$total_price", 0]}},
                "adults": {"$sum": {"$ifNull": ["$adults", 0]}},
                "children": {"$sum": {"$ifNull": ["$children", 0]}},
                "cancelled": {
                    "$sum": {
                        "$cond": [
                            {"$in": [{"$toLower": {"$ifNull": ["$status", ""]}}, ["cancelled", "canceled", "cancelled_by_guest", "cancelled_by_hotel"]]},
                            1,
                            0,
                        ]
                    }
                },
            }
        },
        {"$sort": {"_id.date": 1}},
    ]
    docs = list(db.booking_orders.aggregate(pipeline, allowDiskUse=True))
    return [
        {
            "date": _parse_day(item["_id"]["date"]),
            "prop_id": item["_id"]["prop_id"],
            "room_type_id": item["_id"]["room_type_id"],
            "booking_source": item["_id"]["booking_source"],
            "status": item["_id"]["status"],
            "bookings": item["bookings"],
            "nights": item["nights"],
            "revenue_usd": item["revenue_usd"],
            "adults": item["adults"],
            "children": item["children"],
            "cancelled": item["cancelled"],
        }
        for item in docs
        if item["_id"]["date"]
    ]


def extract_kpi_booking_nights_daily(client, db_name: str) -> list[dict[str, Any]]:
    """Expande cada reserva a una fila por noche de estancia.

    ``total_price`` no trae desglose nocturno en Mongo, por lo que se prorratea
    linealmente entre noches y habitaciones. La moneda se conserva sin convertir;
    nunca se suman importes de monedas distintas en una misma fila.
    """
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        pipeline = [
            {"$match": {
                "check_in_date": {"$type": "string"},
                "check_out_date": {"$type": "string"},
            }},
            {"$set": {
                "_check_in": {"$dateFromString": {"dateString": {"$substrBytes": ["$check_in_date", 0, 10]}, "onError": None, "onNull": None}},
                "_check_out": {"$dateFromString": {"dateString": {"$substrBytes": ["$check_out_date", 0, 10]}, "onError": None, "onNull": None}},
                "_rooms": {"$max": [{"$convert": {"input": "$rooms", "to": "int", "onError": 1, "onNull": 1}}, 1]},
            }},
            {"$match": {"$expr": {"$and": [
                {"$ne": ["$_check_in", None]}, {"$ne": ["$_check_out", None]},
                {"$gt": ["$_check_out", "$_check_in"]},
            ]}}},
            {"$set": {
                "_nights": {"$dateDiff": {"startDate": "$_check_in", "endDate": "$_check_out", "unit": "day"}},
            }},
            {"$set": {
                "_night_offsets": {"$range": [0, "$_nights"]},
                "_is_cancelled": {"$in": [{"$toLower": {"$ifNull": ["$status", ""]}}, ["cancelled", "canceled", "cancelled_by_guest", "cancelled_by_hotel"]]},
            }},
            {"$unwind": "$_night_offsets"},
            {"$set": {
                "occupied_date": {"$dateAdd": {"startDate": "$_check_in", "unit": "day", "amount": "$_night_offsets"}},
                "_night_revenue": {"$divide": [{"$ifNull": ["$total_price", 0]}, {"$multiply": ["$_nights", "$_rooms"]}]},
            }},
            {"$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$occupied_date"}},
                    "prop_id": "$prop_id", "room_type_id": {"$ifNull": ["$room_type_id", ""]},
                    "currency": {"$toUpper": {"$ifNull": ["$currency", ""]}},
                },
                "rooms_sold": {"$sum": {"$cond": ["$_is_cancelled", 0, "$_rooms"]}},
                "room_nights": {"$sum": {"$cond": ["$_is_cancelled", 0, "$_rooms"]}},
                "revenue": {"$sum": {"$cond": ["$_is_cancelled", 0, "$_night_revenue"]}},
                "cancelled_rooms": {"$sum": {"$cond": ["$_is_cancelled", "$_rooms", 0]}},
                "adults": {"$sum": {"$cond": ["$_is_cancelled", 0, {"$ifNull": ["$adults", 0]}]}},
                "children": {"$sum": {"$cond": ["$_is_cancelled", 0, {"$ifNull": ["$children", 0]}]}},
            }},
            {"$sort": {"_id.date": 1}},
        ]
        docs = list(db.booking_orders.aggregate(pipeline, allowDiskUse=True))
        return [{
            "date": item["_id"]["date"], "prop_id": item["_id"]["prop_id"],
            "room_type_id": item["_id"]["room_type_id"], "currency": item["_id"]["currency"],
            "rooms_sold": int(item["rooms_sold"]), "room_nights": int(item["room_nights"]),
            "revenue": float(item["revenue"] or 0), "cancelled_rooms": int(item["cancelled_rooms"]),
            "adults": int(item["adults"]), "children": int(item["children"]),
        } for item in docs]
    finally:
        if owns:
            mongo.close()


def extract_kpi_inventory_daily(client, db_name: str) -> list[dict[str, Any]]:
    """Agrega inventario por día, hotel y tipo de habitación."""
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        pipeline = [{"$group": {
            "_id": {"date": "$date", "prop_id": "$prop_id", "room_type_id": {"$ifNull": ["$room_type_id", ""]}},
            "available_rooms": {"$sum": {"$ifNull": ["$available_rooms", 0]}},
            "blocked_rooms": {"$sum": {"$ifNull": ["$blocked_rooms", 0]}},
            "total_rooms": {"$sum": {"$ifNull": ["$total_rooms", 0]}},
        }}, {"$sort": {"_id.date": 1}}]
        return [{"date": _parse_day(x["_id"]["date"]), "prop_id": x["_id"]["prop_id"], "room_type_id": x["_id"]["room_type_id"], "available_rooms": int(x["available_rooms"]), "blocked_rooms": int(x["blocked_rooms"]), "total_rooms": int(x["total_rooms"])} for x in db.room_inventory_calendar.aggregate(pipeline, allowDiskUse=True)]
    finally:
        if owns:
            mongo.close()


def extract_kpi_rate_daily(client, db_name: str) -> list[dict[str, Any]]:
    """Agrega tarifa publicada por día/hotel/plan.

    ``hotel_rate_calendar`` no tiene currency ni room_type_id en el esquema
    actual; esos campos permanecen vacíos para no fabricar una correspondencia.
    """
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        pipeline = [{"$group": {
            "_id": {"date": "$date", "prop_id": "$prop_id", "rate_plan_id": "$rate_plan_id"},
            "published_rate": {"$avg": {"$ifNull": ["$rate_amount", 0]}},
            "closed": {"$max": {"$cond": [{"$eq": ["$is_closed", True]}, 1, 0]}},
        }}, {"$sort": {"_id.date": 1}}]
        rate_plans = {
            doc.get("rate_plan_id"): doc
            for doc in db.rate_plans.find({}, {"rate_plan_id": 1, "currency": 1, "applicable_room_types": 1})
        }
        rows: list[dict[str, Any]] = []
        for item in db.hotel_rate_calendar.aggregate(pipeline, allowDiskUse=True):
            plan = rate_plans.get(item["_id"]["rate_plan_id"], {})
            applicable = plan.get("applicable_room_types") or []
            # Vacío significa que el origen no permite saber si aplica a un
            # tipo concreto; se conserva como fila de plan, sin cruzarla.
            room_types = [str(value) for value in applicable] or [""]
            for room_type_id in room_types:
                rows.append({
                    "date": _parse_day(item["_id"]["date"]),
                    "prop_id": item["_id"]["prop_id"],
                    "rate_plan_id": item["_id"]["rate_plan_id"],
                    "currency": str(plan.get("currency") or "").upper(),
                    "room_type_id": room_type_id,
                    "published_rate": float(item["published_rate"] or 0),
                    "closed": bool(item["closed"]),
                })
        return rows
    finally:
        if owns:
            mongo.close()


def extract_kpi_room_performance_daily(client, db_name: str) -> list[dict[str, Any]]:
    """Construye el KPI compuesto en memoria a partir de las tres agregaciones.

    El cruce es por fecha/hotel/tipo. Las tarifas publicadas solo se asocian
    cuando tienen esa misma clave; con el esquema actual quedan no asociadas y
    ``published_rate``/``rate_variance`` quedan nulos, evitando un RevPAR falso.
    """
    bookings = extract_kpi_booking_nights_daily(client, db_name)
    inventory = extract_kpi_inventory_daily(client, db_name)
    rates = extract_kpi_rate_daily(client, db_name)
    inv_map = {(x["date"], x["prop_id"], x["room_type_id"]): x for x in inventory}
    rate_candidates: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for rate in rates:
        if rate["room_type_id"]:
            rate_candidates.setdefault((rate["date"], rate["prop_id"], rate["room_type_id"]), []).append(rate)
    # Una tarifa publicada solo se cruza si hay exactamente una candidata;
    # múltiples planes serían ambiguos sin rate_plan_id en booking_orders.
    rate_map = {key: values[0] for key, values in rate_candidates.items() if len(values) == 1}
    result: dict[tuple[Any, ...], dict[str, Any]] = {}
    for inv in inventory:
        key = (inv["date"], inv["prop_id"], inv["room_type_id"], "")
        result[key] = {
            "date": inv["date"], "prop_id": inv["prop_id"], "room_type_id": inv["room_type_id"],
            "currency": "", "rooms_sold": 0, "room_nights": 0, "revenue": 0.0,
            "cancelled_rooms": 0, "adults": 0, "children": 0,
            "available_rooms": inv["available_rooms"], "total_rooms": inv["total_rooms"],
            "blocked_rooms": inv["blocked_rooms"], "published_rate": None, "rate_variance": None,
        }
    for booking in bookings:
        key = (booking["date"], booking["prop_id"], booking["room_type_id"], booking["currency"])
        row = result.setdefault(key, {**booking, "available_rooms": 0, "total_rooms": 0, "blocked_rooms": 0, "published_rate": None, "rate_variance": None})
        inv = inv_map.get((booking["date"], booking["prop_id"], booking["room_type_id"]))
        if inv:
            row.update({k: inv[k] for k in ("available_rooms", "total_rooms", "blocked_rooms")})
        rate = rate_map.get((booking["date"], booking["prop_id"], booking["room_type_id"]))
        if rate and (not rate["currency"] or rate["currency"] == booking["currency"]):
            row["published_rate"] = rate["published_rate"]
            row["rate_variance"] = (row["revenue"] / row["room_nights"]) - rate["published_rate"] if row["room_nights"] else 0
    return list(result.values())


def extract_kpi_review_daily(client, db_name: str) -> list[dict[str, Any]]:
    """Agrega reputación por día y propiedad desde ``reviews``.

    Las métricas se calculan únicamente con campos observados en Mongo:
    rating, moderation_status, staff_response(_at), moderated_at y sentimiento.
    Los tiempos inexistentes permanecen en cero y se reportan con contadores,
    nunca se rellenan con una duración inventada.
    """
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        pipeline = [
            {"$match": {"created_at": {"$type": "date"}}},
            {"$set": {
                "_day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "_status": {"$toLower": {"$trim": {"input": {"$ifNull": ["$moderation_status", "pending"]}}}},
                "_has_response": {"$and": [
                    {"$ne": [{"$ifNull": ["$staff_response", None]}, None]},
                    {"$ne": [{"$ifNull": ["$staff_response", ""]}, ""]},
                ]},
                "_moderated_at": {"$convert": {"input": "$moderated_at", "to": "date", "onError": None, "onNull": None}},
                "_staff_response_at": {"$convert": {"input": "$staff_response_at", "to": "date", "onError": None, "onNull": None}},
            }},
            {"$set": {
                "_moderation_ms": {"$cond": [
                    {"$and": [{"$eq": [{"$type": "$_moderated_at"}, "date"]}, {"$eq": [{"$type": "$created_at"}, "date"]}]},
                    {"$subtract": ["$_moderated_at", "$created_at"]},
                    None,
                ]},
                "_response_ms": {"$cond": [
                    {"$and": [{"$eq": [{"$type": "$_staff_response_at"}, "date"]}, {"$eq": [{"$type": "$created_at"}, "date"]}]},
                    {"$subtract": ["$_staff_response_at", "$created_at"]},
                    None,
                ]},
            }},
            {"$group": {
                "_id": {"date": "$_day", "prop_id": "$prop_id"},
                "reviews": {"$sum": 1},
                "rating_sum": {"$sum": {"$cond": [{"$eq": ["$_status", "approved"]}, {"$ifNull": ["$rating", 0]}, 0]}},
                "approved": {"$sum": {"$cond": [{"$eq": ["$_status", "approved"]}, 1, 0]}},
                "pending": {"$sum": {"$cond": [{"$eq": ["$_status", "pending"]}, 1, 0]}},
                "rejected": {"$sum": {"$cond": [{"$eq": ["$_status", "rejected"]}, 1, 0]}},
                "responded": {"$sum": {"$cond": ["$_has_response", 1, 0]}},
                "positive": {"$sum": {"$cond": [{"$eq": [{"$toLower": {"$ifNull": ["$sentiment_label", ""]}}, "positive"]}, 1, 0]}},
                "neutral": {"$sum": {"$cond": [{"$eq": [{"$toLower": {"$ifNull": ["$sentiment_label", ""]}}, "neutral"]}, 1, 0]}},
                "negative": {"$sum": {"$cond": [{"$eq": [{"$toLower": {"$ifNull": ["$sentiment_label", ""]}}, "negative"]}, 1, 0]}},
                "moderated_count": {"$sum": {"$cond": [{"$gte": [{"$ifNull": ["$_moderation_ms", -1]}, 0]}, 1, 0]}},
                "moderation_ms_sum": {"$sum": {"$cond": [{"$gte": [{"$ifNull": ["$_moderation_ms", -1]}, 0]}, "$_moderation_ms", 0]}},
                "responded_count": {"$sum": {"$cond": [{"$gte": [{"$ifNull": ["$_response_ms", -1]}, 0]}, 1, 0]}},
                "response_ms_sum": {"$sum": {"$cond": [{"$gte": [{"$ifNull": ["$_response_ms", -1]}, 0]}, "$_response_ms", 0]}},
            }},
            {"$sort": {"_id.date": 1}},
        ]
        docs = list(db.reviews.aggregate(pipeline, allowDiskUse=True))
        rows: list[dict[str, Any]] = []
        for item in docs:
            reviews = int(item["reviews"])
            moderated_count = int(item["moderated_count"])
            responded_count = int(item["responded_count"])
            rows.append({
                "date": item["_id"]["date"], "prop_id": item["_id"].get("prop_id", 0),
                "reviews": reviews, "rating_sum": float(item["rating_sum"] or 0),
                "avg_rating": float(item["rating_sum"] or 0) / int(item["approved"] or 0) if item["approved"] else 0,
                "approved": int(item["approved"]), "pending": int(item["pending"]), "rejected": int(item["rejected"]),
                "responded": int(item["responded"]), "positive": int(item["positive"]),
                "neutral": int(item["neutral"]), "negative": int(item["negative"]),
                "moderated_count": moderated_count,
                "avg_moderation_minutes": float(item["moderation_ms_sum"] or 0) / moderated_count / 60000 if moderated_count else None,
                "responded_count": responded_count,
                "avg_response_minutes": float(item["response_ms_sum"] or 0) / responded_count / 60000 if responded_count else None,
            })
        return rows
    finally:
        if owns:
            mongo.close()


def _as_datetime(value: Any) -> datetime | None:
    """Parsea fechas Mongo mixtas sin convertir valores inválidos en falsos timestamps."""
    if isinstance(value, datetime):
        return value
    if value is None:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _doc_day(doc: dict[str, Any], *fields: str) -> str:
    for field in fields:
        value = doc.get(field)
        parsed = _as_datetime(value)
        if parsed:
            return parsed.strftime("%Y-%m-%d")
        day = _parse_day(value)
        if day:
            return day
    return ""


def _minutes_between(start: Any, end: Any) -> float | None:
    first = _as_datetime(start)
    second = _as_datetime(end)
    if not first or not second or second < first:
        return None
    return (second - first).total_seconds() / 60


def _add_metric(bucket: dict[str, Any], key: str, value: float | int = 1) -> None:
    bucket[key] = bucket.get(key, 0) + value


def extract_kpi_housekeeping_daily(client, db_name: str) -> list[dict[str, Any]]:
    """Agrega operaciones por día y propiedad, sin copiar documentos a ClickHouse.

    La rotación solo usa pares observables en ``room_status_history``:
    un estado sucio (`vacant_dirty`/`occupied_dirty`) seguido por una transición
    limpia (`vacant_clean`/`inspected`) con timestamps válidos. Si falta una de
    esas marcas, el caso no entra en el promedio y ``rotation_observed`` lo deja
    explícito.
    """
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        by_key: dict[tuple[str, int], dict[str, Any]] = {}

        def bucket(day: str, prop_id: Any) -> dict[str, Any]:
            if not day:
                return {}
            try:
                normalized_prop_id = int(prop_id or 0)
            except (TypeError, ValueError):
                normalized_prop_id = 0
            key = (day, normalized_prop_id)
            if key not in by_key:
                by_key[key] = {"date": day, "prop_id": key[1]}
            return by_key[key]

        def add_task_metrics(collection: str, *, maintenance: bool = False) -> None:
            projection = {
                "prop_id": 1, "scheduled_date": 1, "created_at": 1,
                "started_at": 1, "completed_at": 1, "status": 1,
                "room_label": 1, "hotel_room_id": 1, "room_id": 1,
            }
            for doc in db[collection].find({"status": {"$ne": "deleted"}}, projection):
                day = _doc_day(doc, "scheduled_date", "completed_at", "created_at")
                if not day:
                    continue
                row = bucket(day, doc.get("prop_id"))
                prefix = "maintenance" if maintenance else "tasks"
                _add_metric(row, f"{prefix}_total")
                if doc.get("status") == "completed":
                    _add_metric(row, f"{prefix}_completed")
                completed = doc.get("completed_at")
                if completed:
                    _add_metric(row, f"{prefix}_with_completed_at")
                    scheduled_day = _parse_day(doc.get("scheduled_date"))
                    completed_day = _parse_day(completed)
                    if scheduled_day and completed_day and completed_day <= scheduled_day:
                        _add_metric(row, f"{prefix}_completed_on_time")
                if not maintenance:
                    minutes = _minutes_between(doc.get("started_at"), doc.get("completed_at"))
                    if minutes is not None:
                        row.setdefault("_cleaning_minutes", []).append(minutes)
                    if doc.get("status") == "completed":
                        _add_metric(row, "rooms_cleaned")
                    if doc.get("room_label") or doc.get("hotel_room_id") or doc.get("room_id"):
                        _add_metric(row, "rooms_to_clean", 0)

        add_task_metrics("housekeeping_tasks")
        add_task_metrics("maintenance_tasks", maintenance=True)

        for doc in db.room_status_history.find({}, {"prop_id": 1, "created_at": 1, "new_status": 1, "old_status": 1, "hotel_room_id": 1, "room_label": 1}):
            day = _doc_day(doc, "created_at")
            if not day:
                continue
            row = bucket(day, doc.get("prop_id"))
            _add_metric(row, "rooms_status_events")
            if doc.get("new_status") in {"vacant_dirty", "occupied_dirty", "cleaning_in_progress"}:
                _add_metric(row, "rooms_to_clean")
            if doc.get("new_status") in {"cleaning_completed", "vacant_clean", "inspected"}:
                _add_metric(row, "rooms_available_after_cleaning")

        # La fuente de disponibilidad ya está agregada por día/tipo; aquí solo
        # sumamos sus números para el KPI de operaciones.
        for doc in db.room_inventory_calendar.find({}, {"date": 1, "prop_id": 1, "available_rooms": 1, "blocked_rooms": 1, "total_rooms": 1}):
            day = _doc_day(doc, "date")
            if not day:
                continue
            row = bucket(day, doc.get("prop_id"))
            _add_metric(row, "inventory_available_rooms", int(doc.get("available_rooms") or 0))
            _add_metric(row, "inventory_blocked_rooms", int(doc.get("blocked_rooms") or 0))
            _add_metric(row, "inventory_total_rooms", int(doc.get("total_rooms") or 0))

        for doc in db.additional_charges.find({}, {"prop_id": 1, "charge_date": 1, "created_at": 1, "total": 1, "amount": 1, "quantity": 1}):
            day = _doc_day(doc, "charge_date", "created_at")
            if not day:
                continue
            row = bucket(day, doc.get("prop_id"))
            _add_metric(row, "charges_total")
            amount = doc.get("total")
            if amount is None:
                amount = (doc.get("amount") or 0) * max(1, int(doc.get("quantity") or 1))
            _add_metric(row, "charges_amount", float(amount or 0))

        # supplier_country_coverage es un indicador de calidad de inventario,
        # no una réplica de lotes: cuenta lotes que ya tienen país informado.
        for doc in db.fact_inventory.find({}, {"prop_id": 1, "acquired_at": 1, "supplier_country": 1}):
            day = _doc_day(doc, "acquired_at")
            if not day:
                continue
            row = bucket(day, doc.get("prop_id"))
            if str(doc.get("supplier_country") or "").strip():
                _add_metric(row, "supplier_country_coverage")

        # Deriva únicamente pares consecutivos con timestamps confiables.
        history: dict[tuple[int, str], list[dict[str, Any]]] = {}
        for doc in db.room_status_history.find({}, {"prop_id": 1, "room_label": 1, "hotel_room_id": 1, "new_status": 1, "created_at": 1}):
            room_key = str(doc.get("hotel_room_id") or doc.get("room_label") or "")
            parsed = _as_datetime(doc.get("created_at"))
            if room_key and parsed:
                history.setdefault((int(doc.get("prop_id") or 0), room_key), []).append({**doc, "_parsed": parsed})
        for (prop_id, _room), events in history.items():
            events.sort(key=lambda item: item["_parsed"])
            for previous, current in zip(events, events[1:]):
                if previous.get("new_status") not in {"vacant_dirty", "occupied_dirty", "cleaning_in_progress"}:
                    continue
                if current.get("new_status") not in {"cleaning_completed", "vacant_clean", "inspected"}:
                    continue
                minutes = (current["_parsed"] - previous["_parsed"]).total_seconds() / 60
                if minutes < 0:
                    continue
                row = bucket(current["_parsed"].strftime("%Y-%m-%d"), prop_id)
                row.setdefault("_rotation_minutes", []).append(minutes)
                _add_metric(row, "rotation_observed")

        rows: list[dict[str, Any]] = []
        for row in by_key.values():
            cleaning = row.pop("_cleaning_minutes", [])
            rotation = row.pop("_rotation_minutes", [])
            row["avg_cleaning_minutes"] = sum(cleaning) / len(cleaning) if cleaning else None
            row["avg_checkout_to_available_minutes"] = sum(rotation) / len(rotation) if rotation else None
            rows.append(row)
        return sorted(rows, key=lambda item: (item["date"], item["prop_id"]))
    finally:
        if owns:
            mongo.close()


def extract_kpi_invoice_daily(client, db_name: str) -> list[dict[str, Any]]:
    """Agrega facturación por día × hotel × estado (F1.4).

    No copia facturas: solo viajan agregados. La fecha es ``issued_at``
    (con respaldo ``created_at``) porque el informe responde cuánto se
    facturó por período. Los importes se suman en su moneda original sin
    conversión; ``paid_total`` incluye ``paid`` y ``refunded`` (una factura
    reembolsada sí fue cobrada antes de revertirse), ``pending_total`` es
    ``issued`` y ``cancelled_total`` es ``cancelled``. Nunca se inventan.
    """
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        by_key: dict[tuple[str, int, str], dict[str, Any]] = {}
        projection = {
            "prop_id": 1, "status": 1, "subtotal": 1, "taxes": 1,
            "total": 1, "issued_at": 1, "created_at": 1,
        }
        for doc in db.reservation_invoices.find({}, projection):
            day = _doc_day(doc, "issued_at", "created_at")
            if not day:
                continue
            try:
                normalized_prop_id = int(doc.get("prop_id") or 0)
            except (TypeError, ValueError):
                normalized_prop_id = 0
            status = str(doc.get("status") or "").strip().lower()
            key = (day, normalized_prop_id, status)
            row = by_key.get(key)
            if row is None:
                row = {"date": day, "prop_id": normalized_prop_id, "status": status}
                by_key[key] = row
            total = float(doc.get("total") or 0)
            _add_metric(row, "invoice_count")
            _add_metric(row, "subtotal", float(doc.get("subtotal") or 0))
            _add_metric(row, "taxes", float(doc.get("taxes") or 0))
            _add_metric(row, "total", total)
            if status in {"paid", "refunded"}:
                _add_metric(row, "paid_total", total)
            elif status == "issued":
                _add_metric(row, "pending_total", total)
            elif status == "cancelled":
                _add_metric(row, "cancelled_total", total)
        return sorted(by_key.values(), key=lambda item: (item["date"], item["prop_id"], item["status"]))
    finally:
        if owns:
            mongo.close()


def extract_kpi_payment_daily(client, db_name: str) -> list[dict[str, Any]]:
    """Agrega pagos por día × hotel × método × estado (F1.5).

    El saldo pendiente NO se deriva solo de pagos: por cada (día, propiedad) se
    cruza el total facturado (facturas no anuladas emitidas ese día) contra lo
    cobrado (pagos confirmados ese día). Las columnas de contexto se repiten en
    cada fila del día (desnormalización controlada) y el endpoint las agrega por
    claves distintas (fecha, prop_id). Los días con facturación pero sin pagos
    emiten una fila sintética ``no_payment`` para que el pendiente sea visible.
    """
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        by_key: dict[tuple[str, int, str, str], dict[str, Any]] = {}

        def bucket(day: str, prop_id: Any, method: str, status: str) -> dict[str, Any]:
            try:
                normalized_prop_id = int(prop_id or 0)
            except (TypeError, ValueError):
                normalized_prop_id = 0
            key = (day, normalized_prop_id, method, status)
            if key not in by_key:
                by_key[key] = {
                    "date": day, "prop_id": normalized_prop_id,
                    "method": method, "status": status,
                }
            return by_key[key]

        # 1. Grupos de pagos.
        payment_projection = {
            "prop_id": 1, "method": 1, "status": 1, "amount": 1,
            "paid_at": 1, "created_at": 1,
        }
        for doc in db.reservation_payments.find({}, payment_projection):
            day = _doc_day(doc, "paid_at", "created_at")
            if not day:
                continue
            method = str(doc.get("method") or "").strip().lower()
            status = str(doc.get("status") or "").strip().lower()
            row = bucket(day, doc.get("prop_id"), method, status)
            amount = float(doc.get("amount") or 0)
            _add_metric(row, "payment_count")
            if status == "confirmed":
                _add_metric(row, "paid_amount", amount)
            elif status == "refunded":
                _add_metric(row, "refunded_amount", amount)
            elif status in {"failed", "rejected", "declined", "error"}:
                _add_metric(row, "failed_amount", amount)

        # 2. Contexto de facturación por (día, propiedad).
        invoiced_by_day: dict[tuple[str, int], float] = {}
        collected_by_day: dict[tuple[str, int], float] = {}
        invoice_projection = {"prop_id": 1, "status": 1, "total": 1, "issued_at": 1, "created_at": 1}
        for doc in db.reservation_invoices.find({}, invoice_projection):
            day = _doc_day(doc, "issued_at", "created_at")
            if not day:
                continue
            status = str(doc.get("status") or "").strip().lower()
            if status == "cancelled":
                continue
            try:
                prop = int(doc.get("prop_id") or 0)
            except (TypeError, ValueError):
                prop = 0
            key = (day, prop)
            invoiced_by_day[key] = invoiced_by_day.get(key, 0.0) + float(doc.get("total") or 0)
        for row in by_key.values():
            if row.get("status") == "confirmed":
                key = (row["date"], row["prop_id"])
                collected_by_day[key] = collected_by_day.get(key, 0.0) + float(row.get("paid_amount") or 0)

        # 3. Adjuntar contexto a cada fila y emitir fila sintética para días
        #    con facturación pero sin ningún pago.
        for (day, prop, _method, _status), row in by_key.items():
            inv = invoiced_by_day.get((day, prop), 0.0)
            col = collected_by_day.get((day, prop), 0.0)
            row["invoiced_amount"] = round(inv, 2)
            row["collected_amount"] = round(col, 2)
            row["outstanding_amount"] = round(inv - col, 2)
        for (day, prop), inv in invoiced_by_day.items():
            if (day, prop) not in {(r["date"], r["prop_id"]) for r in by_key.values()}:
                col = collected_by_day.get((day, prop), 0.0)
                by_key[(day, prop, "", "no_payment")] = {
                    "date": day, "prop_id": prop, "method": "", "status": "no_payment",
                    "payment_count": 0, "paid_amount": 0, "refunded_amount": 0, "failed_amount": 0,
                    "invoiced_amount": round(inv, 2), "collected_amount": round(col, 2),
                    "outstanding_amount": round(inv - col, 2),
                }
        return sorted(by_key.values(), key=lambda item: (item["date"], item["prop_id"], item["method"], item["status"]))
    finally:
        if owns:
            mongo.close()


def extract_kpi_funnel_daily(client, db_name: str) -> list[dict[str, Any]]:
    """Agrega la Fact grande por día × país × destino para análisis global.

    Esta tabla conserva el resumen compacto histórico. Para el informe táctico
    por hotel y canal se usa ``extract_kpi_funnel_property_channel_daily``.
    ``revenue_usd`` solo suma reservas (`reserva_bool=true`), no el precio de
    todas las búsquedas.
    """
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        return _extract_kpi_funnel(db)
    finally:
        if owns:
            mongo.close()


def _extract_kpi_funnel(db) -> list[dict[str, Any]]:
    pipeline = [
        {
            "$group": {
                "_id": {
                    "date": {"$ifNull": ["$date_key", ""]},
                    "visitor_location_country_id": {
                        "$ifNull": ["$visitor_location_country_id", 0]
                    },
                    "srch_destination_id": {"$ifNull": ["$srch_destination_id", 0]},
                },
                "searches": {"$sum": 1},
                "clicks": {"$sum": {"$ifNull": ["$click_bool", False]}},
                "reservations": {"$sum": {"$ifNull": ["$reserva_bool", False]}},
                "revenue_usd": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$reserva_bool", True]},
                            {"$ifNull": ["$reservas_brutas_usd", {"$ifNull": ["$price_usd", 0]}]},
                            0,
                        ]
                    }
                },
                "avg_booking_window": {"$avg": {"$ifNull": ["$srch_booking_window", 0]}},
            }
        },
        {"$sort": {"_id.date": 1}},
    ]
    docs = list(db.fact_hotel_reservations.aggregate(pipeline, allowDiskUse=True))
    return [
        {
            "date": _parse_day(item["_id"]["date"]),
            "visitor_location_country_id": item["_id"]["visitor_location_country_id"],
            "srch_destination_id": item["_id"]["srch_destination_id"],
            "searches": item["searches"],
            "clicks": int(item["clicks"]),
            "reservations": int(item["reservations"]),
            "revenue_usd": float(item["revenue_usd"] or 0),
            "avg_booking_window": float(item["avg_booking_window"] or 0),
        }
        for item in docs
        if item["_id"]["date"]
    ]


def extract_kpi_funnel_property_channel_daily(client, db_name: str) -> list[dict[str, Any]]:
    """Agrega el embudo para la vista táctica por hotel y canal.

    Granularidad: día × prop_id × site_id × país visitante × destino.
    La Fact conserva todos esos campos y la agregación se ejecuta dentro de
    MongoDB; solo los grupos y sus métricas viajan a ClickHouse. El volumen
    La granularidad completa produce 785K+ grupos en el dataset sintético;
    por eso esta tabla se filtra a los IDs operacionales conocidos y se mantiene
    separada del resumen global. En los datos actuales esa intersección produce
    solo 22 filas, y sus ``prop_id`` siguen siendo IDs del catálogo de búsqueda:
    no deben interpretarse como una relación con reservas operacionales hasta
    que exista una fuente de eventos propia.
    """
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        operational_prop_ids = _operational_prop_ids(db)
        if not operational_prop_ids:
            return []

        pipeline = [
            {"$match": {"prop_id": {"$in": operational_prop_ids}}},
            {
                "$group": {
                    "_id": {
                        "date": {"$ifNull": ["$date_key", ""]},
                        "prop_id": {"$ifNull": ["$prop_id", 0]},
                        "site_id": {"$ifNull": ["$site_id", 0]},
                        "visitor_location_country_id": {
                            "$ifNull": ["$visitor_location_country_id", 0]
                        },
                        "srch_destination_id": {"$ifNull": ["$srch_destination_id", 0]},
                    },
                    "searches": {"$sum": 1},
                    "clicks": {"$sum": {"$cond": ["$click_bool", 1, 0]}},
                    "reservations": {"$sum": {"$cond": ["$reserva_bool", 1, 0]}},
                    "revenue_usd": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$reserva_bool", True]},
                                {"$ifNull": ["$reservas_brutas_usd", {"$ifNull": ["$price_usd", 0]}]},
                                0,
                            ]
                        }
                    },
                    "avg_booking_window": {
                        "$avg": {"$ifNull": ["$srch_booking_window", 0]}
                    },
                    "avg_length_of_stay": {
                        "$avg": {"$ifNull": ["$srch_length_of_stay", 0]}
                    },
                    "adults": {"$sum": {"$ifNull": ["$srch_adults_count", 0]}},
                    "children": {"$sum": {"$ifNull": ["$srch_children_count", 0]}},
                    "rooms": {"$sum": {"$ifNull": ["$srch_room_count", 0]}},
                }
            },
            {"$sort": {"_id.date": 1}},
        ]
        docs = list(db.fact_hotel_reservations.aggregate(pipeline, allowDiskUse=True))
        return [
            {
                "date": _parse_day(item["_id"]["date"]),
                "prop_id": item["_id"]["prop_id"],
                "site_id": item["_id"]["site_id"],
                "visitor_location_country_id": item["_id"]["visitor_location_country_id"],
                "srch_destination_id": item["_id"]["srch_destination_id"],
                "searches": int(item["searches"]),
                "clicks": int(item["clicks"]),
                "reservations": int(item["reservations"]),
                "revenue_usd": float(item["revenue_usd"] or 0),
                "avg_booking_window": float(item["avg_booking_window"] or 0),
                "avg_length_of_stay": float(item["avg_length_of_stay"] or 0),
                "adults": int(item["adults"]),
                "children": int(item["children"]),
                "rooms": int(item["rooms"]),
            }
            for item in docs
            if item["_id"]["date"]
        ]
    finally:
        if owns:
            mongo.close()


def _label_key(value: Any) -> str:
    """Normaliza IDs de catálogos para casar int/string/ObjectId de Mongo."""
    return "" if value is None else str(value).strip()


def _label_map(
    db,
    collection: str,
    key_fields: tuple[str, ...],
    label_fields: tuple[str, ...],
    query: dict[str, Any] | None = None,
) -> dict[tuple[str, ...], str]:
    """Lee un catálogo pequeño para enriquecer KPIs sin publicarlo como dimensión."""
    result: dict[tuple[str, ...], str] = {}
    projection = {field: 1 for field in (*key_fields, *label_fields)}
    for doc in db[collection].find(query or {}, projection):
        key = tuple(_label_key(doc.get(field)) for field in key_fields)
        label = next((str(doc.get(field)).strip() for field in label_fields if doc.get(field)), "")
        if any(key):
            result[key] = label
    return result


def _enrich_kpi_labels(db, payload: dict[str, list[dict[str, Any]]]) -> None:
    """Añade labels vigentes a cada agregado KPI en el mismo proceso ETL.

    Los IDs permanecen para trazabilidad y filtros exactos; los labels evitan
    JOINs en ClickHouse y una segunda consulta a Mongo desde los dashboards.
    """
    operational_prop_ids = _operational_prop_ids(db)
    hotel_query = {"prop_id": {"$in": operational_prop_ids}} if operational_prop_ids else {"_id": {"$exists": False}}
    hotel_labels = _label_map(
        db, "dim_hotels", ("prop_id",),
        ("hotel_label", "display_name", "hotel_name", "name"), hotel_query,
    )
    room_labels = _label_map(db, "room_types", ("prop_id", "room_type_id"), ("name", "room_type_label", "display_name"))
    room_labels.update(_label_map(db, "room_types", ("room_type_id",), ("name", "room_type_label", "display_name")))
    rate_labels = _label_map(db, "rate_plans", ("rate_plan_id",), ("name", "label", "display_name"))
    country_labels = _label_map(db, "dim_visitor_countries", ("visitor_location_country_id",), ("visitor_country_label", "country_display_name", "country_name"))
    destination_labels = _label_map(db, "dim_destinations", ("srch_destination_id",), ("destination_label", "destination_display_name", "destination_name"))
    site_labels = _label_map(db, "dim_sites", ("site_id",), ("site_label", "site_display_name", "site_name"))

    for table_name, rows in payload.items():
        for row in rows:
            if "prop_id" in row:
                row["hotel_label"] = hotel_labels.get((_label_key(row["prop_id"]),), "")
            if "room_type_id" in row:
                room_labels_by_prop = room_labels.get(
                    (_label_key(row.get("prop_id")), _label_key(row["room_type_id"])),
                    "",
                )
                row["room_type_label"] = room_labels_by_prop or room_labels.get((_label_key(row["room_type_id"]),), "")
            if "rate_plan_id" in row:
                row["rate_plan_label"] = rate_labels.get((_label_key(row["rate_plan_id"]),), "")
            if "visitor_location_country_id" in row:
                row["visitor_country_label"] = country_labels.get((_label_key(row["visitor_location_country_id"]),), "")
            if "srch_destination_id" in row:
                row["destination_label"] = destination_labels.get((_label_key(row["srch_destination_id"]),), "")
            if "site_id" in row:
                row["site_label"] = site_labels.get((_label_key(row["site_id"]),), "")


def extract_all(client, db_name: str) -> dict[str, list[dict[str, Any]]]:
    """Extrae los nueve KPI y enriquece sus labels desde catálogos Mongo pequeños.

    Los catálogos se consultan durante el ETL solo para resolver texto; no se
    publican como tablas ClickHouse ni se copian como réplica.
    """
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        payload: dict[str, list[dict[str, Any]]] = {}
        payload["kpi_booking_daily"] = extract_kpi_booking_daily(mongo, db_name)
        payload["kpi_booking_nights_daily"] = extract_kpi_booking_nights_daily(mongo, db_name)
        payload["kpi_inventory_daily"] = extract_kpi_inventory_daily(mongo, db_name)
        payload["kpi_rate_daily"] = extract_kpi_rate_daily(mongo, db_name)
        payload["kpi_room_performance_daily"] = extract_kpi_room_performance_daily(mongo, db_name)
        # Reputación se publica como agregado táctico; el detalle de reviews
        # permanece en MongoDB (operacional) y no cruza a ClickHouse.
        payload["kpi_review_daily"] = extract_kpi_review_daily(mongo, db_name)
        payload["kpi_funnel_daily"] = extract_kpi_funnel_daily(mongo, db_name)
        payload["kpi_funnel_property_channel_daily"] = extract_kpi_funnel_property_channel_daily(
            mongo, db_name
        )
        payload["kpi_housekeeping_daily"] = extract_kpi_housekeeping_daily(mongo, db_name)
        # Facturación táctica: agregado por día/hotel/estado.
        payload["kpi_invoice_daily"] = extract_kpi_invoice_daily(mongo, db_name)
        # Pagos tácticos: agregado por día/hotel/método/estado + contexto de
        # facturación del día para el saldo pendiente.
        payload["kpi_payment_daily"] = extract_kpi_payment_daily(mongo, db_name)
        _enrich_kpi_labels(mongo[db_name], payload)
        return payload
    finally:
        if owns:
            mongo.close()
