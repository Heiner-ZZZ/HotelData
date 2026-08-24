"""Tests del fix de reubicación del hotel 2 (académico, aprobado por el dueño).

Mueve el Resort Cancún Playa (prop 2) a una ciudad cercana a Lima-Perú para
demostrar el funcionamiento del posicionamiento competitivo (IE-H02): con
coordenadas dentro del ``RADIO_KM`` de prop 1, ambos hoteles se convierten en
competidores reales (Haversine literal) y la banda/percentil/mapa se llenan.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_FIX_PATH = Path(__file__).resolve().parent.parent / "scripts" / "relocate_hotel_2_lima.py"
_spec = importlib.util.spec_from_file_location("relocate_hotel_2_lima", _FIX_PATH)
_fix = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_fix)
RELOCATE = _fix.RELOCATE

# Hotel Lima Centro (prop 1) — referencia del radio competitivo.
PROP1_LAT, PROP1_LNG = -12.0464, -77.0428


def test_hotel2_se_mueve_a_peru() -> None:
    assert RELOCATE["prop_id"] == 2
    assert RELOCATE["country_id"] == 219  # Perú en dim_visitor_countries
    assert RELOCATE["country_label"] == "Perú"
    assert RELOCATE["city"] == "Lima"
    assert RELOCATE["destination_id"] == 89  # Lima en dim_destinations


def test_hotel2_queda_dentro_del_radio_competitivo_de_hotel1() -> None:
    """Ambos con coordenadas → Haversine <= RADIO_KM hace que compitan."""
    from src.app.modules.strategic.kpi_strategic import RADIO_KM, haversine_km

    d = haversine_km(PROP1_LAT, PROP1_LNG, RELOCATE["latitude"], RELOCATE["longitude"])
    assert d <= RADIO_KM, f"distancia {d} km > radio {RADIO_KM} km — no serían competidores"
    assert d > 0, "no pueden estar en el mismo punto exacto"
