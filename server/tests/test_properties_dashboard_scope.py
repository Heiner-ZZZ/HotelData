"""Scope of ``properties_dashboard``: a restricted role (gerente) must only
see its own assigned properties, never the whole catalog.

Regression: ``properties_dashboard`` called ``list_partner_hotels`` twice —
the second call without ``user`` overwrote the filtered list and returned
every hotel to every manager.
"""
from __future__ import annotations

from src.app.modules.partner.services.dashboard.main import properties_dashboard


def _prop_ids(result: dict) -> list[int]:
    return [item["prop_id"] for item in result["properties"]["items"]]


def test_dashboard_only_returns_assigned_hotels_for_restricted_user(db):
    db.dim_hotels.insert_many(
        [
            {"prop_id": 1, "hotel_name": "Hotel Uno", "display_name": "Hotel Uno"},
            {"prop_id": 2, "hotel_name": "Hotel Dos", "display_name": "Hotel Dos"},
            {"prop_id": 3, "hotel_name": "Hotel Tres", "display_name": "Hotel Tres"},
        ]
    )
    gerente = {
        "username": "gerente_lima",
        "primary_role": "gerente",
        "assigned_hotels": [1],
    }

    result = properties_dashboard(page=1, page_size=10, user=gerente)

    assert _prop_ids(result) == [1]
    assert result["properties"]["total"] == 1


def test_dashboard_returns_all_hotels_for_unfiltered_role(db):
    db.dim_hotels.insert_many(
        [
            {"prop_id": 1, "hotel_name": "Hotel Uno", "display_name": "Hotel Uno"},
            {"prop_id": 2, "hotel_name": "Hotel Dos", "display_name": "Hotel Dos"},
        ]
    )
    admin = {"username": "root", "primary_role": "super_admin"}

    result = properties_dashboard(page=1, page_size=10, user=admin)

    assert set(_prop_ids(result)) == {1, 2}
