"""Tests de los informes estratégicos TAF14 (Vista A y B) sobre tablas ``strat_*``.

Siguen el principio de los informes tácticos compuestos: cada dashboard lee
las tablas mensuales ``strat_*`` y devuelve ``summary`` (KPIs en cajas
separadas) + ``series`` (gráficos) + ``rows`` (tabla de registros paginada).
Los 7 informes dictados en TAF14: Vista A = IE-H01 (desempeño + rentabilidad
por plan) e IE-H02 (posicionamiento); Vista B = IE-G01 (KPIs estratégicos),
IE-G02 (rankings R-G01..R-G06), IE-G03 (rentabilidad de cartera), IE-G04
(mercados) e IE-G05 (forecasting). El BSC quedó fuera del alcance por
decisión del dueño (patrón Z, KPIs en cajas separadas).

Cubren las funciones puras (sin depender de ClickHouse levantado), la
validación de rango y el gate de permiso ``reports.strategic.read``. La
conectividad real se verifica con una prueba de integración que se salta si
CH no está disponible.
"""

from __future__ import annotations

import pytest
from passlib.context import CryptContext

# ─── Fixtures de filas (mismo shape que transform.TABLE_COLUMNS) ─────────

_HOTEL_ROW = {
    "month": "2026-07-01", "prop_id": 1, "hotel_label": "Hotel A",
    "currency": "USD", "bookings": 10, "rooms_sold": 10, "room_nights": 30,
    "revenue": 3000.0, "discount_amount": 300.0, "adults": 20, "children": 5,
    "cancelled_rooms": 1, "total_rooms": 2,
}


def _hotel_row(**overrides) -> dict:
    row = dict(_HOTEL_ROW)
    row.update(overrides)
    return row


def _rep_row(**overrides) -> dict:
    row = {
        "month": "2026-07-01", "prop_id": 1, "hotel_label": "Hotel A",
        "reviews": 10, "avg_rating": 4.5, "positive": 8, "neutral": 1,
        "negative": 1, "responded": 8, "response_rate": 80.0,  # porcentaje (0-100), igual que el ETL
    }
    row.update(overrides)
    return row


def _plan_row(**overrides) -> dict:
    row = {
        "month": "2026-07-01", "prop_id": 1, "hotel_label": "Hotel A",
        "room_type_id": "RT-1", "room_type_label": "Estándar", "currency": "USD",
        "bookings": 10, "rooms_sold": 10, "room_nights": 30, "revenue": 3000.0,
        "discount_amount": 300.0, "adults": 20, "children": 5, "cancelled_rooms": 1,
    }
    row.update(overrides)
    return row


def _market_row(**overrides) -> dict:
    row = {
        "month": "2026-07-01", "visitor_location_country_id": 1,
        "visitor_country_label": "Perú", "srch_destination_id": 10,
        "destination_label": "Cusco", "searches": 100, "clicks": 30,
        "reservations": 5, "revenue_usd": 500.0,
    }
    row.update(overrides)
    return row


# ─── Vista A — hotel individual (IE-H01 / IE-H02) ─────────────────────────

def test_hotel_kpis_single_hotel_math() -> None:
    from src.app.modules.strategic.kpi_strategic import _build_hotel_kpis

    rows = [
        _hotel_row(month="2026-07-01", prop_id=1, hotel_label="Hotel A", revenue=3000.0,
                   room_nights=30, bookings=10, total_rooms=2),
        _hotel_row(month="2026-08-01", prop_id=1, hotel_label="Hotel A", revenue=3100.0,
                   room_nights=31, bookings=11, total_rooms=2),
    ]
    prev = [_hotel_row(revenue=2000.0, room_nights=20, bookings=8)]
    reps = [
        _rep_row(month="2026-07-01", prop_id=1, reviews=10, avg_rating=4.5, response_rate=80.0),
        _rep_row(month="2026-08-01", prop_id=1, reviews=10, avg_rating=4.3, response_rate=50.0),
    ]
    prev_reps = [_rep_row(month="2026-06-01", prop_id=1, reviews=10, avg_rating=4.0, response_rate=60.0)]

    kpis = {k["id"]: k for k in _build_hotel_kpis(rows, prev, reps, prev_reps)}
    assert kpis["revenue"]["value"] == 6100.0
    assert kpis["revenue"]["pct_change"] == 205.0  # vs 2000 del período anterior
    assert kpis["revenue"]["trend"] == "up"
    assert kpis["adr"]["value"] == 100.0  # 6100 / 61 noches
    assert kpis["ocupacion"]["value"] == round(61 / 124 * 100, 2)
    assert kpis["rating"]["value"] == 4.4
    assert kpis["respuesta"]["value"] == 65.0  # (80·10 + 50·10)/20, sin doble ×100
    assert kpis["bookings"]["value"] == 21


def test_respuesta_rate_is_percentage_not_fraction() -> None:
    """Regresión: ``response_rate`` viene del ETL como PORCENTAJE (0-100).
    El KPI debe exponerlo tal cual (65 = 65%), nunca multiplicarlo por 100
    otra vez (eso mostró 3,333% en dev cuando la tasa real era 33,33%)."""
    from src.app.modules.strategic.kpi_strategic import _build_hotel_kpis

    rows = [_hotel_row(revenue=3000.0, room_nights=30, bookings=10, total_rooms=2)]
    reps = [_rep_row(reviews=10, avg_rating=4.5, response_rate=33.33)]
    kpis = {k["id"]: k for k in _build_hotel_kpis(rows, [], reps, [])}
    assert kpis["respuesta"]["value"] == 33.33
    assert kpis["respuesta"]["unit"] == "%"
    assert kpis["respuesta"]["value"] < 100  # una tasa real nunca excede 100%


def test_kpi_exposes_has_prev_flag() -> None:
    """El KPI distingue "sin cambio real" de "sin período anterior para
    comparar". Con ``prev`` presente → ``has_prev`` True y variación real;
    sin datos previos → ``has_prev`` False y ``pct_change`` 0 (el frontend
    mostrará "sin comparación" en vez de un engañoso 0.0%)."""
    from src.app.modules.strategic.kpi_strategic import _build_hotel_kpis

    rows = [_hotel_row(revenue=3000.0, room_nights=30, bookings=10, total_rooms=2)]
    prev = [_hotel_row(revenue=2500.0, room_nights=25, bookings=9, total_rooms=2)]
    kpis = {k["id"]: k for k in _build_hotel_kpis(rows, prev, [], [])}
    assert kpis["revenue"]["has_prev"] is True
    assert kpis["revenue"]["pct_change"] == 20.0  # (3000-2500)/2500*100

    kpis_sin_prev = {k["id"]: k for k in _build_hotel_kpis(rows, [], [], [])}
    assert kpis_sin_prev["revenue"]["has_prev"] is False
    assert kpis_sin_prev["revenue"]["pct_change"] == 0.0


def test_cancelacion_y_descuento_comparan_vs_periodo_anterior() -> None:
    """Regresión: Cancelaciones y Descuento pasaban ``prev=0.0`` fijo, así que
    su variación era SIEMPRE 0.0% aunque hubiera datos previos. Ahora comparan
    contra la tasa real del período anterior (cancelación y descuento)."""
    from src.app.modules.strategic.kpi_strategic import _build_hotel_kpis

    rows = [_hotel_row(revenue=3000.0, room_nights=30, bookings=10, total_rooms=2,
                       cancelled_rooms=1, discount_amount=300.0)]
    prev = [_hotel_row(revenue=3000.0, room_nights=30, bookings=10, total_rooms=2,
                       cancelled_rooms=3, discount_amount=150.0)]
    kpis = {k["id"]: k for k in _build_hotel_kpis(rows, prev, [], [])}

    # Cancelación actual = 1/10·100 = 10%; previa = 3/10·100 = 30% → -66.67%
    assert kpis["cancelacion"]["has_prev"] is True
    assert kpis["cancelacion"]["pct_change"] == round((10 - 30) / 30 * 100, 2)
    # Descuento actual = 300/3300·100 = 9.09%; previo = 150/3150·100 = 4.76%
    desc_actual = 300 / 3300 * 100
    desc_prev = 150 / 3150 * 100
    assert kpis["descuento"]["has_prev"] is True
    assert kpis["descuento"]["pct_change"] == round((desc_actual - desc_prev) / desc_prev * 100, 2)


def test_revenue_growth_mirrors_growth_and_has_prev() -> None:
    """Crecimiento de revenue: su ``value`` YA es la variación vs período
    anterior; su propio ``pct_change`` debe espejarla (no quedar fijo en 0.0)
    y ``has_prev`` refleja si existe revenue previo."""
    from src.app.modules.strategic.kpi_strategic import _build_hotel_kpis

    rows = [_hotel_row(revenue=3000.0, room_nights=30, bookings=10, total_rooms=2)]
    prev = [_hotel_row(revenue=2500.0, room_nights=25, bookings=9, total_rooms=2)]
    kpis = {k["id"]: k for k in _build_hotel_kpis(rows, prev, [], [])}
    assert kpis["revenue_growth"]["value"] == 20.0
    assert kpis["revenue_growth"]["pct_change"] == 20.0
    assert kpis["revenue_growth"]["has_prev"] is True

    kpis_sin_prev = {k["id"]: k for k in _build_hotel_kpis(rows, [], [], [])}
    assert kpis_sin_prev["revenue_growth"]["value"] == 0.0
    assert kpis_sin_prev["revenue_growth"]["pct_change"] == 0.0
    assert kpis_sin_prev["revenue_growth"]["has_prev"] is False


def test_hotel_rows_monthly_records_table() -> None:
    """Tabla de registros (patrón compuesto): una fila por mes del hotel con
    bruto/neto/descuento, ADR, ocupación, RevPAR y cancelación."""
    from src.app.modules.strategic.kpi_strategic import _build_hotel_rows

    rows = [
        _hotel_row(month="2026-07-01", bookings=10, rooms_sold=10, room_nights=30,
                   revenue=3000.0, discount_amount=300.0, cancelled_rooms=1, total_rooms=2),
        _hotel_row(month="2026-08-01", bookings=11, rooms_sold=11, room_nights=31,
                   revenue=3100.0, discount_amount=310.0, cancelled_rooms=2, total_rooms=2),
    ]
    monthly = _build_hotel_rows(rows)
    assert len(monthly) == 2
    july = next(m for m in monthly if m["month"] == "2026-07-01")
    assert july["bookings"] == 10
    assert july["room_nights"] == 30
    assert july["revenue_bruto"] == 3300.0
    assert july["revenue_neto"] == 3000.0
    assert july["descuento"] == 300.0
    assert july["adr"] == 100.0
    assert july["ocupacion_pct"] == round(30 / (2 * 31) * 100, 2)  # julio = 31 días
    assert july["revpar"] == round(3000 / 62, 2)
    assert july["cancelacion_pct"] == 10.0


def test_haversine_km_known_distance() -> None:
    """Haversine con coordenadas reales (centros de ciudad de geo_catalog):
    CDMX → Guadalajara ≈ 460 km; el mismo punto da 0 km."""
    from src.app.modules.strategic.kpi_strategic import haversine_km

    dist = haversine_km(19.4326, -99.1332, 20.6597, -103.3496)
    assert 440 < dist < 480, dist
    assert haversine_km(19.4326, -99.1332, 19.4326, -99.1332) == 0.0


def test_banda_precio_percentiles() -> None:
    """Banda de precio por percentiles (interpolación lineal)."""
    from src.app.modules.strategic.kpi_strategic import _banda_precio

    assert _banda_precio([100.0, 200.0, 300.0, 400.0]) == {
        "p25": 175.0, "p50": 250.0, "p75": 325.0,
    }
    assert _banda_precio([80.0, 120.0]) == {"p25": 90.0, "p50": 100.0, "p75": 110.0}
    assert _banda_precio([]) is None


def test_percentile_rank_of_value() -> None:
    """Percentil empírico: % de competidores con valor ESTRICTAMENTE menor."""
    from src.app.modules.strategic.kpi_strategic import _percentile_rank

    values = [50.0, 100.0, 150.0, 200.0]
    assert _percentile_rank(values, 50.0) == 0.0
    assert _percentile_rank(values, 100.0) == 25.0
    assert _percentile_rank(values, 200.0) == 75.0
    assert _percentile_rank([], 100.0) is None


def test_hotel_posicionamiento_competitive_set_by_city() -> None:
    """IE-H02 Nivel 1: el conjunto competitivo son los hoteles de la MISMA
    ciudad con datos en la plataforma; el ADR propio se posiciona por
    percentiles contra su banda de precio (sin diagnóstico enlatado)."""
    from src.app.modules.strategic.kpi_strategic import _build_hotel_posicionamiento

    rows = [_hotel_row(prop_id=1, hotel_label="Hotel Lima", revenue=3000.0, room_nights=30)]
    prev = [_hotel_row(prop_id=1, revenue=2000.0, room_nights=40)]  # prev ADR 50
    reps = [_rep_row(prop_id=1, reviews=10, avg_rating=4.5, response_rate=80.0)]
    prev_reps = [_rep_row(prop_id=1, reviews=10, avg_rating=4.0, response_rate=60.0)]

    # Competidores: 2 en Lima (ADR 80 y 120) y 1 en Cusco (ADR 200, ~570 km).
    all_hotels = [
        _hotel_row(prop_id=2, hotel_label="Hotel B", revenue=2400.0, room_nights=30,
                   city="Lima", city_lat=-12.0464, city_lng=-77.0428),   # ADR 80
        _hotel_row(prop_id=3, hotel_label="Hotel C", revenue=3600.0, room_nights=30,
                   city="Lima", city_lat=-12.0464, city_lng=-77.0428),   # ADR 120
        _hotel_row(prop_id=4, hotel_label="Hotel D", revenue=6000.0, room_nights=30,
                   city="Cusco", city_lat=-13.5319, city_lng=-71.9675),  # ADR 200, otra ciudad
    ]
    all_reps = [
        _rep_row(prop_id=2, reviews=10, avg_rating=4.0),
        _rep_row(prop_id=3, reviews=10, avg_rating=4.2),
        _rep_row(prop_id=4, reviews=10, avg_rating=4.8),
    ]

    p = _build_hotel_posicionamiento(
        reps, prev_reps, rows, prev,
        city="Lima", city_lat=-12.0464, city_lng=-77.0428,
        all_hotel_rows=all_hotels, all_rep_rows=all_reps,
    )
    assert p["rating"] == 4.5
    assert p["adr"] == 100.0
    assert p["adr_variacion"] == 100.0
    assert p["competitors"] == 2  # solo los 2 de Lima; Cusco queda fuera
    assert p["city"] == "Lima"
    assert p["radio_km"] == 5.0
    assert p["banda_precio"] == {"p25": 90.0, "p50": 100.0, "p75": 110.0}
    assert p["adr_percentile"] == 50.0   # 100 vs [80,120] → 1 de 2 por debajo
    assert p["rating_percentile"] == 100.0  # 4.5 vs [4.0,4.2] → todos por debajo
    assert p["precio_relativo_pct"] == 0.0  # (100/100 − 1)·100
    assert p["diagnosis"]
    assert p["decision"]


def test_hotel_posicionamiento_empty_state_honest() -> None:
    """Sin competidores con datos NO se inventa diagnosis/decision: estado
    vacío honesto (competitors=0, banda y percentiles None, textos vacíos)."""
    from src.app.modules.strategic.kpi_strategic import _build_hotel_posicionamiento

    rows = [_hotel_row(prop_id=1, revenue=3000.0, room_nights=30)]
    p = _build_hotel_posicionamiento(
        [], [], rows, [],
        city="Lima", city_lat=None, city_lng=None,
        all_hotel_rows=[], all_rep_rows=[],
    )
    assert p["competitors"] == 0
    assert p["city"] == "Lima"
    assert p["banda_precio"] is None
    assert p["adr_percentile"] is None
    assert p["rating_percentile"] is None
    assert p["precio_relativo_pct"] is None
    assert p["diagnosis"] == ""
    assert p["decision"] == ""
    # Sin coords propias ni competidores → sin marcadores para el mapa.
    assert p["own_lat"] is None
    assert p["own_lng"] is None
    assert p["competitors_markers"] == []


def test_hotel_posicionamiento_no_fabricated_coords() -> None:
    """Ciudad sin coordenadas en geo_catalog → ``radio_km`` es None (no se
    fabrica distancia), pero la agrupación por ciudad sigue funcionando."""
    from src.app.modules.strategic.kpi_strategic import _build_hotel_posicionamiento

    rows = [_hotel_row(prop_id=1, revenue=3000.0, room_nights=30)]
    all_hotels = [
        _hotel_row(prop_id=2, revenue=2400.0, room_nights=30, city="Lima",
                   city_lat=None, city_lng=None),  # ADR 80, mismo nombre de ciudad
    ]
    p = _build_hotel_posicionamiento(
        [], [], rows, [],
        city="Lima", city_lat=None, city_lng=None,
        all_hotel_rows=all_hotels, all_rep_rows=[],
    )
    assert p["competitors"] == 1
    assert p["radio_km"] is None
    assert p["banda_precio"]["p50"] == 80.0


def test_hotel_posicionamiento_radius_literal_with_hotel_coords() -> None:
    """Con coordenadas POR HOTEL el radio de 5 km es LITERAL: un competidor de
    la misma ciudad pero a >5 km queda fuera (Haversine, no el nombre de ciudad)."""
    from src.app.modules.strategic.kpi_strategic import _build_hotel_posicionamiento

    rows = [_hotel_row(prop_id=1, hotel_label="Hotel Lima", revenue=3000.0, room_nights=30)]
    all_hotels = [
        _hotel_row(prop_id=2, hotel_label="Hotel Cerca", revenue=2400.0, room_nights=30,
                   city="Lima", city_lat=-12.06, city_lng=-77.045),  # ~1.5 km → dentro
        _hotel_row(prop_id=3, hotel_label="Hotel Lejos", revenue=3600.0, room_nights=30,
                   city="Lima", city_lat=-12.12, city_lng=-77.03),   # ~8 km → fuera
    ]
    p = _build_hotel_posicionamiento(
        [], [], rows, [],
        city="Lima", city_lat=-12.0464, city_lng=-77.0428,
        all_hotel_rows=all_hotels, all_rep_rows=[],
    )
    assert p["competitors"] == 1  # solo el cercano; el lejano queda fuera del radio
    assert p["banda_precio"]["p50"] == 80.0  # ADR del único competidor dentro del radio


def test_hotel_posicionamiento_exposes_map_markers() -> None:
    """IE-H02 expone ``own_lat``/``own_lng`` y la lista de competidores con
    coords para el mapa competitivo, ordenados por distancia ascendente."""
    from src.app.modules.strategic.kpi_strategic import _build_hotel_posicionamiento

    rows = [_hotel_row(prop_id=1, hotel_label="Hotel Lima", revenue=3000.0, room_nights=30)]
    all_hotels = [
        _hotel_row(prop_id=2, hotel_label="Hotel Cerca", revenue=2400.0, room_nights=30,
                   city="Lima", city_lat=-12.06, city_lng=-77.045),   # ~1.5 km
        _hotel_row(prop_id=3, hotel_label="Hotel Medio", revenue=3600.0, room_nights=30,
                   city="Lima", city_lat=-12.08, city_lng=-77.04),    # ~3.7 km
    ]
    p = _build_hotel_posicionamiento(
        [], [], rows, [],
        city="Lima", city_lat=-12.0464, city_lng=-77.0428,
        all_hotel_rows=all_hotels, all_rep_rows=[],
    )
    assert p["own_lat"] == -12.0464
    assert p["own_lng"] == -77.0428
    markers = p["competitors_markers"]
    assert len(markers) == 2
    # Ordenados por distancia ascendente (el más cercano primero).
    assert markers[0]["prop_id"] == 2
    assert markers[0]["hotel_label"] == "Hotel Cerca"
    assert markers[0]["lat"] == -12.06
    assert markers[0]["lng"] == -77.045
    assert markers[0]["adr"] == 80.0
    assert markers[0]["distance_km"] is not None
    assert markers[1]["prop_id"] == 3
    assert markers[0]["distance_km"] < markers[1]["distance_km"]


def test_hotel_serie_monthly_and_planes_paginated() -> None:
    from src.app.modules.strategic.kpi_strategic import (
        _build_hotel_serie,
        _build_planes,
    )

    rows = [
        _hotel_row(month="2026-07-01", revenue=3000.0, room_nights=30, total_rooms=2),
        _hotel_row(month="2026-08-01", revenue=3100.0, room_nights=31, total_rooms=2),
    ]
    serie = _build_hotel_serie(rows)
    assert serie["labels"] == ["2026-07-01", "2026-08-01"]
    datasets = {d["label"]: d["data"] for d in serie["datasets"]}
    assert datasets["Revenue neto (USD)"] == [3000.0, 3100.0]
    assert len(datasets["Ocupación (%)"]) == 2

    plans = [
        _plan_row(room_type_label="Estándar", revenue=1000.0),
        _plan_row(room_type_label="Suite", revenue=2500.0),
    ]
    pag = _build_planes(plans, page=1, page_size=1)
    assert pag["total"] == 2
    assert pag["rows"][0]["label"] == "Suite"
    assert pag["has_next"] is True


# ─── IE-G02 — Rankings estratégicos (R-G01..R-G06) ────────────────────────

def test_rankings_groups_rg01_to_rg06_present() -> None:
    """IE-G02 (TAF14 §5): los 6 rankings dictados existen como grupos con
    código, título, criterio y filas (entidad/valor/variación/motivo/decisión)."""
    from src.app.modules.strategic.kpi_strategic import _build_rankings

    rows = [
        _hotel_row(prop_id=1, hotel_label="Hotel A", revenue=3000.0, room_nights=30),
        _hotel_row(prop_id=2, hotel_label="Hotel B", revenue=1000.0, room_nights=10),
    ]
    prev = [
        _hotel_row(prop_id=1, revenue=2000.0),
        _hotel_row(prop_id=2, revenue=1500.0),
    ]
    plans = [_plan_row(room_type_label="Estándar", revenue=2000.0)]
    reps = [_rep_row(prop_id=1, reviews=10, avg_rating=4.8, response_rate=90.0)]
    prev_reps = [_rep_row(prop_id=1, reviews=10, avg_rating=4.0, response_rate=60.0)]
    markets = [_market_row(destination_label="Cusco", revenue_usd=500.0)]
    prev_markets = [_market_row(destination_label="Cusco", revenue_usd=300.0)]

    built = _build_rankings(rows, prev, plans, reps, prev_reps, markets, prev_markets)
    groups = built["groups"]
    assert built["kpis"] and built["series"]["labels"]
    codes = [g["codigo"] for g in groups]
    assert codes == ["R-G01", "R-G02", "R-G03", "R-G04", "R-G05", "R-G06"]
    for g in groups:
        assert g["titulo"]
        assert g["criterio"]
        assert isinstance(g["rows"], list)
        assert g["rows"][0]["entidad"]
        assert "motivo" in g["rows"][0]
        assert "decision" in g["rows"][0]


def test_rankings_rg01_leaders_by_revenue_and_rg02_opportunity() -> None:
    """R-G01 ordena por revenue desc (líderes); R-G02 por crecimiento de
    revenue vs período anterior (oportunidad)."""
    from src.app.modules.strategic.kpi_strategic import _build_rankings

    rows = [
        _hotel_row(prop_id=1, hotel_label="Hotel A", revenue=3000.0, room_nights=30),
        _hotel_row(prop_id=2, hotel_label="Hotel B", revenue=1000.0, room_nights=10),
        _hotel_row(prop_id=3, hotel_label="Hotel C", revenue=2000.0, room_nights=20),
    ]
    prev = [
        _hotel_row(prop_id=1, revenue=2000.0),   # A crece 50%
        _hotel_row(prop_id=2, revenue=900.0),    # B crece 11%
        _hotel_row(prop_id=3, revenue=2800.0),   # C cae -28%
    ]
    built = _build_rankings(rows, prev, [], [], [], [], [])
    by_code = {g["codigo"]: g for g in built["groups"]}

    rg01 = by_code["R-G01"]
    assert [r["entidad"] for r in rg01["rows"]] == ["Hotel A", "Hotel C", "Hotel B"]
    assert rg01["rows"][0]["valor"] == 3000.0

    rg02 = by_code["R-G02"]
    assert rg02["rows"][0]["entidad"] == "Hotel A"  # mayor crecimiento
    assert rg02["rows"][0]["variacion"] == 50.0


def test_rankings_rg03_risk_and_rg06_reputation() -> None:
    """R-G03 = hoteles con caída (riesgo); R-G06 = reputación ponderada."""
    from src.app.modules.strategic.kpi_strategic import _build_rankings

    rows = [
        _hotel_row(prop_id=1, hotel_label="Hotel A", revenue=3000.0, room_nights=30),
        _hotel_row(prop_id=2, hotel_label="Hotel B", revenue=1000.0, room_nights=10),
    ]
    prev = [
        _hotel_row(prop_id=1, revenue=2000.0),
        _hotel_row(prop_id=2, revenue=2000.0),  # B cae 50%
    ]
    reps = [
        _rep_row(prop_id=1, reviews=10, avg_rating=4.8, response_rate=90.0),
        _rep_row(prop_id=2, reviews=10, avg_rating=4.1, response_rate=50.0),
    ]
    built = _build_rankings(rows, prev, [], reps, [], [], [])
    by_code = {g["codigo"]: g for g in built["groups"]}

    rg03 = by_code["R-G03"]
    assert rg03["rows"][0]["entidad"] == "Hotel B"  # mayor caída
    assert rg03["rows"][0]["variacion"] == -50.0

    rg06 = by_code["R-G06"]
    assert rg06["rows"][0]["entidad"] == "Hotel A"  # mejor rating


def test_rankings_rg04_markets_and_rg05_plans() -> None:
    """R-G04 = mercados por revenue; R-G05 = planes por revenue neto."""
    from src.app.modules.strategic.kpi_strategic import _build_rankings

    markets = [
        _market_row(destination_label="Cusco", revenue_usd=800.0),
        _market_row(destination_label="Lima", revenue_usd=400.0),
    ]
    plans = [
        _plan_row(room_type_label="Suite", revenue=2500.0),
        _plan_row(room_type_label="Estándar", revenue=1000.0),
    ]
    built = _build_rankings([], [], plans, [], [], markets, [])
    by_code = {g["codigo"]: g for g in built["groups"]}

    rg04 = by_code["R-G04"]
    assert rg04["rows"][0]["entidad"] == "Cusco"
    assert rg04["rows"][0]["valor"] == 800.0

    rg05 = by_code["R-G05"]
    assert rg05["rows"][0]["entidad"] == "Suite"
    assert rg05["rows"][0]["valor"] == 2500.0


# ─── Vista A — IE-H02 posicionamiento como patrón Z ─────────────────────

def test_posicionamiento_serie_and_rows_z_pattern() -> None:
    """IE-H02 (posicionamiento) ahora es un bloque Z: serie mensual
    (rating/ADR) + tabla de registros por mes — no solo un aside."""
    from src.app.modules.strategic.kpi_strategic import (
        _build_posicionamiento_rows,
        _build_posicionamiento_serie,
    )

    reps = [
        _rep_row(month="2026-07-01", reviews=10, avg_rating=4.5, response_rate=80.0),
        _rep_row(month="2026-08-01", reviews=10, avg_rating=4.3, response_rate=50.0),
    ]
    rows = [
        _hotel_row(month="2026-07-01", revenue=3000.0, room_nights=30, total_rooms=2),
        _hotel_row(month="2026-08-01", revenue=3100.0, room_nights=31, total_rooms=2),
    ]
    serie = _build_posicionamiento_serie(reps, rows)
    assert serie["labels"] == ["2026-07-01", "2026-08-01"]
    datasets = {d["label"]: d["data"] for d in serie["datasets"]}
    assert datasets["Rating"] == [4.5, 4.3]
    assert datasets["ADR (USD)"] == [100.0, 100.0]

    monthly = _build_posicionamiento_rows(reps, rows)
    assert len(monthly) == 2
    latest = monthly[0]  # más reciente primero
    assert latest["month"] == "2026-08-01"
    assert latest["rating"] == 4.3
    assert latest["adr"] == 100.0
    assert latest["respuesta"] == 50.0


# ─── Vista B — cartera (IE-G03) ───────────────────────────────────────────

def test_cartera_summary_kpis() -> None:
    """KPIs de la cartera agregando todas las filas de strat_hotel_monthly."""
    from src.app.modules.strategic.kpi_strategic import _build_cartera_summary

    rows = [
        _hotel_row(prop_id=1, revenue=3000.0, room_nights=30, bookings=10, total_rooms=2),
        _hotel_row(prop_id=2, hotel_label="Hotel B", revenue=1000.0, room_nights=10,
                   bookings=4, total_rooms=1),
    ]
    prev = [
        _hotel_row(prop_id=1, revenue=2000.0),
        _hotel_row(prop_id=2, hotel_label="Hotel B", revenue=800.0),
    ]
    reps = [_rep_row(prop_id=1, reviews=10, avg_rating=4.5, response_rate=80.0)]

    s = _build_cartera_summary(rows, prev, reps, [])
    by_id = {k["id"]: k for k in s["kpis"]}
    assert s["hoteles"] == 2
    assert by_id["revenue"]["value"] == 4000.0
    assert by_id["revenue"]["pct_change"] == round((4000 - 2800) / 2800 * 100, 2)  # 42.86
    assert by_id["adr"]["value"] == 100.0  # 4000 / 40 noches
    assert by_id["rating"]["value"] == 4.5
    assert by_id["bookings"]["value"] == 14


def test_cartera_rows_bruto_neto_descuento_sorted() -> None:
    from src.app.modules.strategic.kpi_strategic import _build_cartera_rows

    rows = [
        _hotel_row(prop_id=1, hotel_label="Hotel A", revenue=3000.0, discount_amount=300.0,
                   room_nights=30, bookings=10, total_rooms=2),
        _hotel_row(prop_id=2, hotel_label="Hotel B", revenue=1000.0, discount_amount=100.0,
                   room_nights=10, bookings=4, total_rooms=1),
        _hotel_row(prop_id=3, hotel_label="Hotel C", revenue=500.0, discount_amount=0.0,
                   room_nights=5, bookings=2, total_rooms=1),
    ]
    items = _build_cartera_rows(rows, [])
    assert len(items) == 3
    first = items[0]  # ordenado por revenue neto desc → Hotel A
    assert first["prop_id"] == 1
    assert first["hotel_label"] == "Hotel A"
    assert first["revenue_bruto"] == 3300.0
    assert first["revenue_neto"] == 3000.0
    assert first["descuento"] == 300.0
    assert first["descuento_pct"] == round(300 / 3300 * 100, 2)
    assert first["adr"] == 100.0


def test_cartera_series_monthly_revenue_and_occupancy() -> None:
    from src.app.modules.strategic.kpi_strategic import _build_cartera_series

    rows = [
        _hotel_row(month="2026-07-01", revenue=3000.0, room_nights=30, total_rooms=2),
        _hotel_row(month="2026-08-01", revenue=3100.0, room_nights=31, total_rooms=2),
    ]
    series = _build_cartera_series(rows)
    assert series["labels"] == ["2026-07-01", "2026-08-01"]
    datasets = {d["label"]: d["data"] for d in series["datasets"]}
    assert datasets["Revenue neto (USD)"] == [3000.0, 3100.0]
    assert len(datasets["Ocupación (%)"]) == 2


def test_cartera_rows_variacion_vs_previous() -> None:
    from src.app.modules.strategic.kpi_strategic import _build_cartera_rows

    rows = [_hotel_row(prop_id=1, revenue=3000.0, room_nights=30)]
    prev = [_hotel_row(prop_id=1, revenue=2000.0, room_nights=20)]
    items = _build_cartera_rows(rows, prev)
    assert items[0]["variacion"] == 50.0


# ─── Mercados (IE-G04) ────────────────────────────────────────────────────

def test_markets_summary_series_rows() -> None:
    """Mercados compuesto: KPIs de demanda + serie + tabla con cuadrante."""
    from src.app.modules.strategic.kpi_strategic import _build_markets

    rows = [
        _market_row(destination_label="Cusco", revenue_usd=8000.0, searches=1000, clicks=300, reservations=80),
        _market_row(destination_label="Lima", revenue_usd=1000.0, searches=500, clicks=100, reservations=10),
        _market_row(destination_label="Arequipa", revenue_usd=1500.0, searches=200, clicks=50, reservations=5),
        _market_row(destination_label="Iquitos", revenue_usd=300.0, searches=50, clicks=10, reservations=1),
    ]
    prev = [
        _market_row(destination_label="Cusco", revenue_usd=6000.0, searches=900, reservations=60),
        _market_row(destination_label="Lima", revenue_usd=750.0, searches=400, reservations=8),
        _market_row(destination_label="Arequipa", revenue_usd=2000.0, searches=300, reservations=8),
        _market_row(destination_label="Iquitos", revenue_usd=400.0, searches=60, reservations=1),
    ]
    m = _build_markets(rows, prev)
    by_id = {k["id"]: k for k in m["summary"]["kpis"]}
    assert by_id["searches"]["value"] == 1750
    assert by_id["reservations"]["value"] == 96
    assert by_id["revenue"]["value"] == 10800.0
    assert by_id["conversion"]["value"] == round(96 / 1750 * 100, 2)

    by_dest = {item["destination"]: item for item in m["rows"]}
    assert by_dest["Cusco"]["quadrant"] == "estrella"
    assert by_dest["Lima"]["quadrant"] == "oportunidad"
    assert by_dest["Arequipa"]["quadrant"] == "consolidacion"
    assert by_dest["Iquitos"]["quadrant"] == "riesgo"
    assert m["rows"][0]["destination"] == "Cusco"  # ordenado por revenue
    assert m["series"]["labels"]


# ─── Response models (composite, sin BSC) ─────────────────────────────────

def test_portfolio_response_model_validates_composite() -> None:
    """Regresión: el response model de la cartera valida el contrato compuesto
    (summary.kpis + series + rows) + rankings IE-G02."""
    from src.app.modules.strategic.kpi_strategic import (
        _build_cartera_rows,
        _build_cartera_series,
        _build_cartera_summary,
        _build_planes,
        _build_rankings,
    )
    from src.app.modules.strategic.schemas import StrategicPortfolioResponse

    rows = [_hotel_row(prop_id=1, revenue=3000.0, discount_amount=300.0,
                       room_nights=30, bookings=10, total_rooms=2)]
    raw = {
        "available": True,
        "source": "clickhouse",
        "date_from": "2026-07-01",
        "date_to": "2026-07-31",
        "prop_id": None,
        "summary": _build_cartera_summary(rows, [], [], []),
        "series": _build_cartera_series(rows),
        "rows": _build_cartera_rows(rows, [])[:1],
        "planes": _build_planes([_plan_row()], page=1, page_size=20),
        "rankings": _build_rankings(rows, [], [], [], [], [], []),
        "total": 1, "page": 1, "page_size": 20, "total_pages": 1,
        "has_next": False, "has_prev": False,
    }
    model = StrategicPortfolioResponse.model_validate(raw)
    assert model.summary.hoteles == 1
    assert len(model.summary.kpis) >= 10
    assert model.rows[0].revenue_neto == 3000.0
    assert model.planes.total == 1
    assert len(model.rankings.groups) == 6  # IE-G02: R-G01..R-G06


def test_hotel_response_model_validates_composite() -> None:
    from src.app.modules.strategic.kpi_strategic import (
        _build_hotel_kpis,
        _build_hotel_posicionamiento,
        _build_hotel_rows,
        _build_hotel_serie,
        _build_planes,
    )
    from src.app.modules.strategic.schemas import StrategicHotelResponse

    rows = [_hotel_row(revenue=3000.0, room_nights=30, bookings=10, total_rooms=2)]
    raw = {
        "available": True,
        "source": "clickhouse",
        "date_from": "2026-07-01",
        "date_to": "2026-07-31",
        "prop_id": 1,
        "summary": {
            "kpis": _build_hotel_kpis(rows, [], [], []),
            "posicionamiento": _build_hotel_posicionamiento([], [], rows, []),
        },
        "serie": _build_hotel_serie(rows),
        "rows": _build_hotel_rows(rows)[:1],
        "planes": _build_planes([_plan_row()], page=1, page_size=20),
        "total": 1, "page": 1, "page_size": 20, "total_pages": 1,
        "has_next": False, "has_prev": False,
    }
    model = StrategicHotelResponse.model_validate(raw)
    assert len(model.summary.kpis) >= 10
    assert model.summary.posicionamiento is not None
    assert model.rows[0].revenue_neto == 3000.0
    assert model.planes.total == 1


def test_markets_response_model_validates_composite() -> None:
    from src.app.modules.strategic.kpi_strategic import _build_markets
    from src.app.modules.strategic.schemas import StrategicMarketsResponse

    rows = [_market_row(destination_label="Cusco", searches=100, reservations=5, revenue_usd=500.0)]
    m = _build_markets(rows, [])
    raw = {
        "available": True,
        "source": "clickhouse",
        "date_from": "2026-07-01",
        "date_to": "2026-07-31",
        "prop_id": None,
        "summary": m["summary"],
        "series": m["series"],
        "rows": m["rows"][:1],
        "total": 1, "page": 1, "page_size": 20, "total_pages": 1,
        "has_next": False, "has_prev": False,
    }
    model = StrategicMarketsResponse.model_validate(raw)
    assert len(model.summary.kpis) >= 4
    assert model.rows[0].destination == "Cusco"


# ─── Validación de rango ──────────────────────────────────────────────────

def test_validate_range_rejects_inverted() -> None:
    from src.app.modules.strategic.kpi_strategic import _validate_range

    with pytest.raises(ValueError):
        _validate_range("2026-08-02", "2026-08-01", 180)


def test_validate_range_defaults_to_days() -> None:
    from src.app.modules.strategic.kpi_strategic import _validate_range

    start, end = _validate_range(None, None, 90)
    assert end >= start


def test_default_range_is_month_aligned() -> None:
    """El rango por defecto (sin date_from/date_to) debe alinearse al primer
    día del mes: los datos strat_* son de granularidad mensual, así que una
    ventana empezada a mitad de mes hace que su ventana anterior no calce con
    la fila del mes previo y toda comparación dé "sin comparación" aunque
    existan datos."""
    from src.app.modules.strategic.kpi_strategic import _validate_range

    start, _ = _validate_range(None, None, 30)
    assert start.day == 1


def test_prev_window_aligns_to_months() -> None:
    """La ventana anterior debe cubrir los MISMOS meses calendario, cerrados
    al mes del inicio. La versión previa restaba días exactos (para un rango
    que arranca 01-ago buscaba 09-jul→31-jul) y perdía la fila del mes
    anterior (2026-07-01), por lo que toda comparación quedaba vacía."""
    from datetime import date
    from src.app.modules.strategic.kpi_strategic import _prev_window

    # Mensual: [01-ago → hoy] compara contra julio completo [01-07 → 31-07]
    assert _prev_window(date(2026, 8, 1), date(2026, 8, 23)) == (date(2026, 7, 1), date(2026, 7, 31))
    # Trimestral: [01-jun → hoy] compara contra [01-mar → 31-may]
    assert _prev_window(date(2026, 6, 1), date(2026, 8, 23)) == (date(2026, 3, 1), date(2026, 5, 31))
    # Anual: [01-sep-25 → hoy] compara contra [01-sep-24 → 31-ago-25]
    assert _prev_window(date(2025, 9, 1), date(2026, 8, 23)) == (date(2024, 9, 1), date(2025, 8, 31))


def test_month_aligned_prev_yields_real_comparison() -> None:
    """Regresión del caso real del hotel: con filas mensuales del mes actual y
    del mes anterior, la comparación debe ser real (has_prev True, variación
    ≠ 0) — es lo que hace que el KPI deje de mostrar "sin comparación"."""
    from src.app.modules.strategic.kpi_strategic import _build_hotel_kpis

    current = [_hotel_row(month="2026-08-01", revenue=1504.0, room_nights=16,
                          bookings=3, total_rooms=2)]
    prev = [_hotel_row(month="2026-07-01", revenue=812.3, room_nights=6,
                       bookings=6, total_rooms=2)]
    kpis = {k["id"]: k for k in _build_hotel_kpis(current, prev, [], [])}
    assert kpis["revenue"]["has_prev"] is True
    assert kpis["revenue"]["pct_change"] == round((1504.0 - 812.3) / 812.3 * 100, 2)
    assert kpis["bookings"]["has_prev"] is True


# ─── Gate de permiso (frontera de seguridad) ──────────────────────────────

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _make_user(db, username: str, role: str) -> None:
    db.users.insert_one(
        {
            "username": username,
            "email": f"{username}@example.com",
            "display_name": username.replace("_", " ").title(),
            "password_hash": _pwd.hash("TestPass123!"),
            "primary_role": role,
            "is_active": True,
        }
    )


@pytest.mark.asyncio
async def test_strategic_requires_fine_permission(client, db) -> None:
    """Rol con reports.read (grueso) pero sin reports.strategic.read → 403."""
    db.roles.insert_one(
        {"role_name": "role_strategic_coarse", "display_name": "Coarse",
         "permissions": ["reports.read"], "is_system": True}
    )
    _make_user(db, "user_strategic_coarse", "role_strategic_coarse")
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "user_strategic_coarse", "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/strategic/portfolio")
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_strategic_fine_permission_grants_access_and_response_models(client, db) -> None:
    """Con reports.strategic.portfolio.read (Vista B) el endpoint responde 200
    y el body valida contra los modelos Pydantic *Response (aunque ClickHouse
    esté caído devuelve available:false, nunca 500)."""
    from src.app.modules.strategic.schemas import (
        StrategicMarketsResponse,
        StrategicPortfolioResponse,
    )

    db.roles.insert_one(
        {"role_name": "role_strategic_fine", "display_name": "Fine",
         "permissions": ["reports.strategic.portfolio.read"], "is_system": True}
    )
    _make_user(db, "user_strategic_fine", "role_strategic_fine")
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "user_strategic_fine", "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/strategic/portfolio")
    assert resp.status_code == 200, resp.text
    StrategicPortfolioResponse.model_validate(resp.json())

    resp = await client.get("/api/strategic/markets")
    assert resp.status_code == 200, resp.text
    StrategicMarketsResponse.model_validate(resp.json())


@pytest.mark.asyncio
async def test_strategic_page_size_minimum_5(client, db) -> None:
    """Mínimo de 5 elementos por página en las tablas estratégicas: pedir
    ``page_size`` menor que 5 es rechazado (422), y 5 (o más) responde 200.
    Así la última tabla de registros no termina oculta en una página minúscula."""
    db.roles.insert_one(
        {"role_name": "role_strategic_pagesize", "display_name": "PageSize",
         "permissions": ["reports.strategic.portfolio.read"], "is_system": True}
    )
    _make_user(db, "user_strategic_pagesize", "role_strategic_pagesize")
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "user_strategic_pagesize", "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/strategic/portfolio?page_size=2")
    assert resp.status_code == 422, resp.text  # por debajo del mínimo 5

    resp = await client.get("/api/strategic/portfolio?page_size=5")
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_vista_separation_permissions_do_not_cross(client, db) -> None:
    """Separación por permiso (bug 'botones que no abren'): el permiso de
    Vista A (reports.strategic.read, dueño de hotel) NO abre la cartera Vista
    B (portfolio/markets → 403); el de cartera (reports.strategic.portfolio.
    read) tampoco abre la Vista A (hotel → 403). Los botones de SISTEMA solo
    aparecen con el permiso de cartera."""
    db.roles.insert_one(
        {"role_name": "role_vista_a_only", "display_name": "Vista A only",
         "permissions": ["reports.strategic.read"], "is_system": True}
    )
    _make_user(db, "user_vista_a_only", "role_vista_a_only")
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "user_vista_a_only", "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text

    # Vista A abre, Vista B NO.
    resp = await client.get("/api/strategic/hotel/1")
    assert resp.status_code == 404, resp.text  # sin assigned_hotels → deny-by-default, NO 403
    resp = await client.get("/api/strategic/portfolio")
    assert resp.status_code == 403, resp.text
    resp = await client.get("/api/strategic/markets")
    assert resp.status_code == 403, resp.text

    # Rol de cartera: Vista B abre, Vista A NO.
    db.roles.insert_one(
        {"role_name": "role_vista_b_only", "display_name": "Vista B only",
         "permissions": ["reports.strategic.portfolio.read"], "is_system": True}
    )
    _make_user(db, "user_vista_b_only", "role_vista_b_only")
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "user_vista_b_only", "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/strategic/portfolio")
    assert resp.status_code == 200, resp.text
    resp = await client.get("/api/strategic/hotel/1")
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_hotel_scope_deny_by_default(client, db) -> None:
    """Un rol restringido (gerente_hotel) sin assigned_hotels NO ve ningún
    hotel de la Vista A (deny-by-default → 404)."""
    db.roles.insert_one(
        {"role_name": "role_strategic_gerente", "display_name": "Gerente",
         "permissions": ["reports.strategic.read"], "is_system": True}
    )
    _make_user(db, "user_strategic_gerente", "role_strategic_gerente")
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "user_strategic_gerente", "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/strategic/hotel/1")
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_hotel_scope_assigned_hotel_ok_outside_404(client, db) -> None:
    """Con assigned_hotels=[1]: /hotel/1 → 200, /hotel/2 → 404 y el
    drill-down de la cartera (portfolio?prop_id=2) también queda fuera."""
    from src.app.modules.strategic.schemas import StrategicHotelResponse

    db.roles.insert_one(
        {"role_name": "role_strategic_gerente_asignado", "display_name": "Gerente",
         "permissions": ["reports.strategic.read", "reports.strategic.portfolio.read"], "is_system": True}
    )
    _make_user(db, "user_strategic_gerente_asig", "role_strategic_gerente_asignado")
    db.users.update_one(
        {"username": "user_strategic_gerente_asig"},
        {"$set": {"assigned_hotels": [1]}},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "user_strategic_gerente_asig", "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/strategic/hotel/1")
    assert resp.status_code == 200, resp.text
    StrategicHotelResponse.model_validate(resp.json())

    resp = await client.get("/api/strategic/hotel/2")
    assert resp.status_code == 404, resp.text

    resp = await client.get("/api/strategic/portfolio", params={"prop_id": 2})
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_hotel_unfiltered_role_any_hotel(client, db) -> None:
    """super_admin (rol no filtrado) accede a cualquier hotel de la Vista A."""
    db.roles.insert_one(
        {"role_name": "super_admin", "display_name": "Super Admin",
         "permissions": ["reports.strategic.read"], "is_system": True}
    )
    _make_user(db, "user_strategic_super", "super_admin")
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "user_strategic_super", "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/strategic/hotel/1")
    assert resp.status_code == 200, resp.text


@pytest.mark.integration
def test_portfolio_real_clickhouse() -> None:
    """Integración: /portfolio responde compuesto (summary + cartera) si CH está arriba."""
    from src.app.modules.strategic.kpi_strategic import get_portfolio_dashboard

    try:
        result = get_portfolio_dashboard(days=180)
    except Exception as exc:  # noqa: BLE001 - pragma: no cover; ClickHouse opcional
        pytest.skip(f"ClickHouse no disponible: {exc}")
    if not result["available"]:
        pytest.skip(f"Tablas strat_* aún no cargadas en ClickHouse: {result.get('message', '')[:120]}")
    assert result["summary"]["kpis"]
    assert "rows" in result
