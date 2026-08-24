"""Tests de la lógica pura del fix de coordenadas de strat_hotel_monthly.

Replica la semántica del ETL (_enrich_strat_hotel_geo): la coordenada REAL por
hotel (dim_hotels.latitude/longitude) gana; si el hotel no la tiene, se usa el
centro de ciudad (geo_catalog type=city por nombre); si tampoco hay, queda
None (honesto, nunca inventada).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_FIX_PATH = Path(__file__).resolve().parent.parent / "scripts" / "fix_strat_hotel_coords.py"
_spec = importlib.util.spec_from_file_location("fix_strat_hotel_coords", _FIX_PATH)
_fix = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_fix)
resolve_strat_coords = _fix.resolve_strat_coords


def test_coordenada_real_del_hotel_gana() -> None:
    """prop 1: dim_hotels tiene lat/lng reales → se usan (caso del mapa IE-H02)."""
    rows = [{"prop_id": 1, "city": "Lima", "city_lat": None, "city_lng": None}]
    hotels = {1: {"city": "Lima", "latitude": -12.0464, "longitude": -77.0428}}
    out = resolve_strat_coords(rows, hotels, {})
    assert out[0]["city"] == "Lima"
    assert out[0]["city_lat"] == -12.0464
    assert out[0]["city_lng"] == -77.0428


def test_sin_coord_de_hotel_usa_centro_de_ciudad_del_catalogo() -> None:
    """Hotel sin lat/lng propia pero ciudad en geo_catalog → centro de ciudad."""
    rows = [{"prop_id": 9, "city": "Lima", "city_lat": None, "city_lng": None}]
    hotels = {9: {"city": "Lima", "latitude": None, "longitude": None}}
    geo = {"lima": (10.0, -70.0)}
    out = resolve_strat_coords(rows, hotels, geo)
    assert out[0]["city_lat"] == 10.0
    assert out[0]["city_lng"] == -70.0


def test_sin_coord_ni_catalogo_queda_none_honesto() -> None:
    """Sin coord de hotel y sin ciudad en el catálogo → None (nunca inventada)."""
    rows = [{"prop_id": 9, "city": "CiudadFalsa", "city_lat": None, "city_lng": None}]
    hotels = {9: {"city": "CiudadFalsa", "latitude": None, "longitude": None}}
    out = resolve_strat_coords(rows, hotels, {})
    assert out[0]["city_lat"] is None
    assert out[0]["city_lng"] is None


def test_no_reescribe_coords_ya_presentes() -> None:
    """prop 2 ya tiene coords en strat → no se pisan con otra fuente."""
    rows = [{"prop_id": 2, "city": "Cancún", "city_lat": 21.1619, "city_lng": -86.8515}]
    hotels = {2: {"city": "Cancún", "latitude": 21.15, "longitude": -86.81}}
    out = resolve_strat_coords(rows, hotels, {"cancún": (21.1619, -86.8515)})
    assert out[0]["city_lat"] == 21.1619
    assert out[0]["city_lng"] == -86.8515
