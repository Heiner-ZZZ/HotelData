"""Reservations CSV export logic — formato normalizado profesional."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any

from src.database.connection import get_database


def _fmt_date(value: Any) -> str:
    """Normaliza a dd/mm/yyyy — acepta ISO YYYY-MM-DD, datetime o string."""
    if not value:
        return ""
    try:
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y")
        s = str(value).strip()
        # ISO datetime con T
        if "T" in s:
            s = s.split("T")[0]
        # YYYY-MM-DD
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            d = datetime.strptime(s[:10], "%Y-%m-%d")
            return d.strftime("%d/%m/%Y")
        # dd/mm/yyyy ya normalizado
        if "/" in s:
            return s
        return s
    except Exception:
        return str(value)


def _fmt_datetime(value: Any) -> str:
    """Normaliza a dd/mm/yyyy HH:mm para timestamps."""
    if not value:
        return ""
    try:
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y %H:%M")
        s = str(value).strip()
        # Intenta ISO 8601
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                d = datetime.strptime(s[:19], fmt)
                return d.strftime("%d/%m/%Y %H:%M") if "H" in fmt else d.strftime("%d/%m/%Y")
            except Exception:
                continue
        if "T" in s:
            s = s.replace("T", " ")
        return s[:16]
    except Exception:
        return str(value)


def _fmt_amount(value: Any) -> str:
    """Importe con 2 decimales sin símbolo — encabezado indica (USD)."""
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


_STATUS_LABELS: dict[str, str] = {
    "pending": "Pendiente",
    "confirmed": "Confirmada",
    "cancelled": "Cancelada",
    "checked_in": "Check-in",
    "checked_out": "Check-out",
    "no_show": "No show",
}


def export_reservations_csv(
    status_filter: str | None = None,
    prop_id: int | None = None,
) -> tuple[io.StringIO, str]:
    """Generate a CSV export of reservations with optional filters.

    Formato normalizado: BOM UTF-8, encabezados en español, fechas dd/mm/yyyy,
    montos 2 decimales, separador coma RFC4180.

    Returns (output_buffer, raw_date_string).
    """
    db = get_database()
    filters: dict[str, Any] = {}
    if status_filter:
        filters["status"] = status_filter
    if prop_id:
        filters["prop_id"] = prop_id
    bookings = list(db.booking_orders.find(filters, {"_id": 0}).sort([("created_at", -1)]))

    output = io.StringIO()
    # BOM UTF-8 para Excel Windows
    output.write("\ufeff")
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "ID Reserva", "ID Propiedad", "Estado", "Huésped", "Email Huésped", "Tel. Huésped",
        "Check-in", "Check-out", "Adultos", "Niños", "Habitaciones",
        "Importe Total (USD)", "Divisa", "Noches", "Canal", "Creado", "Comentario",
    ])
    for b in bookings:
        writer.writerow([
            b.get("booking_id", ""),
            b.get("prop_id", ""),
            _STATUS_LABELS.get(str(b.get("status", "")), str(b.get("status", ""))),
            b.get("guest_name", ""),
            b.get("guest_email", ""),
            b.get("guest_phone", ""),
            _fmt_date(b.get("check_in_date")),
            _fmt_date(b.get("check_out_date")),
            b.get("adults", ""),
            b.get("children", ""),
            b.get("rooms", ""),
            _fmt_amount(b.get("total_price")),
            b.get("currency", ""),
            b.get("total_nights", ""),
            b.get("booking_source", ""),
            _fmt_datetime(b.get("created_at")),
            b.get("comment", ""),
        ])

    output.seek(0)
    raw_date = datetime.now().strftime("%Y-%m-%d")
    return output, raw_date
