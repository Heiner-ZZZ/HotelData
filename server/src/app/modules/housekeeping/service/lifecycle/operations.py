"""Read-only tactical operations analytics from ClickHouse."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from config.settings import get_settings


_COLUMNS = (
    "date, prop_id, hotel_label, tasks_total, tasks_completed, "
    "tasks_completed_on_time, tasks_with_completed_at, maintenance_total, "
    "maintenance_completed, maintenance_completed_on_time, rooms_status_events, "
    "rooms_to_clean, rooms_cleaned, rooms_available_after_cleaning, "
    "avg_cleaning_minutes, avg_checkout_to_available_minutes, rotation_observed, "
    "inventory_available_rooms, inventory_blocked_rooms, inventory_total_rooms, "
    "charges_total, charges_amount, supplier_country_coverage"
)


def _default_range(days: int) -> tuple[date, date]:
    end = date.today()
    return end - timedelta(days=days - 1), end


def get_operations_analytics(
    *,
    prop_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 30,
) -> dict[str, Any]:
    """Read the compact operations KPI; never reads Mongo from the dashboard.

    Missing timestamps are represented as null in ClickHouse and remain excluded
    from averages. This endpoint therefore reports an explicit ``rotation_observed``
    count instead of presenting an invented checkout-to-available value.
    """
    settings = get_settings()
    fallback_from, fallback_to = _default_range(days)
    start = date.fromisoformat(date_from) if date_from else fallback_from
    end = date.fromisoformat(date_to) if date_to else fallback_to
    if end < start:
        raise ValueError("date_to debe ser igual o posterior a date_from")

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
                f"SELECT {_COLUMNS} FROM kpi_housekeeping_daily FINAL WHERE "
                + " AND ".join(where)
                + " ORDER BY date ASC, prop_id ASC"
            )
            result = client.query(query, parameters=params)
            rows = [_row_to_dict(row) for row in result.result_rows]
            return {
                "available": True,
                "source": "clickhouse",
                "date_from": start.isoformat(),
                "date_to": end.isoformat(),
                "prop_id": prop_id,
                "rows": rows,
                "summary": _summarise(rows),
            }
        finally:
            client.close()
    except Exception as exc:  # ClickHouse is optional during local development.
        return {
            "available": False,
            "source": "clickhouse",
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "prop_id": prop_id,
            "rows": [],
            "summary": _summarise([]),
            "message": str(exc),
        }


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    names = _COLUMNS.replace(" ", "").split(",")
    return {
        name: (value.isoformat() if hasattr(value, "isoformat") else value)
        for name, value in zip(names, row)
    }


def _summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def total(key: str) -> int | float:
        return sum((row.get(key) or 0) for row in rows)

    observed = int(total("rotation_observed"))
    cleaning_samples = [row["avg_cleaning_minutes"] for row in rows if row.get("avg_cleaning_minutes") is not None]
    rotation_samples = [row["avg_checkout_to_available_minutes"] for row in rows if row.get("avg_checkout_to_available_minutes") is not None]
    return {
        "tasks_total": int(total("tasks_total")),
        "tasks_completed": int(total("tasks_completed")),
        "maintenance_total": int(total("maintenance_total")),
        "maintenance_completed": int(total("maintenance_completed")),
        "rooms_cleaned": int(total("rooms_cleaned")),
        "inventory_available_rooms": int(total("inventory_available_rooms")),
        "inventory_blocked_rooms": int(total("inventory_blocked_rooms")),
        "charges_amount": float(total("charges_amount")),
        "rotation_observed": observed,
        "avg_cleaning_minutes": sum(cleaning_samples) / len(cleaning_samples) if cleaning_samples else None,
        "avg_checkout_to_available_minutes": sum(rotation_samples) / len(rotation_samples) if rotation_samples else None,
    }
