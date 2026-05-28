from __future__ import annotations

from src.etl.transform_collections import _split_multi_value


def test_split_multi_value_normalizes_delimiters():
    assert _split_multi_value("Wifi; Breakfast, Parking") == ["Breakfast", "Parking", "Wifi"]


def test_split_multi_value_ignores_empty_values():
    assert _split_multi_value("Wifi;; ") == ["Wifi"]
