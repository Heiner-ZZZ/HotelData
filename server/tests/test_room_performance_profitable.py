"""Filtro ``only_profitable`` del dashboard ADR (R1.2).

La grilla diaria mezcla filas con revenue 0 (inventario sin ventas) y filas
con ventas reales. El usuario necesita aislar "los días que sí tuvieron
ganancias" por tipo de habitación. Igual que los filtros de tipo/canal, el
filtro afecta SOLO la grilla paginada: resumen y serie siguen reflejando el
rango completo.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from src.app.modules.revenue.services.analytics import get_room_performance_dashboard


def _fake_rows() -> list[tuple]:
    """Dos días × dos tipos: solo el Deluxe del día 2 tiene revenue."""
    d1 = date.today().isoformat()
    d2 = (date.today() + timedelta(days=1)).isoformat()
    cols = ("date", "prop_id", "hotel_label", "room_type_id", "room_type_label",
            "currency", "booking_source", "rooms_sold", "room_nights", "revenue",
            "cancelled_rooms", "available_rooms", "blocked_rooms", "total_rooms",
            "published_rate", "rate_variance")
    rows = [
        # d1 Standard: inventario sin ventas
        (d1, 1, "Hotel Lima Centro", "RT-1-STD", "Habitación Standard", "USD",
         "", 0, 0, 0.0, 0, 2, 0, 2, None, 0.0),
        # d1 Deluxe: inventario sin ventas
        (d1, 1, "Hotel Lima Centro", "RT-1-DLX", "Habitación Deluxe", "USD",
         "", 0, 0, 0.0, 0, 2, 0, 2, None, 0.0),
        # d2 Standard: sigue sin ventas
        (d2, 1, "Hotel Lima Centro", "RT-1-STD", "Habitación Standard", "USD",
         "", 0, 0, 0.0, 0, 2, 0, 2, None, 0.0),
        # d2 Deluxe: ¡venta real!
        (d2, 1, "Hotel Lima Centro", "RT-1-DLX", "Habitación Deluxe", "USD",
         "", 1, 1, 150.0, 0, 2, 0, 2, 160.0, -6.25),
    ]
    return [dict(zip(cols, r)) for r in rows]


class _FakeResult:
    def __init__(self, rows: list[dict]) -> None:
        self.result_rows = [tuple(r.values()) for r in rows]


class _FakeClient:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self.queries: list[str] = []

    def query(self, query: str, parameters=None):  # noqa: ANN001
        self.queries.append(query)
        return _FakeResult(self._rows)

    def close(self) -> None:
        pass


@pytest.fixture()
def fake_clickhouse(monkeypatch):
    client = _FakeClient(_fake_rows())
    # El servicio hace ``import clickhouse_connect`` DENTRO de la función:
    # parchar el atributo del módulo no alcanza — hay que sustituir la entrada
    # en sys.modules para que el import resuelva al doble.
    monkeypatch.setitem(sys.modules, "clickhouse_connect", SimpleNamespace(get_client=lambda **kw: client))
    return client


def test_sin_filtro_incluye_filas_sin_revenue(fake_clickhouse):
    out = get_room_performance_dashboard(prop_id=1, days=7)

    assert out["available"] is True
    assert out["total"] == 4
    assert all("revenue" in row for row in out["rows"])


def test_only_profitable_deja_solo_dias_con_ganancias(fake_clickhouse):
    out = get_room_performance_dashboard(prop_id=1, days=7, only_profitable=True)

    assert out["available"] is True
    assert out["total"] == 1
    assert len(out["rows"]) == 1
    row = out["rows"][0]
    assert float(row["revenue"]) > 0
    assert row["room_type_label"] == "Habitación Deluxe"


def test_only_profitable_no_afecta_resumen_ni_serie(fake_clickhouse):
    filtered = get_room_performance_dashboard(prop_id=1, days=7, only_profitable=True)
    unfiltered = get_room_performance_dashboard(prop_id=1, days=7)

    # El resumen refleja el rango completo en ambos casos.
    assert filtered["summary"]["revenue"] == unfiltered["summary"]["revenue"]
    assert filtered["summary"]["room_nights"] == unfiltered["summary"]["room_nights"]
    assert filtered["series"] == unfiltered["series"]
