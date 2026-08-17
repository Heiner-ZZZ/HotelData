"""Informes estratégicos TAF14 (Vista A y B) sobre las tablas ``strat_*``.

Siguen el MISMO principio que los informes tácticos compuestos (patrón Z):
cada dashboard devuelve ``summary`` (KPIs en cajas separadas) + ``series``
(gráficos) + ``rows`` (tabla de registros paginada). Los 7 informes dictados
en TAF14: Vista A = IE-H01 (desempeño + rentabilidad por plan) e IE-H02
(posicionamiento, con serie + tabla propias); Vista B = IE-G01 (KPIs
estratégicos), IE-G02 (rankings R-G01..R-G06), IE-G03 (rentabilidad de
cartera), IE-G04 (mercados) e IE-G05 (forecasting — placeholder). El BSC
quedó fuera del alcance por decisión del dueño (patrón Z, KPIs en cajas
separadas).

Lee SOLO ClickHouse (granularidad mensual) y nunca replica Mongo en tiempo de
consulta. Contrato: ``available: false`` + ``message`` cuando ClickHouse no
responde (nunca un 500), rangos ``date_from``/``date_to`` (ambos límites) con
``days`` como fallback, y paginación en las tablas de registros.
"""

from __future__ import annotations

import calendar
import math
from datetime import UTC, date, datetime, timedelta
from typing import Any

from config.settings import get_settings

# Contrato de columnas por tabla (KEEP IN SYNC con transform.TABLE_COLUMNS).
HOTEL_COLUMNS = (
    "month, prop_id, hotel_label, currency, bookings, rooms_sold, room_nights, "
    "revenue, discount_amount, adults, children, cancelled_rooms, total_rooms"
)
PLAN_COLUMNS = (
    "month, prop_id, hotel_label, room_type_id, room_type_label, currency, "
    "bookings, rooms_sold, room_nights, revenue, discount_amount, adults, "
    "children, cancelled_rooms"
)
MARKET_COLUMNS = (
    "month, visitor_location_country_id, visitor_country_label, "
    "srch_destination_id, destination_label, searches, clicks, reservations, "
    "revenue_usd"
)
REPUTATION_COLUMNS = (
    "month, prop_id, hotel_label, reviews, avg_rating, positive, neutral, "
    "negative, responded, response_rate"
)

# ─── Helpers numéricos / rango ───────────────────────────────────────────


def _round2(value: float) -> float:
    return round(float(value or 0), 2)


def _row_to_dict(names: list[str], row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        name: (value.isoformat() if hasattr(value, "isoformat") else value)
        for name, value in zip(names, row)
    }


def _validate_range(
    date_from: str | None,
    date_to: str | None,
    days: int,
) -> tuple[date, date]:
    """Resuelve el rango: date_from/date_to explícitos o últimos ``days`` días."""
    end = datetime.now(UTC).date()
    fallback_from = end - timedelta(days=days - 1)
    start = date.fromisoformat(date_from) if date_from else fallback_from
    end = date.fromisoformat(date_to) if date_to else end
    if end < start:
        raise ValueError("date_to debe ser igual o posterior a date_from")
    return start, end


def _prev_window(start: date, end: date) -> tuple[date, date]:
    """Ventana anterior de la misma longitud, inmediatamente previa al rango."""
    length = end - start
    return start - length - timedelta(days=1), start - timedelta(days=1)


def _month_days(month: Any) -> int:
    """Días del mes para una fecha 'AAAA-MM-DD' (primer día del mes)."""
    text = str(month or "")[:10]
    try:
        d = date.fromisoformat(text)
    except ValueError:
        return 30
    return calendar.monthrange(d.year, d.month)[1]


def _pct_change(cur: float, prev: float) -> float:
    if not prev:
        return 0.0
    return round((cur - prev) / abs(prev) * 100, 2)


def _paginate(items: list[dict[str, Any]], page: int, page_size: int) -> dict[str, Any]:
    total = len(items)
    return {
        "rows": items[(page - 1) * page_size : page * page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


# ─── Lectura ClickHouse (solo lectura) ────────────────────────────────────


def _query_monthly(
    client: Any,
    table: str,
    columns: str,
    order_by: str,
    start: date,
    end: date,
    prop_id: int | None = None,
) -> list[dict[str, Any]]:
    where = ["month >= {start:Date}", "month <= {end:Date}"]
    params: dict[str, Any] = {"start": start, "end": end}
    if prop_id is not None:
        where.append("prop_id = {prop_id:UInt32}")
        params["prop_id"] = prop_id
    query = (
        f"SELECT {columns} FROM {table} FINAL WHERE "
        + " AND ".join(where)
        + f" ORDER BY {order_by}"
    )
    result = client.query(query, parameters=params)
    names = [name.strip() for name in columns.split(",")]
    return [_row_to_dict(names, row) for row in result.result_rows]


def _query_prev(
    client: Any,
    table: str,
    columns: str,
    order_by: str,
    start: date,
    end: date,
    prop_id: int | None = None,
) -> list[dict[str, Any]]:
    prev_start, prev_end = _prev_window(start, end)
    return _query_monthly(
        client, table, columns, order_by, prev_start, prev_end, prop_id=prop_id
    )


def _client() -> Any:
    import clickhouse_connect  # type: ignore

    settings = get_settings()
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )


# ─── KPIs (patrón compuesto) ──────────────────────────────────────────────

_TARGETS = {
    "revenue": 0.05,      # crecer 5% vs período anterior
    "adr": 0.0,           # mantener ADR
    "revpar": 0.03,       # crecer RevPAR 3%
    "ocupacion": 0.65,    # piso 65%
    "rating": 4.2,        # piso 4.2
    "respuesta": 0.8,     # piso 80% de respuesta a reseñas
    "cancelacion": 0.05,  # techo 5%
    "descuento": 0.15,    # techo 15%
    "bookings": 0.03,     # crecer 3%
    "room_nights": 0.0,   # mantener noches
    "revenue_growth": 0.0,  # no caer
}


def _trend(value: float, good_direction: str = "up") -> str:
    """Dirección del indicador según si subir es bueno o malo."""
    if value > 0.5:
        return "up" if good_direction == "up" else "down"
    if value < -0.5:
        return "down" if good_direction == "up" else "up"
    return "flat"


def _semaforo(cur: float, prev: float, *, lower_is_better: bool = False) -> str:
    if prev == 0:
        return "green" if cur else "yellow"
    if lower_is_better:
        return "green" if cur <= prev else ("yellow" if cur <= prev * 1.5 else "red")
    return "green" if cur >= prev else ("yellow" if cur >= prev * 0.9 else "red")


def _kpi(kid: str, label: str, value: float, unit: str, prev: float,
         good_direction: str = "up", target: float | None = None,
         lower_is_better: bool = False, detail: str = "") -> dict[str, Any]:
    """KPI con meta, variación vs período anterior, tendencia y semáforo."""
    variation = _pct_change(value, prev)
    t = target if target is not None else (prev * (1 + _TARGETS.get(kid, 0)) if prev else 0.0)
    if lower_is_better:
        ok = value <= t
        warn = t < value <= t * 1.5
    else:
        ok = value >= t
        warn = t * 0.9 <= value < t
    return {
        "id": kid,
        "label": label,
        "value": _round2(value),
        "unit": unit,
        "target": _round2(t) if t else None,
        "pct_change": variation,
        "trend": _trend(variation, good_direction),
        "semaforo": "green" if ok else ("yellow" if warn else "red"),
        "detail": detail,
    }


def _weighted_rating(rep_rows: list[dict[str, Any]]) -> tuple[float, float]:
    """Rating y tasa de respuesta ponderados por volumen de reseñas."""
    total = sum(int(r.get("reviews") or 0) for r in rep_rows)
    if not total:
        return 0.0, 0.0
    rating = (
        sum(float(r.get("avg_rating") or 0) * int(r.get("reviews") or 0) for r in rep_rows)
        / total
    )
    response = (
        sum(float(r.get("response_rate") or 0) * int(r.get("reviews") or 0) for r in rep_rows)
        / total
    )
    return rating, response


def _derive_financials(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Totales y derivados (ADR/ocupación/RevPAR/cancelación/descuento) de las
    filas de ``strat_hotel_monthly`` — la matemática de los KPIs."""
    revenue = sum(float(r.get("revenue") or 0) for r in rows)
    room_nights = sum(int(r.get("room_nights") or 0) for r in rows)
    capacity = sum(int(r.get("total_rooms") or 0) * _month_days(r.get("month")) for r in rows)
    bookings = sum(int(r.get("bookings") or 0) for r in rows)
    cancelled = sum(int(r.get("cancelled_rooms") or 0) for r in rows)
    rooms_sold = sum(int(r.get("rooms_sold") or 0) for r in rows)
    discount = sum(float(r.get("discount_amount") or 0) for r in rows)
    revenue_bruto = revenue + discount
    return {
        "revenue": revenue,
        "room_nights": room_nights,
        "capacity": capacity,
        "bookings": bookings,
        "cancelled": cancelled,
        "rooms_sold": rooms_sold,
        "discount": discount,
        "revenue_bruto": revenue_bruto,
        "adr": revenue / room_nights if room_nights else 0.0,
        "ocupacion": room_nights / capacity * 100 if capacity else 0.0,
        "revpar": revenue / capacity if capacity else 0.0,
        "cancelacion": cancelled / rooms_sold * 100 if rooms_sold else 0.0,
        "descuento_pct": discount / revenue_bruto * 100 if revenue_bruto else 0.0,
    }


def _financial_kpis(cur: dict[str, float], prev: dict[str, float],
                    rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """KPIs económicos-comerciales (con variación vs período anterior)."""
    growth = _pct_change(cur["revenue"], prev["revenue"])
    return [
        _kpi("revenue", "Revenue neto", cur["revenue"], "USD", prev["revenue"],
             detail=f"{cur['bookings']} reservas en el período"),
        _kpi("adr", "ADR", cur["adr"], "USD", prev["adr"], detail="Tarifa media por noche"),
        _kpi("revpar", "RevPAR", cur["revpar"], "USD", prev["revpar"], detail="Ingreso por habitación disponible"),
        _kpi("ocupacion", "Ocupación", cur["ocupacion"], "%", prev["ocupacion"],
             target=_TARGETS["ocupacion"] * 100, detail="Noches / capacidad del mes"),
        _kpi("cancelacion", "Cancelaciones", cur["cancelacion"], "%", 0.0,
             good_direction="down", target=_TARGETS["cancelacion"] * 100,
             lower_is_better=True, detail="Habitaciones canceladas / vendidas"),
        _kpi("descuento", "Descuento aplicado", cur["descuento_pct"], "%", 0.0,
             good_direction="down", target=_TARGETS["descuento"] * 100,
             lower_is_better=True, detail="Descuento / revenue bruto"),
        _kpi("bookings", "Reservas", float(cur["bookings"]), "unid.", float(prev["bookings"]),
             detail="Reservas confirmadas"),
        _kpi("room_nights", "Noches ocupadas", float(cur["room_nights"]), "noches", float(prev["room_nights"]),
             detail="Noches estancia"),
        _kpi("revenue_growth", "Crecimiento de revenue", growth, "%", 0.0,
             target=0.0, detail="vs período anterior"),
    ]


def _reputation_kpis(rep_rows: list[dict[str, Any]],
                     prev_rep_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """KPIs de reputación (rating y respuesta ponderados por reseñas).

    ``response_rate`` ya viene de ``strat_reputation_monthly`` como PORCENTAJE
    (0-100): el ETL lo calcula con ``responded / reviews * 100.0`` (extract.py).
    Se expone tal cual — multiplicarlo por 100 otra vez duplicaba la conversión
    y mostraba 3,333% en dev cuando la tasa real era 33,33%.
    """
    rating, response = _weighted_rating(rep_rows)
    prev_rating, prev_response = _weighted_rating(prev_rep_rows)
    return [
        _kpi("rating", "Rating promedio", rating, "estrellas", prev_rating,
             target=_TARGETS["rating"], detail="Reseñas aprobadas"),
        _kpi("respuesta", "Respuesta a reseñas", response, "%", prev_response,
             target=_TARGETS["respuesta"] * 100, detail="Reseñas respondidas"),
    ]


def _build_hotel_kpis(
    rows: list[dict[str, Any]],
    prev_rows: list[dict[str, Any]],
    rep_rows: list[dict[str, Any]],
    prev_rep_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """KPIs de UN hotel (o de toda la cartera): financieros + reputación."""
    cur = _derive_financials(rows)
    prev = _derive_financials(prev_rows)
    return _financial_kpis(cur, prev, rows) + _reputation_kpis(rep_rows, prev_rep_rows)


# ─── Vista A — hotel individual (IE-H01 / IE-H02) ────────────────────────


def _build_hotel_posicionamiento(
    rep_rows: list[dict[str, Any]],
    prev_rep_rows: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    prev_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """IE-H02 (posicionamiento) con datos PROPIOS del hotel: rating × precio.
    No consulta la tabla de mercado (no tiene prop_id) para no filtrar
    demanda de otros hoteles a un dueño."""
    rating, _ = _weighted_rating(rep_rows)
    prev_rating, _ = _weighted_rating(prev_rep_rows)
    cur = _derive_financials(rows)
    prev = _derive_financials(prev_rows)
    adr = cur["adr"]
    prev_adr = prev["adr"]

    if rating >= 4.2 and adr > 0:
        diagnosis = "Reputación sólida que respalda el precio actual."
        decision = "Sostener tarifa; probar subidas puntuales en alta demanda."
    elif rating >= 4.2 and adr == 0:
        diagnosis = "Buena reputación pero sin revenue en el período."
        decision = "Verificar disponibilidad y canales activos."
    elif rating < 4.2 and adr > 0:
        diagnosis = "El precio no está respaldado por la reputación."
        decision = "Invertir en calidad/respuesta a reseñas antes de subir tarifa."
    else:
        diagnosis = "Sin señal clara de posicionamiento en el período."
        decision = "Recuperar demanda y construir reputación antes de reposicionar."

    return {
        "rating": _round2(rating),
        "adr": _round2(adr),
        "rating_variacion": _pct_change(rating, prev_rating),
        "adr_variacion": _pct_change(adr, prev_adr),
        "diagnosis": diagnosis,
        "decision": decision,
    }


def _build_hotel_serie(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Serie mensual del hotel: revenue neto y ocupación."""
    monthly: dict[str, dict[str, float]] = {}
    for r in rows:
        month = r.get("month") or ""
        bucket = monthly.setdefault(month, {"revenue": 0.0, "room_nights": 0.0, "capacity": 0.0})
        bucket["revenue"] += float(r.get("revenue") or 0)
        bucket["room_nights"] += int(r.get("room_nights") or 0)
        bucket["capacity"] += int(r.get("total_rooms") or 0) * _month_days(month)
    labels = sorted(monthly)
    return {
        "labels": labels,
        "datasets": [
            {"label": "Revenue neto (USD)", "data": [_round2(monthly[m]["revenue"]) for m in labels]},
            {"label": "Ocupación (%)", "data": [
                _round2(monthly[m]["room_nights"] / monthly[m]["capacity"] * 100) if monthly[m]["capacity"] else 0
                for m in labels
            ]},
        ],
    }


def _build_hotel_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tabla de registros del hotel: una fila por mes (bruto/neto/descuento,
    ADR, ocupación, RevPAR, cancelación). Más reciente primero."""
    monthly: dict[str, dict[str, float]] = {}
    for r in rows:
        month = r.get("month") or ""
        bucket = monthly.setdefault(month, {
            "bookings": 0.0, "room_nights": 0.0, "revenue": 0.0,
            "discount": 0.0, "cancelled": 0.0, "rooms_sold": 0.0, "capacity": 0.0,
        })
        bucket["bookings"] += int(r.get("bookings") or 0)
        bucket["room_nights"] += int(r.get("room_nights") or 0)
        bucket["revenue"] += float(r.get("revenue") or 0)
        bucket["discount"] += float(r.get("discount_amount") or 0)
        bucket["cancelled"] += int(r.get("cancelled_rooms") or 0)
        bucket["rooms_sold"] += int(r.get("rooms_sold") or 0)
        bucket["capacity"] += int(r.get("total_rooms") or 0) * _month_days(month)

    items = []
    for month in sorted(monthly, reverse=True):
        b = monthly[month]
        bruto = b["revenue"] + b["discount"]
        items.append({
            "month": month,
            "bookings": int(b["bookings"]),
            "room_nights": int(b["room_nights"]),
            "revenue_bruto": _round2(bruto),
            "revenue_neto": _round2(b["revenue"]),
            "descuento": _round2(b["discount"]),
            "adr": _round2(b["revenue"] / b["room_nights"]) if b["room_nights"] else 0.0,
            "ocupacion_pct": _round2(b["room_nights"] / b["capacity"] * 100) if b["capacity"] else 0.0,
            "revpar": _round2(b["revenue"] / b["capacity"]) if b["capacity"] else 0.0,
            "cancelacion_pct": _round2(b["cancelled"] / b["rooms_sold"] * 100) if b["rooms_sold"] else 0.0,
        })
    return items


def _build_planes(
    plan_rows: list[dict[str, Any]],
    page: int,
    page_size: int,
) -> dict[str, Any]:
    plans: dict[str, dict[str, Any]] = {}
    for r in plan_rows:
        label = r.get("room_type_label") or r.get("room_type_id") or "Sin tipo"
        p = plans.setdefault(label, {
            "label": label, "bookings": 0, "room_nights": 0,
            "revenue_bruto": 0.0, "revenue_neto": 0.0, "descuento": 0.0,
        })
        p["bookings"] += int(r.get("bookings") or 0)
        p["room_nights"] += int(r.get("room_nights") or 0)
        p["revenue_neto"] += float(r.get("revenue") or 0)
        p["descuento"] += float(r.get("discount_amount") or 0)
    for p in plans.values():
        p["revenue_bruto"] = _round2(p["revenue_neto"] + p["descuento"])
        p["descuento_pct"] = _round2(p["descuento"] / p["revenue_bruto"] * 100) if p["revenue_bruto"] else 0.0
        p["adr"] = _round2(p["revenue_neto"] / p["room_nights"]) if p["room_nights"] else 0.0
        p["revenue_neto"] = _round2(p["revenue_neto"])
        p["descuento"] = _round2(p["descuento"])
    items = sorted(plans.values(), key=lambda p: -p["revenue_neto"])
    return _paginate(items, page, page_size)


# ─── IE-G02 — Rankings estratégicos (R-G01..R-G06) ────────────────────────


def _ranking_entry(entidad: str, valor: float, unidad: str, variacion: float,
                   motivo: str, decision: str) -> dict[str, Any]:
    return {
        "entidad": entidad,
        "valor": _round2(valor),
        "unidad": unidad,
        "variacion": _round2(variacion),
        "motivo": motivo,
        "decision": decision,
    }


def _build_rankings(
    rows: list[dict[str, Any]],
    prev_rows: list[dict[str, Any]],
    plan_rows: list[dict[str, Any]],
    rep_rows: list[dict[str, Any]],
    prev_rep_rows: list[dict[str, Any]],
    market_rows: list[dict[str, Any]],
    prev_market_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """IE-G02 — rankings estratégicos R-G01..R-G06 (TAF14 §5).

    Cada ranking explica el criterio, el período, la variación y termina en
    una decisión sugerida. Devuelve ``kpis`` (una caja por ranking), ``series``
    (top hoteles por revenue para el gráfico) y ``groups`` (las 6 tablas de
    registros con motivo + decisión).
    """
    hotels = _by_hotel(rows)
    prev_hotels = _by_hotel(prev_rows)

    def _hotel_growth(pid: int) -> float:
        prev = prev_hotels.get(pid, {})
        return _pct_change(hotels[pid]["revenue"], prev.get("revenue", 0))

    # R-G01 — Hoteles líderes: mayor revenue neto del período
    rg01 = [
        _ranking_entry(
            h["hotel_label"], h["revenue"], "USD", _hotel_growth(h["prop_id"]),
            motivo="Mayor revenue neto del período",
            decision="Replicar prácticas y proteger fortalezas",
        )
        for h in sorted(hotels.values(), key=lambda x: -x["revenue"])[:5]
    ]

    # R-G02 — Hoteles con mayor oportunidad: mayor crecimiento vs período anterior
    rg02 = [
        _ranking_entry(
            h["hotel_label"], h["revenue"], "USD", _hotel_growth(h["prop_id"]),
            motivo="Mayor crecimiento de revenue vs período anterior",
            decision="Priorizar acompañamiento e inversión",
        )
        for h in sorted(hotels.values(), key=lambda x: -_hotel_growth(x["prop_id"]))[:5]
    ]

    # R-G03 — Hoteles con riesgo estratégico: mayor caída de revenue
    rg03 = [
        _ranking_entry(
            h["hotel_label"], h["revenue"], "USD", _hotel_growth(h["prop_id"]),
            motivo="Deterioro persistente o pérdida de revenue",
            decision="Activar un plan de corrección",
        )
        for h in sorted(hotels.values(), key=lambda x: _hotel_growth(x["prop_id"]))[:5]
    ]

    # R-G04 — Mercados y destinos con mayor oportunidad (demanda agregada)
    market_totals: dict[str, float] = {}
    for r in market_rows:
        label = r.get("destination_label") or str(r.get("srch_destination_id") or "Mercado")
        market_totals[label] = market_totals.get(label, 0.0) + float(r.get("revenue_usd") or 0)
    prev_market_totals: dict[str, float] = {}
    for r in prev_market_rows:
        label = r.get("destination_label") or str(r.get("srch_destination_id") or "Mercado")
        prev_market_totals[label] = prev_market_totals.get(label, 0.0) + float(r.get("revenue_usd") or 0)
    rg04 = [
        _ranking_entry(
            label, revenue, "USD", _pct_change(revenue, prev_market_totals.get(label, 0)),
            motivo="Demanda, crecimiento y atractivo del destino",
            decision="Decidir expansión y posicionamiento",
        )
        for label, revenue in sorted(market_totals.items(), key=lambda kv: -kv[1])[:5]
    ]

    # R-G05 — Planes hoteleros con mayor contribución (revenue neto agregado)
    plan_totals: dict[str, dict[str, float]] = {}
    for r in plan_rows:
        label = r.get("room_type_label") or r.get("room_type_id") or "Sin tipo"
        p = plan_totals.setdefault(label, {"revenue": 0.0, "bookings": 0})
        p["revenue"] += float(r.get("revenue") or 0)
        p["bookings"] += int(r.get("bookings") or 0)
    rg05 = [
        _ranking_entry(
            label, p["revenue"], "USD", 0.0,
            motivo=f"Mayor contribución de revenue neto ({int(p['bookings'])} reservas)",
            decision="Mantener, rediseñar o retirar planes",
        )
        for label, p in sorted(plan_totals.items(), key=lambda kv: -kv[1]["revenue"])[:5]
    ]

    # R-G06 — Hoteles referentes en reputación (rating ponderado por reseñas)
    rep_total: dict[int, dict[str, float]] = {}
    for r in rep_rows:
        pid = int(r.get("prop_id") or 0)
        bucket = rep_total.setdefault(pid, {"reviews": 0, "rating_sum": 0.0})
        bucket["reviews"] += int(r.get("reviews") or 0)
        bucket["rating_sum"] += float(r.get("avg_rating") or 0) * int(r.get("reviews") or 0)
    prev_rating: dict[int, float] = {}
    for r in prev_rep_rows:
        pid = int(r.get("prop_id") or 0)
        rev = int(r.get("reviews") or 0)
        prev_rating[pid] = (float(r.get("avg_rating") or 0) * rev) / rev if rev else 0.0
    ranked_reps = sorted(
        ((pid, b) for pid, b in rep_total.items() if b["reviews"] > 0),
        key=lambda kv: kv[1]["rating_sum"] / kv[1]["reviews"],
        reverse=True,
    )[:5]
    rg06 = [
        _ranking_entry(
            hotels.get(pid, {}).get("hotel_label", f"Hotel #{pid}"),
            bucket["rating_sum"] / bucket["reviews"],
            "estrellas",
            _pct_change(bucket["rating_sum"] / bucket["reviews"], prev_rating.get(pid, 0)),
            motivo="Nivel, evolución y consistencia de la percepción del huésped",
            decision="Replicar prácticas de marca y servicio",
        )
        for pid, bucket in ranked_reps
    ]

    groups = [
        {"codigo": "R-G01", "titulo": "Hoteles líderes de la cartera", "criterio": "Revenue neto del período", "rows": rg01},
        {"codigo": "R-G02", "titulo": "Hoteles con mayor oportunidad", "criterio": "Crecimiento de revenue vs período anterior", "rows": rg02},
        {"codigo": "R-G03", "titulo": "Hoteles con riesgo estratégico", "criterio": "Deterioro o pérdida de revenue", "rows": rg03},
        {"codigo": "R-G04", "titulo": "Mercados y destinos con oportunidad", "criterio": "Demanda y crecimiento del destino", "rows": rg04},
        {"codigo": "R-G05", "titulo": "Planes con mayor contribución", "criterio": "Revenue neto por tipo de habitación", "rows": rg05},
        {"codigo": "R-G06", "titulo": "Hoteles referentes en reputación", "criterio": "Rating ponderado por reseñas", "rows": rg06},
    ]

    kpis = [
        {
            "id": f"ranking_{g['codigo'].lower().replace('-', '_')}",
            "label": g["codigo"],
            "value": float(len(g["rows"])),
            "unit": "pos.",
            "target": None,
            "pct_change": 0.0,
            "trend": "flat",
            "semaforo": "green" if g["codigo"] in ("R-G01", "R-G06") else ("yellow" if g["codigo"] in ("R-G02", "R-G04") else "red"),
            "detail": g["titulo"],
        }
        for g in groups
    ]

    series = {
        "labels": [e["entidad"] for e in rg01],
        "datasets": [
            {"label": "Revenue neto (USD)", "data": [e["valor"] for e in rg01]},
        ],
    }

    return {"kpis": kpis, "series": series, "groups": groups}


# ─── IE-H02 — Posicionamiento (patrón Z) ──────────────────────────────────


def _build_posicionamiento_serie(
    rep_rows: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Serie mensual de posicionamiento: rating (reputación) + ADR (precio)."""
    rating_by_month: dict[str, list[tuple[float, int]]] = {}
    for r in rep_rows:
        month = r.get("month") or ""
        rating_by_month.setdefault(month, []).append(
            (float(r.get("avg_rating") or 0), int(r.get("reviews") or 0))
        )
    adr_by_month: dict[str, list[float]] = {}
    for r in rows:
        month = r.get("month") or ""
        rn = int(r.get("room_nights") or 0)
        if rn:
            adr_by_month.setdefault(month, []).append(float(r.get("revenue") or 0) / rn)
    labels = sorted(set(rating_by_month) | set(adr_by_month))
    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Rating",
                "data": [
                    _round2(sum(v * n for v, n in rating_by_month.get(m, [])) / sum(n for _, n in rating_by_month.get(m, [])))
                    if rating_by_month.get(m) else 0.0
                    for m in labels
                ],
            },
            {
                "label": "ADR (USD)",
                "data": [
                    _round2(sum(adr_by_month.get(m, [])) / len(adr_by_month.get(m, [])))
                    if adr_by_month.get(m) else 0.0
                    for m in labels
                ],
            },
        ],
    }


def _build_posicionamiento_rows(
    rep_rows: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Tabla de registros del posicionamiento: una fila por mes con rating,
    ADR y tasa de respuesta (misma granularidad que la serie)."""
    by_month: dict[str, dict[str, Any]] = {}
    for r in rep_rows:
        month = r.get("month") or ""
        bucket = by_month.setdefault(month, {"rating_n": 0, "rating_sum": 0.0, "respuesta_sum": 0.0, "respuesta_n": 0, "adr_sum": 0.0, "adr_n": 0})
        rev = int(r.get("reviews") or 0)
        bucket["rating_n"] += rev
        bucket["rating_sum"] += float(r.get("avg_rating") or 0) * rev
        bucket["respuesta_sum"] += float(r.get("response_rate") or 0) * rev
        bucket["respuesta_n"] += rev
    for r in rows:
        month = r.get("month") or ""
        bucket = by_month.setdefault(month, {"rating_n": 0, "rating_sum": 0.0, "respuesta_sum": 0.0, "respuesta_n": 0, "adr_sum": 0.0, "adr_n": 0})
        rn = int(r.get("room_nights") or 0)
        if rn:
            bucket["adr_sum"] += float(r.get("revenue") or 0) / rn
            bucket["adr_n"] += 1
    items = []
    for month in sorted(by_month, reverse=True):
        b = by_month[month]
        items.append({
            "month": month,
            "rating": _round2(b["rating_sum"] / b["rating_n"]) if b["rating_n"] else 0.0,
            "adr": _round2(b["adr_sum"] / b["adr_n"]) if b["adr_n"] else 0.0,
            "respuesta": _round2(b["respuesta_sum"] / b["respuesta_n"]) if b["respuesta_n"] else 0.0,
        })
    return items


# ─── Vista B — cartera (IE-G03) ───────────────────────────────────────────


def _by_hotel(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    hotels: dict[int, dict[str, Any]] = {}
    for r in rows:
        pid = int(r.get("prop_id") or 0)
        h = hotels.setdefault(pid, {
            "prop_id": pid,
            "hotel_label": r.get("hotel_label") or f"Hotel #{pid}",
            "revenue": 0.0, "revenue_bruto": 0.0, "discount": 0.0,
            "room_nights": 0, "bookings": 0,
            "rooms_sold": 0, "cancelled_rooms": 0, "capacity": 0,
        })
        h["revenue"] += float(r.get("revenue") or 0)
        h["revenue_bruto"] += float(r.get("revenue") or 0) + float(r.get("discount_amount") or 0)
        h["discount"] += float(r.get("discount_amount") or 0)
        h["room_nights"] += int(r.get("room_nights") or 0)
        h["bookings"] += int(r.get("bookings") or 0)
        h["rooms_sold"] += int(r.get("rooms_sold") or 0)
        h["cancelled_rooms"] += int(r.get("cancelled_rooms") or 0)
        h["capacity"] += int(r.get("total_rooms") or 0) * _month_days(r.get("month"))
    return hotels


def _build_cartera_summary(
    rows: list[dict[str, Any]],
    prev_rows: list[dict[str, Any]],
    rep_rows: list[dict[str, Any]],
    prev_rep_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resumen compuesto de la cartera: KPIs agregados + nº de hoteles."""
    kpis = _build_hotel_kpis(rows, prev_rows, rep_rows, prev_rep_rows)
    hoteles = len({int(r.get("prop_id") or 0) for r in rows if r.get("prop_id") is not None})
    return {"kpis": kpis, "hoteles": hoteles}


def _build_cartera_rows(
    rows: list[dict[str, Any]],
    prev_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Tabla de registros de la cartera: una fila por hotel (bruto/neto/
    descuento, ADR, ocupación, RevPAR, variación). Ordenada por revenue neto."""
    hotels = _by_hotel(rows)
    prev_hotels = _by_hotel(prev_rows)

    items = []
    for pid, h in hotels.items():
        prev = prev_hotels.get(pid, {})
        adr = h["revenue"] / h["room_nights"] if h["room_nights"] else 0.0
        ocupacion = h["room_nights"] / h["capacity"] * 100 if h["capacity"] else 0.0
        revpar = h["revenue"] / h["capacity"] if h["capacity"] else 0.0
        items.append({
            "prop_id": pid,
            "hotel_label": h["hotel_label"],
            "bookings": h["bookings"],
            "room_nights": h["room_nights"],
            "revenue_bruto": _round2(h["revenue_bruto"]),
            "revenue_neto": _round2(h["revenue"]),
            "descuento": _round2(h["discount"]),
            "descuento_pct": _round2(h["discount"] / h["revenue_bruto"] * 100) if h["revenue_bruto"] else 0.0,
            "adr": _round2(adr),
            "ocupacion_pct": _round2(ocupacion),
            "revpar": _round2(revpar),
            "variacion": _pct_change(h["revenue"], prev.get("revenue", 0)),
        })
    items.sort(key=lambda i: -i["revenue_neto"])
    return items


def _build_cartera_series(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Serie mensual de la cartera: revenue neto y ocupación agregados."""
    monthly: dict[str, dict[str, float]] = {}
    for r in rows:
        month = r.get("month") or ""
        bucket = monthly.setdefault(month, {"revenue": 0.0, "room_nights": 0.0, "capacity": 0.0})
        bucket["revenue"] += float(r.get("revenue") or 0)
        bucket["room_nights"] += int(r.get("room_nights") or 0)
        bucket["capacity"] += int(r.get("total_rooms") or 0) * _month_days(month)
    labels = sorted(monthly)
    return {
        "labels": labels,
        "datasets": [
            {"label": "Revenue neto (USD)", "data": [_round2(monthly[m]["revenue"]) for m in labels]},
            {"label": "Ocupación (%)", "data": [
                _round2(monthly[m]["room_nights"] / monthly[m]["capacity"] * 100) if monthly[m]["capacity"] else 0
                for m in labels
            ]},
        ],
    }


# ─── Mercados (IE-G04) ────────────────────────────────────────────────────


def _build_markets(
    rows: list[dict[str, Any]],
    prev_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Mercados compuesto: KPIs de demanda + serie mensual + tabla por destino
    con cuadrante crecimiento × posición."""
    def _aggregate(src: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for r in src:
            label = r.get("destination_label") or str(r.get("srch_destination_id") or "Mercado")
            m = out.setdefault(label, {
                "destination": label, "searches": 0, "clicks": 0,
                "reservations": 0, "revenue": 0.0,
            })
            m["searches"] += int(r.get("searches") or 0)
            m["clicks"] += int(r.get("clicks") or 0)
            m["reservations"] += int(r.get("reservations") or 0)
            m["revenue"] += float(r.get("revenue_usd") or 0)
        return out

    current = _aggregate(rows)
    previous = _aggregate(prev_rows)
    total_revenue = sum(m["revenue"] for m in current.values()) or 1.0
    total_searches = sum(m["searches"] for m in current.values())
    total_clicks = sum(m["clicks"] for m in current.values())
    total_reservations = sum(m["reservations"] for m in current.values())
    prev_revenue = sum(m["revenue"] for m in previous.values())
    prev_searches = sum(m["searches"] for m in previous.values())
    prev_reservations = sum(m["reservations"] for m in previous.values())
    conversion = total_reservations / total_searches * 100 if total_searches else 0.0
    prev_conversion = prev_reservations / prev_searches * 100 if prev_searches else 0.0

    summary = {
        "kpis": [
            _kpi("searches", "Búsquedas", float(total_searches), "unid.", float(prev_searches),
                 detail="Búsquedas de la demanda"),
            _kpi("clicks", "Clics", float(total_clicks), "unid.", 0.0,
                 detail="Clics sobre resultados"),
            _kpi("reservations", "Reservas", float(total_reservations), "unid.", float(prev_reservations),
                 detail="Reservas confirmadas"),
            _kpi("revenue", "Revenue de mercado", total_revenue, "USD", prev_revenue,
                 detail="Revenue de la demanda"),
            _kpi("conversion", "Conversión", conversion, "%", prev_conversion,
                 detail="Reservas / búsquedas"),
        ]
    }

    matrix = []
    for label, m in current.items():
        prev = previous.get(label, {})
        growth = _pct_change(m["revenue"], prev.get("revenue", 0))
        position = m["revenue"] / total_revenue * 100
        conv = m["reservations"] / m["searches"] * 100 if m["searches"] else 0.0
        if growth >= 0 and position >= 10:
            quadrant, decision = "estrella", "Invertir: destino con posición y tracción"
        elif growth >= 0 and position < 10:
            quadrant, decision = "oportunidad", "Explorar: crece pero tiene poca posición"
        elif growth < 0 and position >= 10:
            quadrant, decision = "consolidacion", "Sostener: fuerte pero pierde tracción"
        else:
            quadrant, decision = "riesgo", "Revisar: cae y tiene posición marginal"
        matrix.append({
            "destination": label,
            "searches": m["searches"],
            "clicks": m["clicks"],
            "reservations": m["reservations"],
            "revenue": _round2(m["revenue"]),
            "conversion_pct": _round2(conv),
            "growth_pct": growth,
            "position_pct": _round2(position),
            "quadrant": quadrant,
            "decision": decision,
        })
    matrix.sort(key=lambda m: -m["revenue"])

    monthly: dict[str, dict[str, float]] = {}
    for r in rows:
        month = r.get("month") or ""
        bucket = monthly.setdefault(month, {"revenue": 0.0, "reservations": 0.0})
        bucket["revenue"] += float(r.get("revenue_usd") or 0)
        bucket["reservations"] += int(r.get("reservations") or 0)
    labels = sorted(monthly)
    series = {
        "labels": labels,
        "datasets": [
            {"label": "Revenue (USD)", "data": [_round2(monthly[m]["revenue"]) for m in labels]},
            {"label": "Reservas", "data": [int(monthly[m]["reservations"]) for m in labels]},
        ],
    }

    return {"summary": summary, "series": series, "rows": matrix}


# ─── Dashboards (orquestación) ────────────────────────────────────────────


def _unavailable(
    exc: Exception,
    start: date,
    end: date,
    prop_id: int | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    return {
        "available": False,
        "source": "clickhouse",
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "prop_id": prop_id,
        "message": str(exc),
        "summary": {"kpis": [], "hoteles": 0, "posicionamiento": None},
        "series": {"labels": [], "datasets": []},
        "serie": {"labels": [], "datasets": []},
        "posicionamiento_serie": {"labels": [], "datasets": []},
        "posicionamiento_rows": [],
        "rankings": {"kpis": [], "series": {"labels": [], "datasets": []}, "groups": []},
        "rows": [],
        "planes": _paginate([], page, page_size),
        "total": 0,
        "page": page,
        "page_size": page_size,
        "total_pages": 1,
        "has_next": False,
        "has_prev": False,
    }


def _base_result(start: date, end: date, prop_id: int | None, **payload: Any) -> dict[str, Any]:
    return {
        "available": True,
        "source": "clickhouse",
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "prop_id": prop_id,
        **payload,
    }


def get_portfolio_dashboard(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 180,
    page: int = 1,
    page_size: int = 20,
    prop_id: int | None = None,
) -> dict[str, Any]:
    """Vista B — cartera compuesta (IE-G03): KPIs + serie + tabla por hotel."""
    start, end = _validate_range(date_from, date_to, days)
    if page < 1 or page_size < 1:
        raise ValueError("page y page_size deben ser mayores que cero")

    try:
        client = _client()
        try:
            hotels = _query_monthly(client, "strat_hotel_monthly", HOTEL_COLUMNS,
                                    "month ASC, prop_id ASC", start, end, prop_id=prop_id)
            prev_hotels = _query_prev(client, "strat_hotel_monthly", HOTEL_COLUMNS,
                                      "month ASC, prop_id ASC", start, end, prop_id=prop_id)
            plans = _query_monthly(client, "strat_plan_monthly", PLAN_COLUMNS,
                                   "month ASC, prop_id ASC, room_type_id ASC", start, end, prop_id=prop_id)
            reps = _query_monthly(client, "strat_reputation_monthly", REPUTATION_COLUMNS,
                                  "month ASC, prop_id ASC", start, end, prop_id=prop_id)
            prev_reps = _query_prev(client, "strat_reputation_monthly", REPUTATION_COLUMNS,
                                    "month ASC, prop_id ASC", start, end, prop_id=prop_id)
            markets = _query_monthly(client, "strat_market_monthly", MARKET_COLUMNS,
                                     "month ASC, visitor_location_country_id ASC, srch_destination_id ASC",
                                     start, end, prop_id=None)
            prev_markets = _query_prev(client, "strat_market_monthly", MARKET_COLUMNS,
                                       "month ASC, visitor_location_country_id ASC, srch_destination_id ASC",
                                       start, end, prop_id=None)
        finally:
            client.close()
    except Exception as exc:  # noqa: BLE001 - ClickHouse opcional durante desarrollo local.
        return _unavailable(exc, start, end, prop_id, page, page_size)

    rows = _build_cartera_rows(hotels, prev_hotels)
    return _base_result(
        start, end, prop_id,
        summary=_build_cartera_summary(hotels, prev_hotels, reps, prev_reps),
        series=_build_cartera_series(hotels),
        planes=_build_planes(plans, page, page_size),
        rankings=_build_rankings(hotels, prev_hotels, plans, reps, prev_reps, markets, prev_markets),
        **_paginate(rows, page, page_size),
    )


def get_hotel_dashboard(
    *,
    prop_id: int,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 180,
    page: int = 1,
    page_size: int = 20,
    planes_page: int = 1,
) -> dict[str, Any]:
    """Vista A — hotel compuesto (IE-H01/H02): KPIs + serie + tabla de
    registros mensuales (``page``) + rentabilidad por plan (``planes_page``).
    El scoping de pertenencia lo aplica la RUTA (``user_can_access_hotel``,
    deny-by-default)."""
    start, end = _validate_range(date_from, date_to, days)
    if page < 1 or page_size < 1 or planes_page < 1:
        raise ValueError("page, planes_page y page_size deben ser mayores que cero")

    try:
        client = _client()
        try:
            rows = _query_monthly(client, "strat_hotel_monthly", HOTEL_COLUMNS,
                                  "month ASC, prop_id ASC", start, end, prop_id=prop_id)
            prev_rows = _query_prev(client, "strat_hotel_monthly", HOTEL_COLUMNS,
                                    "month ASC, prop_id ASC", start, end, prop_id=prop_id)
            plans = _query_monthly(client, "strat_plan_monthly", PLAN_COLUMNS,
                                   "month ASC, prop_id ASC, room_type_id ASC", start, end, prop_id=prop_id)
            reps = _query_monthly(client, "strat_reputation_monthly", REPUTATION_COLUMNS,
                                  "month ASC, prop_id ASC", start, end, prop_id=prop_id)
            prev_reps = _query_prev(client, "strat_reputation_monthly", REPUTATION_COLUMNS,
                                    "month ASC, prop_id ASC", start, end, prop_id=prop_id)
        finally:
            client.close()
    except Exception as exc:  # noqa: BLE001 - ClickHouse opcional durante desarrollo local.
        return _unavailable(exc, start, end, prop_id, page, page_size)

    summary = {
        "kpis": _build_hotel_kpis(rows, prev_rows, reps, prev_reps),
        "hoteles": 1,
        "posicionamiento": _build_hotel_posicionamiento(reps, prev_reps, rows, prev_rows),
    }
    return _base_result(
        start, end, prop_id,
        summary=summary,
        serie=_build_hotel_serie(rows),
        posicionamiento_serie=_build_posicionamiento_serie(reps, rows),
        posicionamiento_rows=_build_posicionamiento_rows(reps, rows),
        planes=_build_planes(plans, planes_page, page_size),
        **_paginate(_build_hotel_rows(rows), page, page_size),
    )


def get_markets_dashboard(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 180,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Vista B — mercados compuesto (IE-G04): KPIs de demanda + serie + tabla."""
    start, end = _validate_range(date_from, date_to, days)
    if page < 1 or page_size < 1:
        raise ValueError("page y page_size deben ser mayores que cero")

    try:
        client = _client()
        try:
            rows = _query_monthly(client, "strat_market_monthly", MARKET_COLUMNS,
                                  "month ASC, visitor_location_country_id ASC, srch_destination_id ASC",
                                  start, end, prop_id=None)
            prev_rows = _query_prev(client, "strat_market_monthly", MARKET_COLUMNS,
                                    "month ASC, visitor_location_country_id ASC, srch_destination_id ASC",
                                    start, end, prop_id=None)
        finally:
            client.close()
    except Exception as exc:  # noqa: BLE001 - ClickHouse opcional durante desarrollo local.
        return _unavailable(exc, start, end, None, page, page_size)

    built = _build_markets(rows, prev_rows)
    return _base_result(
        start, end, None,
        summary=built["summary"],
        series=built["series"],
        **_paginate(built["rows"], page, page_size),
    )
