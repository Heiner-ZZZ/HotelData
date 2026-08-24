"""Read-only tactical invoice analytics from ClickHouse (F1.4).

El dashboard de facturación consulta únicamente ``kpi_invoice_daily`` (agregado
diario por hotel y estado). Nunca lee Mongo como sustituto ni replica facturas.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Any

from config.settings import get_settings

_COLUMNS = (
    "date, prop_id, hotel_label, status, invoice_count, subtotal, taxes, "
    "total, paid_total, pending_total, cancelled_total"
)

_STATUS_LABELS: dict[str, str] = {
    "issued": "Emitida",
    "paid": "Pagada",
    "cancelled": "Anulada",
    "refunded": "Reembolsada",
}

_PAYMENT_COLUMNS = (
    "date, prop_id, hotel_label, method, status, payment_count, paid_amount, "
    "refunded_amount, failed_amount, invoiced_amount, collected_amount, "
    "outstanding_amount"
)

_PAYMENT_METHOD_LABELS: dict[str, str] = {
    "card": "Tarjeta",
    "credit_card": "Tarjeta crédito",
    "cash": "Efectivo",
    "bank_transfer": "Transferencia",
    "simulated": "En línea",
    "": "Sin método",
}

_PAYMENT_STATUS_LABELS: dict[str, str] = {
    "confirmed": "Confirmado",
    "refunded": "Reembolsado",
    "failed": "Fallido",
    "rejected": "Rechazado",
    "declined": "Rechazado",
    "error": "Error",
    "no_payment": "Sin pagos",
    "": "Sin estado",
}


def _default_range(days: int) -> tuple[date, date]:
    end = datetime.now(timezone.utc).date()
    return end - timedelta(days=days - 1), end


def get_invoice_dashboard(
    *,
    prop_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 30,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Lee el KPI de facturación y devuelve resumen + serie + filas paginadas.

    ``paid_total``/``pending_total``/``cancelled_total`` provienen del agregado
    ETL (nunca se derivan aquí). El resumen y la serie reflejan SIEMPRE el rango
    completo; el filtro por estado solo afecta la grilla (mismo criterio que la
    página de Facturas, donde los stats no se acoplan al filtro). La paginación
    se aplica en Python porque la granularidad (día × hotel × estado) mantiene
    el resultado pequeño.
    """
    settings = get_settings()
    fallback_from, fallback_to = _default_range(days)
    start = date.fromisoformat(date_from) if date_from else fallback_from
    end = date.fromisoformat(date_to) if date_to else fallback_to
    if end < start:
        raise ValueError("date_to debe ser igual o posterior a date_from")
    if page < 1 or page_size < 1:
        raise ValueError("page y page_size deben ser mayores que cero")

    try:
        import clickhouse_connect  # type: ignore

        client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
        )
        try:
            where = ["date >= {date_from:Date}", "date <= {date_to:Date}"]
            params: dict[str, Any] = {"date_from": start, "date_to": end}
            if prop_id is not None:
                where.append("prop_id = {prop_id:UInt32}")
                params["prop_id"] = prop_id
            query = (
                f"SELECT {_COLUMNS} FROM kpi_invoice_daily FINAL WHERE "
                + " AND ".join(where)
                + " ORDER BY date ASC, prop_id ASC, status ASC"
            )
            result = client.query(query, parameters=params)
            all_rows = [_row_to_dict(row) for row in result.result_rows]
            # El filtro de estado aplica solo a la grilla, no a KPIs ni serie.
            grid_rows = [row for row in all_rows if not status or row["status"] == status]
            total = len(grid_rows)
            page_rows = grid_rows[(page - 1) * page_size : page * page_size]
            return {
                "available": True,
                "source": "clickhouse",
                "date_from": start.isoformat(),
                "date_to": end.isoformat(),
                "prop_id": prop_id,
                "summary": _summarise(all_rows),
                "series": _series(all_rows),
                "rows": page_rows,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": max(1, math.ceil(total / page_size)),
                "has_next": page * page_size < total,
                "has_prev": page > 1,
            }
        finally:
            client.close()
    except Exception as exc:  # ClickHouse es opcional durante el desarrollo local.
        return {
            "available": False,
            "source": "clickhouse",
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "prop_id": prop_id,
            "summary": _summarise([]),
            "series": {"labels": [], "datasets": []},
            "rows": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False,
            "message": str(exc),
        }


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    names = [name.strip() for name in _COLUMNS.split(",")]
    return {
        name: (value.isoformat() if hasattr(value, "isoformat") else value)
        for name, value in zip(names, row)
    }


def get_payments_dashboard(
    *,
    prop_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 30,
    method: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Dashboard F1.5: pagos por método/estado y saldo pendiente (ClickHouse).

    ``kpi_payment_daily`` desnormaliza el contexto de facturación por
    (día, hotel) en cada fila; por eso el resumen y la serie agregan las
    columnas ``invoiced_amount``/``collected_amount``/``outstanding_amount``
    sobre claves DISTINTAS (fecha, prop_id) para no contarlas por método.
    El filtro por método/estado solo afecta la grilla.
    """
    settings = get_settings()
    fallback_from, fallback_to = _default_range(days)
    start = date.fromisoformat(date_from) if date_from else fallback_from
    end = date.fromisoformat(date_to) if date_to else fallback_to
    if end < start:
        raise ValueError("date_to debe ser igual o posterior a date_from")
    if page < 1 or page_size < 1:
        raise ValueError("page y page_size deben ser mayores que cero")

    try:
        import clickhouse_connect  # type: ignore

        client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
        )
        try:
            where = ["date >= {date_from:Date}", "date <= {date_to:Date}"]
            params: dict[str, Any] = {"date_from": start, "date_to": end}
            if prop_id is not None:
                where.append("prop_id = {prop_id:UInt32}")
                params["prop_id"] = prop_id
            query = (
                f"SELECT {_PAYMENT_COLUMNS} FROM kpi_payment_daily FINAL WHERE "
                + " AND ".join(where)
                + " ORDER BY date ASC, prop_id ASC, method ASC, status ASC"
            )
            result = client.query(query, parameters=params)
            all_rows = [_payment_row_to_dict(row) for row in result.result_rows]
            grid_rows = [
                row
                for row in all_rows
                if (not method or row["method"] == method)
                and (not status or row["status"] == status)
            ]
            total = len(grid_rows)
            page_rows = grid_rows[(page - 1) * page_size : page * page_size]
            return {
                "available": True,
                "source": "clickhouse",
                "date_from": start.isoformat(),
                "date_to": end.isoformat(),
                "prop_id": prop_id,
                "summary": _summarise_payments(all_rows),
                "series": _series_payments(all_rows),
                "rows": page_rows,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": max(1, math.ceil(total / page_size)),
                "has_next": page * page_size < total,
                "has_prev": page > 1,
            }
        finally:
            client.close()
    except Exception as exc:  # ClickHouse es opcional durante el desarrollo local.
        return {
            "available": False,
            "source": "clickhouse",
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "prop_id": prop_id,
            "summary": _summarise_payments([]),
            "series": {"labels": [], "datasets": []},
            "rows": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False,
            "message": str(exc),
        }


def _payment_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    names = [name.strip() for name in _PAYMENT_COLUMNS.split(",")]
    return {
        name: (value.isoformat() if hasattr(value, "isoformat") else value)
        for name, value in zip(names, row)
    }


def _summarise_payments(rows: list[dict[str, Any]]) -> dict[str, Any]:
    payment_count = 0
    paid = refunded = failed = 0.0
    by_method: dict[str, dict[str, Any]] = {}
    by_status: dict[str, dict[str, Any]] = {}
    by_hotel: dict[tuple[int, str], dict[str, Any]] = {}
    # El contexto de facturación se agrega sobre claves (fecha, prop) únicas.
    day_context: dict[tuple[str, int], dict[str, float]] = {}

    for row in rows:
        payment_count += int(row.get("payment_count") or 0)
        paid += float(row.get("paid_amount") or 0)
        refunded += float(row.get("refunded_amount") or 0)
        failed += float(row.get("failed_amount") or 0)

        method = row.get("method") or ""
        mbucket = by_method.setdefault(method, {"method": method, "count": 0, "amount": 0.0})
        mbucket["count"] += int(row.get("payment_count") or 0)
        mbucket["amount"] += float(row.get("paid_amount") or 0)

        status = row.get("status") or ""
        sbucket = by_status.setdefault(status, {"status": status, "count": 0, "amount": 0.0})
        sbucket["count"] += int(row.get("payment_count") or 0)
        sbucket["amount"] += float(row.get("paid_amount") or 0) + float(row.get("refunded_amount") or 0) + float(row.get("failed_amount") or 0)

        hotel_key = (int(row.get("prop_id") or 0), row.get("hotel_label") or "")
        hotel = by_hotel.setdefault(hotel_key, {
            "prop_id": hotel_key[0], "hotel_label": hotel_key[1],
            "payment_count": 0, "collected_amount": 0.0,
            "_collected_days": {},
        })
        hotel["payment_count"] += int(row.get("payment_count") or 0)
        # El contexto ``collected_amount`` se repite en cada fila del día; se
        # agrega por (fecha, prop) únicos para no contarlo por método.
        day_key = (row.get("date") or "", hotel_key[0])
        hotel["_collected_days"][day_key] = max(
            hotel["_collected_days"].get(day_key, 0.0),
            float(row.get("collected_amount") or 0),
        )

        day_key = (row.get("date") or "", hotel_key[0])
        day_context.setdefault(day_key, {"invoiced": 0.0, "collected": 0.0})
        day_context[day_key]["invoiced"] = max(
            day_context[day_key]["invoiced"], float(row.get("invoiced_amount") or 0)
        )
        day_context[day_key]["collected"] = max(
            day_context[day_key]["collected"], float(row.get("collected_amount") or 0)
        )

    invoiced = sum(ctx["invoiced"] for ctx in day_context.values())
    collected = sum(ctx["collected"] for ctx in day_context.values())
    return {
        "payment_count": payment_count,
        "paid_amount": _round(paid),
        "refunded_amount": _round(refunded),
        "failed_amount": _round(failed),
        "invoiced_amount": _round(invoiced),
        "collected_amount": _round(collected),
        "outstanding_amount": _round(invoiced - collected),
        "by_method": sorted(
            ({"method": m["method"], "label": _PAYMENT_METHOD_LABELS.get(m["method"], m["method"]),
              "count": m["count"], "amount": _round(m["amount"])}
             for m in by_method.values() if m["count"] > 0),
            key=lambda item: item["amount"],
            reverse=True,
        ),
        "by_status": {
            key: {"count": value["count"], "amount": _round(value["amount"]),
                   "label": _PAYMENT_STATUS_LABELS.get(key, key)}
            for key, value in sorted(by_status.items())
        },
        "by_hotel": sorted(
            ({"prop_id": h["prop_id"], "hotel_label": h["hotel_label"],
              "payment_count": h["payment_count"],
              "collected_amount": _round(sum(h["_collected_days"].values()))}
             for h in by_hotel.values()),
            key=lambda item: item["collected_amount"],
            reverse=True,
        ),
    }


def _series_payments(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Evolución diaria: cobrado, facturado y saldo pendiente."""
    daily: dict[str, dict[str, float]] = {}
    day_context: dict[tuple[str, int], dict[str, float]] = {}
    for row in rows:
        day = row.get("date") or ""
        bucket = daily.setdefault(day, {"paid": 0.0, "refunded": 0.0})
        bucket["paid"] += float(row.get("paid_amount") or 0)
        bucket["refunded"] += float(row.get("refunded_amount") or 0)
        day_key = (day, int(row.get("prop_id") or 0))
        ctx = day_context.setdefault(day_key, {"invoiced": 0.0, "collected": 0.0})
        ctx["invoiced"] = max(ctx["invoiced"], float(row.get("invoiced_amount") or 0))
        ctx["collected"] = max(ctx["collected"], float(row.get("collected_amount") or 0))
    labels = sorted(daily)
    invoiced_by_day: dict[str, float] = {}
    collected_by_day: dict[str, float] = {}
    for (day, _prop), ctx in day_context.items():
        invoiced_by_day[day] = invoiced_by_day.get(day, 0.0) + ctx["invoiced"]
        collected_by_day[day] = collected_by_day.get(day, 0.0) + ctx["collected"]
    return {
        "labels": labels,
        "datasets": [
            {"label": "Cobrado", "data": [_round(daily[d]["paid"]) for d in labels]},
            {"label": "Facturado", "data": [_round(invoiced_by_day.get(d, 0.0)) for d in labels]},
            {"label": "Pendiente", "data": [_round(invoiced_by_day.get(d, 0.0) - collected_by_day.get(d, 0.0)) for d in labels]},
        ],
    }


def _round(value: float) -> float:
    return round(float(value or 0), 2)


def _summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_status: dict[str, dict[str, Any]] = {}
    by_hotel: dict[tuple[int, str], dict[str, Any]] = {}
    invoice_count = 0
    subtotal = taxes = total = paid_total = pending_total = cancelled_total = 0.0
    for row in rows:
        invoice_count += int(row.get("invoice_count") or 0)
        subtotal += float(row.get("subtotal") or 0)
        taxes += float(row.get("taxes") or 0)
        total += float(row.get("total") or 0)
        paid_total += float(row.get("paid_total") or 0)
        pending_total += float(row.get("pending_total") or 0)
        cancelled_total += float(row.get("cancelled_total") or 0)

        status = row.get("status") or ""
        bucket = by_status.setdefault(status, {"count": 0, "total": 0.0})
        bucket["count"] += int(row.get("invoice_count") or 0)
        bucket["total"] += float(row.get("total") or 0)

        hotel_key = (int(row.get("prop_id") or 0), row.get("hotel_label") or "")
        hotel = by_hotel.setdefault(hotel_key, {
            "prop_id": hotel_key[0], "hotel_label": hotel_key[1],
            "invoice_count": 0, "total": 0.0,
        })
        hotel["invoice_count"] += int(row.get("invoice_count") or 0)
        hotel["total"] += float(row.get("total") or 0)

    return {
        "invoice_count": invoice_count,
        "subtotal": _round(subtotal),
        "taxes": _round(taxes),
        "total_amount": _round(total),
        "paid_total": _round(paid_total),
        "pending_total": _round(pending_total),
        "cancelled_total": _round(cancelled_total),
        "by_status": {
            key: {"count": value["count"], "total": _round(value["total"]), "label": _STATUS_LABELS.get(key, key)}
            for key, value in sorted(by_status.items())
        },
        "by_hotel": sorted(
            ({"prop_id": h["prop_id"], "hotel_label": h["hotel_label"],
              "invoice_count": h["invoice_count"], "total": _round(h["total"])}
             for h in by_hotel.values()),
            key=lambda item: item["total"],
            reverse=True,
        ),
    }


def _series(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Evolución diaria del monto facturado, pagado y pendiente."""
    daily: dict[str, dict[str, float]] = {}
    for row in rows:
        day = row.get("date") or ""
        bucket = daily.setdefault(day, {"billed": 0.0, "paid": 0.0, "pending": 0.0, "cancelled": 0.0})
        bucket["billed"] += float(row.get("total") or 0)
        bucket["paid"] += float(row.get("paid_total") or 0)
        bucket["pending"] += float(row.get("pending_total") or 0)
        bucket["cancelled"] += float(row.get("cancelled_total") or 0)
    labels = sorted(daily)
    return {
        "labels": labels,
        "datasets": [
            {"label": "Facturado", "data": [_round(daily[d]["billed"]) for d in labels]},
            {"label": "Pagado", "data": [_round(daily[d]["paid"]) for d in labels]},
            {"label": "Pendiente", "data": [_round(daily[d]["pending"]) for d in labels]},
        ],
    }
