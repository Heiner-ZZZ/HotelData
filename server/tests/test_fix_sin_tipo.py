"""Tests de la lógica pura del fix 'Sin tipo' (fusión de filas de
strat_plan_monthly con room_type_id vacío hacia el tipo base del hotel).

Regla: solo se tocan filas de hoteles incluidos en el mapeo (nada demo/test);
las filas con tipo real se conservan intactas; si el hotel ya tiene fila del
tipo objetivo en ese mes se FUSIONA (suma de métricas), y si no, la fila vacía
se RENOMBRA al tipo objetivo. Es la lógica que usa el script de corrección de
datos (server/scripts/fix_sin_tipo.py) contra booking_orders + strat_plan_monthly.
"""

from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path

_FIX_PATH = Path(__file__).resolve().parent.parent / "scripts" / "fix_sin_tipo.py"
_spec = importlib.util.spec_from_file_location("fix_sin_tipo", _FIX_PATH)
_fix = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_fix)
merge_sin_tipo = _fix.merge_sin_tipo
SIN_TIPO_MAPPING = _fix.SIN_TIPO_MAPPING


def _row(month="2026-07-01", prop=1, rt="", label="", bookings=0, sold=0,
         nights=0, revenue="0.00", discount="0.00", adults=0, children=0, cancelled=0):
    return {
        "month": month, "prop_id": prop, "hotel_label": f"Hotel {prop}",
        "room_type_id": rt, "room_type_label": label, "currency": "USD",
        "bookings": bookings, "rooms_sold": sold, "room_nights": nights,
        "revenue": Decimal(revenue), "discount_amount": Decimal(discount),
        "adults": adults, "children": children, "cancelled_rooms": cancelled,
    }


def test_renombra_fila_vacia_cuando_no_existe_tipo_base() -> None:
    """Jun/2026 prop 1 solo tiene la fila vacía → se renombra a Standard."""
    rows = [_row(month="2026-06-01", prop=1, bookings=3, sold=3, nights=5,
                 revenue="627.10", discount="1.40", adults=3)]
    out = merge_sin_tipo(rows, SIN_TIPO_MAPPING)
    assert len(out) == 1
    r = out[0]
    assert r["room_type_id"] == "RT-1-standard"
    assert r["room_type_label"] == "Habitación Standard"
    assert r["bookings"] == 3
    assert r["revenue"] == Decimal("627.10")


def test_fusiona_fila_vacia_en_el_tipo_base_existente() -> None:
    """Jul/2026 prop 1: la fila vacía (2, 516.50) se suma a Standard (3, 201.80)."""
    rows = [
        _row(month="2026-07-01", prop=1, rt="RT-1-standard", label="Habitación Standard",
             bookings=3, sold=2, nights=2, revenue="201.80", adults=3, children=1, cancelled=1),
        _row(month="2026-07-01", prop=1, bookings=2, sold=2, nights=3,
             revenue="516.50", adults=2),
    ]
    out = merge_sin_tipo(rows, SIN_TIPO_MAPPING)
    assert len(out) == 1
    r = out[0]
    assert r["room_type_id"] == "RT-1-standard"
    assert r["bookings"] == 5
    assert r["rooms_sold"] == 4
    assert r["room_nights"] == 5
    assert r["revenue"] == Decimal("718.30")  # 201.80 + 516.50
    assert r["adults"] == 5
    assert r["children"] == 1
    assert r["cancelled_rooms"] == 1


def test_renombra_fila_vacia_de_otro_hotel_en_el_mapeo() -> None:
    """Jul/2026 prop 2 (solo fila vacía) → RT-2-standard."""
    rows = [_row(month="2026-07-01", prop=2, bookings=1, sold=1, nights=2,
                 revenue="422.50", adults=1)]
    out = merge_sin_tipo(rows, SIN_TIPO_MAPPING)
    assert len(out) == 1
    assert out[0]["room_type_id"] == "RT-2-standard"
    assert out[0]["room_type_label"] == "Habitación Standard"


def test_filas_con_tipo_real_se_conservan_intactas() -> None:
    """Deluxe y Doble Premiun no se tocan; el orden de filas se preserva."""
    rows = [
        _row(month="2026-08-01", prop=1, rt="RT-1-deluxe", label="Habitación Deluxe",
             bookings=1, revenue="188.00"),
        _row(month="2026-08-01", prop=1, rt="RT-1-habitacion-doble-premiun",
             label="Habitacion Doble Premiun", bookings=2, revenue="1316.00"),
    ]
    out = merge_sin_tipo(rows, SIN_TIPO_MAPPING)
    assert [r["room_type_id"] for r in out] == [
        "RT-1-deluxe", "RT-1-habitacion-doble-premiun",
    ]


def test_filas_vacias_de_hoteles_fuera_del_mapeo_no_se_tocan() -> None:
    """Un hotel no incluido en el mapeo (p.ej. 140766) conserva su fila vacía."""
    rows = [_row(month="2026-07-01", prop=140766, bookings=1, revenue="10.00")]
    out = merge_sin_tipo(rows, SIN_TIPO_MAPPING)
    assert len(out) == 1
    assert out[0]["room_type_id"] == ""
    assert out[0]["room_type_label"] == ""
