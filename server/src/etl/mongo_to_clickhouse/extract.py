"""Extracción MongoDB → KPIs ClickHouse (sin réplica de dimensiones).

Los catálogos se consultan solo para resolver labels durante la extracción.
Los KPIs se agregan con ``$group`` en Mongo: solo viajan filas agregadas y
livianas a ClickHouse.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from config.settings import get_settings
from src.etl.mongo_to_clickhouse.config import OPERATIONAL_COLLECTIONS

# Un snapshot sintético más antiguo que este umbral (90 días) se considera el
# funnel GA03 (2012-2013) y se re-ancla a la ventana reciente. Datos reales
# recientes (2026+) nunca superan el umbral y no se tocan.
FUNNEL_REANCHOR_STALE_DAYS = 90


def _reanchor_funnel_dates(
    rows: list[dict[str, Any]],
    *,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Desplaza fechas de un dataset sintético antiguo a la ventana reciente.

    ``fact_hotel_reservations`` es el dataset GA03 de Expedia con fechas
    2012-2013 (800K docs de demo). Sin re-anclar, los informes estratégicos
    (``strat_market_monthly``) y tácticos (``kpi_funnel_*``) muestran años
    anteriores mientras el resto de tablas operacionales van en 2026. Si el
    máximo de la serie está a más de ``FUNNEL_REANCHOR_STALE_DAYS`` de hoy,
    todas las filas se desplazan hacia adelante para que ese máximo caiga en
    la fecha de anclaje (hoy por defecto), preservando la distribución.

    Si el máximo ya es reciente (datos reales), devuelve las filas intactas.
    """
    if not rows:
        return rows
    today = today or datetime.now(UTC).date()
    parsed: list[date] = []
    for row in rows:
        value = str(row.get("date") or "")[:10]
        if len(value) == 10 and value.replace("-", "").isdigit():
            parsed.append(date.fromisoformat(value))
    if not parsed:
        return rows
    max_day = max(parsed)
    delta = today - max_day
    if delta.days <= FUNNEL_REANCHOR_STALE_DAYS:
        return rows
    for row in rows:
        value = str(row.get("date") or "")[:10]
        if len(value) == 10 and value.replace("-", "").isdigit():
            row["date"] = (date.fromisoformat(value) + delta).isoformat()
    return rows


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
    """Expande cada reserva a una fila por noche de estancia (sin canal).

    ``total_price`` no trae desglose nocturno en Mongo, por lo que se prorratea
    linealmente entre noches y habitaciones. La moneda se conserva sin convertir;
    nunca se suman importes de monedas distintas en una misma fila.
    """
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        return _aggregate_booking_nights(db, include_source=False)
    finally:
        if owns:
            mongo.close()


def _aggregate_booking_nights(db, *, include_source: bool) -> list[dict[str, Any]]:
    """Agregación compartida de noches de estancia por ocupación real.

    ``include_source`` añade ``booking_source`` (canal) a la clave de grupo
    para el informe R1.2 (ADR por fecha, tipo de habitación y canal).
    ``kpi_booking_nights_daily`` no lo usa; ``kpi_room_performance_daily`` sí.
    """
    _id: dict[str, Any] = {
        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$occupied_date"}},
        "prop_id": "$prop_id",
        "room_type_id": {"$ifNull": ["$room_type_id", ""]},
        "currency": {"$toUpper": {"$ifNull": ["$currency", ""]}},
    }
    if include_source:
        _id["booking_source"] = {"$ifNull": ["$booking_source", ""]}
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
            "_id": _id,
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
    rows: list[dict[str, Any]] = []
    for item in docs:
        row: dict[str, Any] = {
            "date": item["_id"]["date"], "prop_id": item["_id"]["prop_id"],
            "room_type_id": item["_id"]["room_type_id"], "currency": item["_id"]["currency"],
            "rooms_sold": int(item["rooms_sold"]), "room_nights": int(item["room_nights"]),
            "revenue": float(item["revenue"] or 0), "cancelled_rooms": int(item["cancelled_rooms"]),
            "adults": int(item["adults"]), "children": int(item["children"]),
        }
        if include_source:
            row["booking_source"] = item["_id"]["booking_source"]
        rows.append(row)
    return rows


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

    R1.2: la clave de granularidad incluye el canal (``booking_source``) además
    de fecha/hotel/tipo/divisa, de modo que el informe puede desglosar el ADR
    por fecha, tipo de habitación y canal. Las tarifas publicadas solo se
    asocian cuando tienen esa misma clave; con el esquema actual quedan no
    asociadas y ``published_rate``/``rate_variance`` quedan nulos, evitando un
    RevPAR falso.
    """
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        bookings = _aggregate_booking_nights(db, include_source=True)
        inventory = extract_kpi_inventory_daily(mongo, db_name)
        rates = extract_kpi_rate_daily(mongo, db_name)
        inv_map = {(x["date"], x["prop_id"], x["room_type_id"]): x for x in inventory}
        rate_candidates: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
        for rate in rates:
            if rate["room_type_id"]:
                rate_candidates.setdefault((rate["date"], rate["prop_id"], rate["room_type_id"]), []).append(rate)
        # Una tarifa publicada solo se cruza si hay exactamente una candidata;
        # múltiples planes serían ambiguos sin rate_plan_id en booking_orders.
        rate_map = {key: values[0] for key, values in rate_candidates.items() if len(values) == 1}
        result: dict[tuple[Any, ...], dict[str, Any]] = {}
        # 1. Las reservas primero: una fila con currency/canal vacíos debe
        #    conservar su revenue y noches, nunca colisionar con el placeholder
        #    de inventario de la misma clave.
        for booking in bookings:
            key = (booking["date"], booking["prop_id"], booking["room_type_id"], booking["currency"], booking["booking_source"])
            row = result.setdefault(key, {**booking, "available_rooms": 0, "total_rooms": 0, "blocked_rooms": 0, "published_rate": None, "rate_variance": None})
            inv = inv_map.get((booking["date"], booking["prop_id"], booking["room_type_id"]))
            if inv:
                row.update({k: inv[k] for k in ("available_rooms", "total_rooms", "blocked_rooms")})
            rate = rate_map.get((booking["date"], booking["prop_id"], booking["room_type_id"]))
            if rate and (not rate["currency"] or rate["currency"] == booking["currency"]):
                row["published_rate"] = rate["published_rate"]
                row["rate_variance"] = (row["revenue"] / row["room_nights"]) - rate["published_rate"] if row["room_nights"] else 0
        # 2. Placeholders de inventario solo para (fecha, hotel, tipo) sin
        #    ninguna reserva: alimentan el denominador de capacidad (ocupación
        #    y RevPAR) sin pisar filas reales.
        booked_keys = {(b["date"], b["prop_id"], b["room_type_id"]) for b in bookings}
        for inv in inventory:
            rt_key = (inv["date"], inv["prop_id"], inv["room_type_id"])
            if rt_key in booked_keys:
                continue
            key = (inv["date"], inv["prop_id"], inv["room_type_id"], "", "")
            result[key] = {
                "date": inv["date"], "prop_id": inv["prop_id"], "room_type_id": inv["room_type_id"],
                "currency": "", "booking_source": "", "rooms_sold": 0, "room_nights": 0, "revenue": 0.0,
                "cancelled_rooms": 0, "adults": 0, "children": 0,
                "available_rooms": inv["available_rooms"], "total_rooms": inv["total_rooms"],
                "blocked_rooms": inv["blocked_rooms"], "published_rate": None, "rate_variance": None,
            }
        return list(result.values())
    finally:
        if owns:
            mongo.close()


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


# Un cierre de tarea o una rotación sucia→limpia en menos de un minuto no
# puede ser una medición real de operación hotelera: son artefactos de datos
# (timestamps casi idénticos en demos/tests). Se excluyen del promedio y se
# reportan con contadores en vez de contaminar la media con duraciones absurdas.
MIN_MEASURABLE_MINUTES = 1.0


def _minutes_between(start: Any, end: Any) -> float | None:
    first = _as_datetime(start)
    second = _as_datetime(end)
    if not first or not second or second < first:
        return None
    minutes = (second - first).total_seconds() / 60
    if minutes < MIN_MEASURABLE_MINUTES:
        return None
    return minutes


def _add_metric(bucket: dict[str, Any], key: str, value: float = 1) -> None:
    bucket[key] = bucket.get(key, 0) + value


def extract_kpi_housekeeping_daily(client, db_name: str) -> list[dict[str, Any]]:
    """Agrega operaciones por día y propiedad, sin copiar documentos a ClickHouse.

    La rotación solo usa pares observables en ``room_status_history``:
    un estado sucio (`vacant_dirty`/`occupied_dirty`) seguido por una transición
    limpia (`vacant_clean`/`inspected`) con timestamps válidos. Si falta una de
    esas marcas, el caso no entra en el promedio y ``rotation_observed`` lo deja
    explícito. Las duraciones menores a un minuto se descartan como ruido de
    medición (timestamps casi idénticos de demos/tests) y no cuentan como
    observación.
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
                if minutes < MIN_MEASURABLE_MINUTES:
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
    """Agrega el embudo de demanda por día × país × destino desde tablas
    OPERATIVAS (click_events + booking_orders), nunca de la fact sintética
    GA03. Para el informe táctico por hotel y canal se usa
    ``extract_kpi_funnel_property_channel_daily``. ``revenue_usd`` solo suma
    reservas confirmadas, no el precio de todas las búsquedas.
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
    """Embudo de demanda desde tablas OPERATIVAS (click_events +
    booking_orders), nunca de la fact sintética GA03 (800K docs de demo).

    - searches/clicks: ``click_events`` (source ``search``/``detail``)
    - reservations/revenue: ``booking_orders`` confirmadas (check_in_date)
    - país/destino: del hotel real (``dim_hotels``: display_country_label,
      city), porque los eventos operativos no traen país visitante propio.

    El resultado mantiene el contrato de ``kpi_funnel_daily`` (día × país ×
    destino con searches/clicks/reservations/revenue), pero con el destino
    identificado por ``prop_id`` del hotel real.
    """
    cancelled = {"cancelled", "canceled", "cancelled_by_guest", "cancelled_by_hotel"}

    # 1) Clics reales: día × prop → searches (source=search) / clicks (source=detail)
    clicks: dict[tuple[str, Any], dict[str, int]] = {}
    for ev in db.click_events.find({}, {"clicked_at": 1, "prop_id": 1, "source": 1}):
        day = _parse_day(ev.get("clicked_at"))
        if not day:
            continue
        key = (day, ev.get("prop_id"))
        bucket = clicks.setdefault(key, {"searches": 0, "clicks": 0})
        if str(ev.get("source") or "").strip().lower() == "search":
            bucket["searches"] += 1
        else:
            bucket["clicks"] += 1

    # 2) Reservas reales: día (check_in) × prop → reservations + revenue
    bookings: dict[tuple[str, Any], dict[str, Any]] = {}
    for bo in db.booking_orders.find({}, {"check_in_date": 1, "prop_id": 1, "total_price": 1, "status": 1}):
        day = _parse_day(bo.get("check_in_date"))
        if not day:
            continue
        if str(bo.get("status") or "").strip().lower() in cancelled:
            continue
        key = (day, bo.get("prop_id"))
        bucket = bookings.setdefault(key, {"reservations": 0, "revenue_usd": 0.0})
        bucket["reservations"] += 1
        bucket["revenue_usd"] += float(bo.get("total_price") or 0)

    # 3) Hoteles reales: prop → país/ciudad (para labels sin JOIN en CH).
    prop_ids = sorted({pid for _, pid in clicks} | {pid for _, pid in bookings}, key=lambda v: (v is None, str(v)))
    hotel_query = {"prop_id": {"$in": prop_ids}} if prop_ids else {"_id": {"$exists": False}}
    hotels: dict[str, dict[str, Any]] = {}
    for doc in db.dim_hotels.find(hotel_query, {"prop_id": 1, "display_country_label": 1, "city": 1, "prop_country_id": 1}):
        hotels[_label_key(doc.get("prop_id"))] = doc

    rows = []
    for day, pid in sorted(clicks.keys() | bookings.keys()):
        hotel = hotels.get(_label_key(pid), {})
        click_bucket = clicks.get((day, pid), {"searches": 0, "clicks": 0})
        booking_bucket = bookings.get((day, pid), {"reservations": 0, "revenue_usd": 0.0})
        rows.append({
            "date": day,
            "visitor_location_country_id": int(hotel.get("prop_country_id") or 0),
            "visitor_country_label": str(hotel.get("display_country_label") or ""),
            "srch_destination_id": int(pid or 0),
            "destination_label": str(hotel.get("city") or ""),
            "searches": click_bucket["searches"],
            "clicks": click_bucket["clicks"],
            "reservations": booking_bucket["reservations"],
            "revenue_usd": round(booking_bucket["revenue_usd"], 2),
            "avg_booking_window": 0.0,
        })
    return rows


def extract_kpi_funnel_property_channel_daily(client, db_name: str) -> list[dict[str, Any]]:
    """Embudo táctico por hotel/canal desde tablas OPERATIVAS (click_events +
    booking_orders), nunca de la fact sintética GA03.

    Granularidad: día × prop_id. Los eventos operativos no modelan el canal de
    búsqueda (site_id), así que este agregado agrupa por hotel real y deja
    ``site_id``/``site_label`` vacíos; el país/destino sale de ``dim_hotels``
    (display_country_label, city). El contrato de columnas de
    ``kpi_funnel_property_channel_daily`` se conserva intacto.
    """
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        return _extract_kpi_funnel_property_channel(mongo[db_name])
    finally:
        if owns:
            mongo.close()


def _extract_kpi_funnel_property_channel(db) -> list[dict[str, Any]]:
    """Implementación del embudo táctico por hotel con fuente operativa."""
    cancelled = {"cancelled", "canceled", "cancelled_by_guest", "cancelled_by_hotel"}

    # 1) Clics reales: día × prop → searches / clicks
    clicks: dict[tuple[str, Any], dict[str, int]] = {}
    for ev in db.click_events.find({}, {"clicked_at": 1, "prop_id": 1, "source": 1}):
        day = _parse_day(ev.get("clicked_at"))
        if not day:
            continue
        key = (day, ev.get("prop_id"))
        bucket = clicks.setdefault(key, {"searches": 0, "clicks": 0})
        if str(ev.get("source") or "").strip().lower() == "search":
            bucket["searches"] += 1
        else:
            bucket["clicks"] += 1

    # 2) Reservas reales: día × prop → reservations + revenue + estancia media
    bookings: dict[tuple[str, Any], dict[str, Any]] = {}
    for bo in db.booking_orders.find(
        {}, {"check_in_date": 1, "prop_id": 1, "total_price": 1, "status": 1,
             "total_nights": 1, "adults": 1, "children": 1, "rooms": 1}
    ):
        day = _parse_day(bo.get("check_in_date"))
        if not day:
            continue
        if str(bo.get("status") or "").strip().lower() in cancelled:
            continue
        key = (day, bo.get("prop_id"))
        bucket = bookings.setdefault(key, {
            "reservations": 0, "revenue_usd": 0.0, "length_sum": 0.0,
            "adults": 0, "children": 0, "rooms": 0,
        })
        bucket["reservations"] += 1
        bucket["revenue_usd"] += float(bo.get("total_price") or 0)
        bucket["length_sum"] += float(bo.get("total_nights") or 0)
        bucket["adults"] += int(bo.get("adults") or 0)
        bucket["children"] += int(bo.get("children") or 0)
        bucket["rooms"] += int(bo.get("rooms") or 0)

    # 3) Hoteles reales: prop → labels.
    prop_ids = sorted({pid for _, pid in clicks} | {pid for _, pid in bookings}, key=lambda v: (v is None, str(v)))
    hotel_query = {"prop_id": {"$in": prop_ids}} if prop_ids else {"_id": {"$exists": False}}
    hotels: dict[str, dict[str, Any]] = {}
    for doc in db.dim_hotels.find(hotel_query, {"prop_id": 1, "display_country_label": 1, "city": 1, "prop_country_id": 1}):
        hotels[_label_key(doc.get("prop_id"))] = doc

    rows = []
    for day, pid in sorted(clicks.keys() | bookings.keys()):
        hotel = hotels.get(_label_key(pid), {})
        click_bucket = clicks.get((day, pid), {"searches": 0, "clicks": 0})
        booking_bucket = bookings.get((day, pid), {
            "reservations": 0, "revenue_usd": 0.0, "length_sum": 0.0,
            "adults": 0, "children": 0, "rooms": 0,
        })
        res = booking_bucket["reservations"]
        rows.append({
            "date": day,
            "prop_id": int(pid or 0),
            "site_id": 0,
            "visitor_location_country_id": int(hotel.get("prop_country_id") or 0),
            "visitor_country_label": str(hotel.get("display_country_label") or ""),
            "srch_destination_id": int(pid or 0),
            "destination_label": str(hotel.get("city") or ""),
            "searches": click_bucket["searches"],
            "clicks": click_bucket["clicks"],
            "reservations": res,
            "revenue_usd": round(booking_bucket["revenue_usd"], 2),
            "avg_booking_window": 0.0,
            "avg_length_of_stay": round(booking_bucket["length_sum"] / res, 2) if res else 0.0,
            "adults": booking_bucket["adults"],
            "children": booking_bucket["children"],
            "rooms": booking_bucket["rooms"],
        })
    return rows


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
            # El enriquecimiento solo RELLENA labels vacíos: si el extractor ya
            # resolvió un label real (ej. ciudad/país desde dim_hotels), se
            # conserva y nunca se pisa con el catálogo sintético GA03.
            if "prop_id" in row and not row.get("hotel_label"):
                row["hotel_label"] = hotel_labels.get((_label_key(row["prop_id"]),), "")
            if "room_type_id" in row and not row.get("room_type_label"):
                room_labels_by_prop = room_labels.get(
                    (_label_key(row.get("prop_id")), _label_key(row["room_type_id"])),
                    "",
                )
                row["room_type_label"] = room_labels_by_prop or room_labels.get((_label_key(row["room_type_id"]),), "")
            if "rate_plan_id" in row and not row.get("rate_plan_label"):
                row["rate_plan_label"] = rate_labels.get((_label_key(row["rate_plan_id"]),), "")
            if "visitor_location_country_id" in row and not row.get("visitor_country_label"):
                row["visitor_country_label"] = country_labels.get((_label_key(row["visitor_location_country_id"]),), "")
            if "srch_destination_id" in row and not row.get("destination_label"):
                row["destination_label"] = destination_labels.get((_label_key(row["srch_destination_id"]),), "")
            if "site_id" in row and not row.get("site_label"):
                row["site_label"] = site_labels.get((_label_key(row["site_id"]),), "")


def _enrich_strat_hotel_geo(db, payload: dict[str, list[dict[str, Any]]]) -> None:
    """Resuelve ciudad y coordenadas REALES para ``strat_hotel_monthly`` (IE-H02).

    ``city`` sale de ``dim_hotels`` (el mismo hotel real que ya aporta
    ``hotel_label``); ``city_lat``/``city_lng`` salen del catálogo
    ``geo_catalog`` (entradas ``type=city`` con lat/lng reales, casadas por
    nombre). Una ciudad sin entrada en geo_catalog queda con coordenadas
    ``None`` — honesto, nunca coordenadas sintéticas por hash.
    """
    rows = payload.get("strat_hotel_monthly")
    if not rows:
        return
    prop_ids = [r.get("prop_id") for r in rows if r.get("prop_id") is not None]
    hotel_geo: dict[str, dict[str, Any]] = {}
    if prop_ids:
        for doc in db.dim_hotels.find(
            {"prop_id": {"$in": prop_ids}},
            {"prop_id": 1, "city": 1, "latitude": 1, "longitude": 1},
        ):
            pid = _label_key(doc.get("prop_id"))
            if pid:
                hotel_geo[pid] = {
                    "city": str(doc.get("city") or "").strip(),
                    "latitude": doc.get("latitude"),
                    "longitude": doc.get("longitude"),
                }
    geo_by_city: dict[str, tuple[float, float]] = {}
    for doc in db.geo_catalog.find(
        {"type": "city", "latitude": {"$ne": None}, "longitude": {"$ne": None}},
        {"name": 1, "latitude": 1, "longitude": 1},
    ):
        name = str(doc.get("name") or "").strip().lower()
        if name and doc.get("latitude") is not None and doc.get("longitude") is not None:
            geo_by_city[name] = (float(doc["latitude"]), float(doc["longitude"]))
    for row in rows:
        meta = hotel_geo.get(_label_key(row.get("prop_id")), {})
        city = meta.get("city", "")
        row["city"] = city
        # Coordenada del hotel: la REAL por hotel (dim_hotels.latitude/longitude)
        # si existe; si no, la del centro de ciudad (geo_catalog). Nada inventado.
        lat = meta.get("latitude")
        lng = meta.get("longitude")
        if lat is None or lng is None:
            point = geo_by_city.get(city.strip().lower())
            if point:
                lat, lng = point
        row["city_lat"] = lat
        row["city_lng"] = lng


# ── Capa estratégica mensual (TAF14) ────────────────────────────────────


def _hotel_total_rooms(db, prop_ids: list[Any]) -> dict[str, int]:
    """Mapa prop_id → total_rooms (denominador de ocupación/RevPAR).

    Fuentes en orden (solo lectura durante el ETL, nunca desde el dashboard):
    1. ``dim_hotels.total_rooms``
    2. ``dim_hotels.total_rooms_declared`` (aprobación de onboarding)
    3. suma de ``room_inventory_calendar.total_rooms`` por prop (capacidad
       táctica de la casa, la misma que alimenta ``kpi_inventory_daily``)

    0 solo cuando ninguna fuente tiene el dato (ej: catálogo sintético sin
    capacidad declarada).
    """
    result: dict[str, int] = {}
    query: dict[str, Any] = {"prop_id": {"$in": prop_ids}} if prop_ids else {}
    projection = {"prop_id": 1, "total_rooms": 1, "total_rooms_declared": 1}
    for doc in db.dim_hotels.find(query, projection):
        value = 0
        for field in ("total_rooms", "total_rooms_declared"):
            raw = doc.get(field)
            if raw is not None:
                try:
                    value = int(raw)
                except (TypeError, ValueError):
                    continue
                break
        result[_label_key(doc.get("prop_id"))] = value

    missing = [pid for pid in prop_ids if not result.get(_label_key(pid), 0)]
    if missing:
        # El calendario tiene un doc por fecha×tipo; la capacidad es la suma de
        # los tipos de habitación DISTINTOS (max por tipo), no de todas las filas.
        pipeline = [
            {"$match": {"prop_id": {"$in": missing}, "total_rooms": {"$gt": 0}}},
            {"$group": {"_id": {"prop": "$prop_id", "rt": "$room_type_id"}, "cap": {"$max": "$total_rooms"}}},
            {"$group": {"_id": "$_id.prop", "total": {"$sum": "$cap"}}},
        ]
        for doc in db.room_inventory_calendar.aggregate(pipeline, allowDiskUse=True):
            result[_label_key(doc["_id"])] = int(doc.get("total") or 0)

    return result


def _extract_strat_booking_monthly(db, *, by_room_type: bool) -> list[dict[str, Any]]:
    """Agregado mensual de ``booking_orders`` por mes de llegada.

    ``by_room_type`` añade ``room_type_id`` a la clave (tabla de planes). Los
    importes no se prorratean por noche: para la lectura estratégica mensual se
    usa el mes de ``check_in_date`` y ``total_price`` como revenue neto de
    descuento (``discount_amount`` = original_total − total, sin inventar
    comisiones ni costos que Mongo no aporta).
    """
    _id: dict[str, Any] = {
        "month": {"$concat": [{"$substrBytes": ["$check_in_date", 0, 7]}, "-01"]},
        "prop_id": "$prop_id",
        "currency": {"$toUpper": {"$ifNull": ["$currency", ""]}},
    }
    if by_room_type:
        _id["room_type_id"] = {"$ifNull": ["$room_type_id", ""]}
    pipeline = [
        {"$match": {"check_in_date": {"$type": "string"}}},
        {"$set": {
            "_rooms": {"$max": [{"$convert": {"input": "$rooms", "to": "int", "onError": 1, "onNull": 1}}, 1]},
            "_nights": {"$max": [{"$convert": {"input": "$total_nights", "to": "int", "onError": 0, "onNull": 0}}, 0]},
            "_is_cancelled": {"$in": [{"$toLower": {"$ifNull": ["$status", ""]}}, ["cancelled", "canceled", "cancelled_by_guest", "cancelled_by_hotel"]]},
            "_original": {"$ifNull": ["$original_total_price", {"$ifNull": ["$total_price", 0]}]},
        }},
        {"$group": {
            "_id": _id,
            "bookings": {"$sum": 1},
            "rooms_sold": {"$sum": {"$cond": ["$_is_cancelled", 0, "$_rooms"]}},
            "room_nights": {"$sum": {"$cond": ["$_is_cancelled", 0, {"$multiply": ["$_nights", "$_rooms"]}]}},
            "revenue": {"$sum": {"$cond": ["$_is_cancelled", 0, {"$ifNull": ["$total_price", 0]}]}},
            "discount_amount": {"$sum": {"$cond": ["$_is_cancelled", 0, {"$max": [0, {"$subtract": ["$_original", {"$ifNull": ["$total_price", 0]}]}]}]}},
            "adults": {"$sum": {"$cond": ["$_is_cancelled", 0, {"$ifNull": ["$adults", 0]}]}},
            "children": {"$sum": {"$cond": ["$_is_cancelled", 0, {"$ifNull": ["$children", 0]}]}},
            "cancelled_rooms": {"$sum": {"$cond": ["$_is_cancelled", "$_rooms", 0]}},
        }},
        {"$sort": {"_id.month": 1}},
    ]
    docs = list(db.booking_orders.aggregate(pipeline, allowDiskUse=True))
    rows: list[dict[str, Any]] = []
    for item in docs:
        row: dict[str, Any] = {
            "month": item["_id"]["month"], "prop_id": item["_id"]["prop_id"],
            "currency": item["_id"]["currency"],
            "bookings": int(item["bookings"]), "rooms_sold": int(item["rooms_sold"]),
            "room_nights": int(item["room_nights"]), "revenue": float(item["revenue"] or 0),
            "discount_amount": float(item["discount_amount"] or 0),
            "adults": int(item["adults"]), "children": int(item["children"]),
            "cancelled_rooms": int(item["cancelled_rooms"]),
        }
        if by_room_type:
            row["room_type_id"] = item["_id"]["room_type_id"]
        rows.append(row)
    return rows


def extract_strat_hotel_monthly(client, db_name: str) -> list[dict[str, Any]]:
    """Desempeño mensual por hotel (revenue, noches, cancelaciones, total_rooms)."""
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        rows = _extract_strat_booking_monthly(db, by_room_type=False)
        prop_ids = [row["prop_id"] for row in rows if row.get("prop_id") is not None]
        rooms_map = _hotel_total_rooms(db, prop_ids)
        for row in rows:
            row["total_rooms"] = rooms_map.get(_label_key(row.get("prop_id")), 0)
        return rows
    finally:
        if owns:
            mongo.close()


def extract_strat_plan_monthly(client, db_name: str) -> list[dict[str, Any]]:
    """Rentabilidad mensual por tipo de habitación/plan (revenue y descuento)."""
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        return _extract_strat_booking_monthly(mongo[db_name], by_room_type=True)
    finally:
        if owns:
            mongo.close()


def extract_strat_reputation_monthly(client, db_name: str) -> list[dict[str, Any]]:
    """Reputación mensual por hotel (rating aprobado, sentimiento, respuesta)."""
    settings = get_settings()
    mongo, owns = _mongo_client(client, settings)
    try:
        db = mongo[db_name]
        pipeline = [
            {"$match": {"created_at": {"$type": "date"}}},
            {"$set": {
                "_month": {"$dateToString": {"format": "%Y-%m-01", "date": "$created_at"}},
                "_status": {"$toLower": {"$trim": {"input": {"$ifNull": ["$moderation_status", "pending"]}}}},
                "_has_response": {"$and": [
                    {"$ne": [{"$ifNull": ["$staff_response", None]}, None]},
                    {"$ne": [{"$ifNull": ["$staff_response", ""]}, ""]},
                ]},
            }},
            {"$group": {
                "_id": {"month": "$_month", "prop_id": "$prop_id"},
                "reviews": {"$sum": 1},
                "rating_sum": {"$sum": {"$cond": [{"$eq": ["$_status", "approved"]}, {"$ifNull": ["$rating", 0]}, 0]}},
                "approved": {"$sum": {"$cond": [{"$eq": ["$_status", "approved"]}, 1, 0]}},
                "positive": {"$sum": {"$cond": [{"$eq": [{"$toLower": {"$ifNull": ["$sentiment_label", ""]}}, "positive"]}, 1, 0]}},
                "neutral": {"$sum": {"$cond": [{"$eq": [{"$toLower": {"$ifNull": ["$sentiment_label", ""]}}, "neutral"]}, 1, 0]}},
                "negative": {"$sum": {"$cond": [{"$eq": [{"$toLower": {"$ifNull": ["$sentiment_label", ""]}}, "negative"]}, 1, 0]}},
                "responded": {"$sum": {"$cond": ["$_has_response", 1, 0]}},
            }},
            {"$sort": {"_id.month": 1}},
        ]
        rows: list[dict[str, Any]] = []
        for item in db.reviews.aggregate(pipeline, allowDiskUse=True):
            reviews = int(item["reviews"])
            approved = int(item["approved"])
            responded = int(item["responded"])
            rows.append({
                "month": item["_id"]["month"], "prop_id": item["_id"].get("prop_id", 0),
                "reviews": reviews,
                "avg_rating": float(item["rating_sum"] or 0) / approved if approved else 0.0,
                "positive": int(item["positive"]), "neutral": int(item["neutral"]),
                "negative": int(item["negative"]), "responded": responded,
                "response_rate": (responded / reviews * 100.0) if reviews else 0.0,
            })
        return rows
    finally:
        if owns:
            mongo.close()


def rollup_market_monthly(daily_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rueda el embudo diario (``kpi_funnel_daily``) a granularidad mensual.

    Reutiliza la agregación diaria ya calculada (una sola lectura de la Fact
    grande), sin re-agregar ``fact_hotel_reservations`` por segunda vez.
    """
    buckets: dict[tuple[str, int, int], dict[str, Any]] = {}
    for row in daily_rows:
        day = str(row.get("date") or "")
        month = day[:7] + "-01" if len(day) >= 10 else day
        key = (month, int(row.get("visitor_location_country_id") or 0), int(row.get("srch_destination_id") or 0))
        bucket = buckets.setdefault(key, {
            "month": month,
            "visitor_location_country_id": key[1],
            "visitor_country_label": str(row.get("visitor_country_label") or ""),
            "srch_destination_id": key[2],
            "destination_label": str(row.get("destination_label") or ""),
            "searches": 0, "clicks": 0, "reservations": 0, "revenue_usd": 0.0,
        })
        bucket["searches"] += int(row.get("searches") or 0)
        bucket["clicks"] += int(row.get("clicks") or 0)
        bucket["reservations"] += int(row.get("reservations") or 0)
        bucket["revenue_usd"] += float(row.get("revenue_usd") or 0)
    return sorted(buckets.values(), key=lambda item: item["month"])


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
        # Capa estratégica mensual (TAF14): pocos agregados, sin replicar Mongo.
        payload["strat_hotel_monthly"] = extract_strat_hotel_monthly(mongo, db_name)
        payload["strat_plan_monthly"] = extract_strat_plan_monthly(mongo, db_name)
        payload["strat_reputation_monthly"] = extract_strat_reputation_monthly(mongo, db_name)
        # Mercado mensual se deriva del embudo diario ya agregado (sin re-leer
        # la Fact grande una segunda vez).
        payload["strat_market_monthly"] = rollup_market_monthly(payload["kpi_funnel_daily"])
        _enrich_kpi_labels(mongo[db_name], payload)
        _enrich_strat_hotel_geo(mongo[db_name], payload)
        return payload
    finally:
        if owns:
            mongo.close()
