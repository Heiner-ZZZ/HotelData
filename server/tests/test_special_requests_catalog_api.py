"""Tests for saving the per-hotel special-requests catalog from the Amenities page.

The Amenities page gains a "Peticiones especiales" tab that edits the hotel's
catalog: labels, unit prices, behavior flags (pet_related / high_floor /
late_arrival) and the ``high_floor_from`` threshold. Saving replaces
``hotel_content_pages.special_requests`` wholesale and validates the entries.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.app.core.timezone import local_today
from src.app.modules.partner.services.content.views import partner_hotel_content


def _days_from_today(n: int) -> str:
    return (date.fromisoformat(local_today()) + timedelta(days=n)).isoformat()


@pytest.fixture
def prop(db):
    prop_id = 990
    db.dim_hotels.insert_one({
        "prop_id": prop_id,
        "hotel_name": "Catalog Hotel",
        "display_name": "Catalog Hotel",
    })
    return prop_id


class TestCatalogInManagementGet:
    def test_get_returns_default_catalog_and_threshold(self, db, prop):
        content = partner_hotel_content(prop)
        special_requests = content["special_requests"]
        by_label = {item["label"]: item for item in special_requests}
        assert "Cama extra" in by_label
        assert by_label["Cama extra"]["unit_price"] == 15.0
        assert content["high_floor_from"] == 3

    def test_get_returns_saved_catalog_and_threshold(self, db, prop):
        from src.app.modules.partner.services.content.save import save_special_requests
        save_special_requests(prop, special_requests=[
            {"label": "Cama extra", "unit_price": 25.0, "flags": ["chargeable"]},
            {"label": "Pet Sitter", "unit_price": 5.0, "flags": ["pet_related"]},
        ], high_floor_from=6)
        content = partner_hotel_content(prop)
        by_label = {item["label"]: item for item in content["special_requests"]}
        assert by_label["Cama extra"]["unit_price"] == 25.0
        assert by_label["Pet Sitter"]["pet_related"] is True
        assert by_label["Pet Sitter"]["chargeable"] is True
        assert content["high_floor_from"] == 6


class TestSaveValidation:
    def test_save_rejects_empty_label(self, db, prop):
        from src.app.modules.partner.services.content.save import save_special_requests
        with pytest.raises(ValueError, match="label"):
            save_special_requests(prop, special_requests=[{"label": "  ", "unit_price": 5.0, "flags": []}])

    def test_save_rejects_unknown_flag(self, db, prop):
        from src.app.modules.partner.services.content.save import save_special_requests
        with pytest.raises(ValueError, match="Flags inválidas"):
            save_special_requests(prop, special_requests=[
                {"label": "Cama extra", "unit_price": 5.0, "flags": ["teleport"]},
            ])

    def test_save_rejects_negative_price(self, db, prop):
        from src.app.modules.partner.services.content.save import save_special_requests
        with pytest.raises(ValueError, match="negativo"):
            save_special_requests(prop, special_requests=[
                {"label": "Cama extra", "unit_price": -3.0, "flags": []},
            ])

    def test_save_deduplicates_by_label(self, db, prop):
        from src.app.modules.partner.services.content.save import save_special_requests
        saved = save_special_requests(prop, special_requests=[
            {"label": "Cama extra", "unit_price": 5.0, "flags": []},
            {"label": "Cama Extra", "unit_price": 9.0, "flags": []},
        ])
        assert len(saved.get("special_requests") or []) == 1
        assert saved["special_requests"][0]["unit_price"] == 9.0

    def test_save_threshold_min_1(self, db, prop):
        from src.app.modules.partner.services.content.save import save_special_requests
        saved = save_special_requests(prop, special_requests=[], high_floor_from=0)
        assert saved.get("high_floor_from") == 1


class TestSavedCatalogFeedsBookingValidation:
    def test_saved_high_floor_threshold_blocks_lower_room(self, db, prop):
        """The threshold saved from the page drives the booking-time guard."""
        from src.app.modules.partner.services.content.save import save_special_requests
        from src.app.modules.reservations.service.lifecycle.create import _check_availability
        from src.app.modules.reservations.service.lifecycle.create._special_requests import validate_special_requests
        from src.app.modules.reservations.service._helpers import ReservationInput

        save_special_requests(prop, special_requests=[
            {"label": "Piso alto", "unit_price": 0.0, "flags": ["high_floor"]},
        ], high_floor_from=6)
        db.hotel_rooms.insert_one({
            "prop_id": prop, "hotel_room_id": "HR-990-101", "room_label": "101",
            "room_type_id": "RT-990-standard", "floor": "5", "is_active": True,
        })
        db.room_types.insert_one({
            "room_type_id": "RT-990-standard", "prop_id": prop, "name": "Standard",
            "base_capacity": 2, "max_adults": 2, "max_children": 1, "is_active": True,
        })
        for offset in range(0, 4):
            day = _days_from_today(offset)
            db.room_inventory_calendar.insert_one({
                "prop_id": prop, "room_type_id": "RT-990-standard", "date": day,
                "total_rooms": 10, "available_rooms": 5, "is_available": True,
            })
            db.hotel_rate_calendar.insert_one({
                "prop_id": prop, "room_type_id": "RT-990-standard", "date": day,
                "rate_amount": 100.0, "currency": "USD", "is_closed": False,
            })
        err = validate_special_requests(prop, "HR-990-101", ["Piso alto"])
        assert err is not None
        assert "piso alto" in err
        assert "desde el 6" in err
