"""Tests del servicio de geocodificación Nominatim (OpenStreetMap).

Cubren las piezas puras (clave de caché, parseo de resultados) y el
orquestador ``geocode`` con cliente y caché inyectables — sin red real ni
depender de Nominatim. La política de uso (≤1 req/s) se anula en los tests
para no dormir; la separación mínima real se valida por diseño (constante
``NOMINATIM_MIN_INTERVAL``).
"""

from __future__ import annotations

import pytest

from src.app.modules.geocoding import service as geocode_service


@pytest.fixture(autouse=True)
def _no_rate_limit(monkeypatch):
    monkeypatch.setattr(geocode_service, "NOMINATIM_MIN_INTERVAL", 0.0)
    monkeypatch.setattr(geocode_service, "_last_request_at", 0.0)


class _FakeCollection:
    def __init__(self):
        self.docs = {}

    def find_one(self, query, projection=None):
        return self.docs.get(query.get("query_key"))

    def replace_one(self, query, doc, upsert=False):
        self.docs[query["query_key"]] = dict(doc)


class _FakeDb:
    def __init__(self):
        self._cols = {}

    def __getitem__(self, name):
        if name not in self._cols:
            self._cols[name] = _FakeCollection()
        return self._cols[name]


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        return _FakeResponse(self._payload)


class _BoomClient:
    def get(self, *args, **kwargs):
        raise RuntimeError("offline")


def test_query_key_normalizes():
    key = geocode_service._query_key("  Av. Tulum 5 ", "Cancún", " México ")
    assert key == "av. tulum 5 cancún méxico"
    assert geocode_service._query_key("", "", "") == ""


def test_parse_result_extracts_lat_lng():
    out = geocode_service._parse_result(
        [{"lat": "21.1619", "lon": "-86.8515", "display_name": "Cancún, MX"}]
    )
    assert out == {"latitude": 21.1619, "longitude": -86.8515, "display_name": "Cancún, MX"}


def test_parse_result_none_for_empty_or_bad():
    assert geocode_service._parse_result([]) is None
    assert geocode_service._parse_result(None) is None
    assert geocode_service._parse_result([{"foo": "bar"}]) is None
    assert geocode_service._parse_result("not-a-list") is None


def test_geocode_returns_none_on_network_error():
    assert geocode_service.geocode("X", city="Y", client=_BoomClient(), db=_FakeDb()) is None


def test_geocode_caches_and_reuses():
    client = _FakeClient([{"lat": "21.1619", "lon": "-86.8515", "display_name": "Cancún"}])
    db = _FakeDb()
    r1 = geocode_service.geocode("", city="Cancún", country="México", client=client, db=db)
    r2 = geocode_service.geocode("", city="Cancún", country="México", client=client, db=db)
    assert r1 == {"latitude": 21.1619, "longitude": -86.8515, "display_name": "Cancún"}
    assert r2 == r1
    assert client.calls == 1  # la 2ª llamada sirve de la caché


def test_geocode_returns_none_for_empty_result():
    client = _FakeClient([])
    db = _FakeDb()
    assert geocode_service.geocode("Z", city="Q", client=client, db=db) is None
    assert client.calls == 1


def test_geocode_returns_none_for_blank_query():
    # Sin address/city/country no hay qué consultar (ni se toca la red).
    client = _FakeClient([])
    assert geocode_service.geocode("", client=client, db=_FakeDb()) is None
    assert client.calls == 0
