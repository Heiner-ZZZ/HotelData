"""Tests for saving the per-hotel special-requests catalog from the Amenities page.

The Amenities page gains a "Peticiones especiales" tab that edits the hotel's
catalog: labels, unit prices, behavior flags (pet_related / late_arrival).
Saving replaces ``hotel_content_pages.special_requests`` wholesale and validates
the entries. (El flag ``high_floor`` y el umbral ``high_floor_from`` se
eliminaron 2026-08.)
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
    def test_get_returns_default_catalog(self, db, prop):
        content = partner_hotel_content(prop)
        special_requests = content["special_requests"]
        by_label = {item["label"]: item for item in special_requests}
        assert "Cama extra" in by_label
        assert by_label["Cama extra"]["unit_price"] == 15.0
        # El flag ``high_floor`` ya no se ofrece (eliminado 2026-08).
        assert all(not item.get("high_floor") for item in special_requests)

    def test_get_returns_saved_catalog(self, db, prop):
        from src.app.modules.partner.services.content.save import save_special_requests
        save_special_requests(prop, special_requests=[
            {"label": "Cama extra", "unit_price": 25.0, "flags": ["chargeable"]},
            {"label": "Pet Sitter", "unit_price": 5.0, "flags": ["pet_related"]},
        ])
        content = partner_hotel_content(prop)
        by_label = {item["label"]: item for item in content["special_requests"]}
        assert by_label["Cama extra"]["unit_price"] == 25.0
        assert by_label["Pet Sitter"]["pet_related"] is True
        assert by_label["Pet Sitter"]["chargeable"] is True


class TestDeleteDefaultRequest:
    def test_deleted_default_does_not_come_back(self, db, prop):
        """Eliminar un default en el guardado debe persistir: el read no lo re-mergea."""
        from src.app.modules.partner.services.content.save import save_special_requests

        save_special_requests(prop, special_requests=[
            {"label": "Cuna para bebé", "unit_price": 10.0, "flags": ["chargeable"]},
            {"label": "Accesibilidad", "unit_price": 0.0, "flags": []},
            {"label": "Mascotas (Pet friendly)", "unit_price": 20.0, "flags": ["pet_related", "chargeable"]},
            {"label": "Llegada tarde", "unit_price": 0.0, "flags": ["late_arrival"]},
        ])
        labels = {item["label"] for item in partner_hotel_content(prop)["special_requests"]}
        assert "Cama extra" not in labels
        assert "Cuna para bebé" in labels

    def test_re_adding_deleted_default_restores_it(self, db, prop):
        """Re-agregar un default eliminado en un segundo guardado debe restaurarlo."""
        from src.app.modules.partner.services.content.save import save_special_requests

        save_special_requests(prop, special_requests=[
            {"label": "Cuna para bebé", "unit_price": 10.0, "flags": ["chargeable"]},
        ])
        labels = {item["label"] for item in partner_hotel_content(prop)["special_requests"]}
        assert "Cama extra" not in labels

        save_special_requests(prop, special_requests=[
            {"label": "Cama extra", "unit_price": 12.0, "flags": ["chargeable"]},
            {"label": "Cuna para bebé", "unit_price": 10.0, "flags": ["chargeable"]},
        ])
        by_label = {item["label"]: item for item in partner_hotel_content(prop)["special_requests"]}
        assert by_label["Cama extra"]["unit_price"] == 12.0


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

    def test_legacy_high_floor_entries_are_dropped(self, db, prop):
        """El flag ``high_floor`` (eliminado 2026-08) ya no se acepta al guardar,
        y una entrada legacy con ese flag no reaparece en el catálogo."""
        from src.app.modules.partner.services.content.save import save_special_requests
        with pytest.raises(ValueError, match="Flags inválidas"):
            save_special_requests(prop, special_requests=[
                {"label": "Piso alto", "unit_price": 0.0, "flags": ["high_floor"]},
            ])
        # Entrada legacy sembrada a mano en BD → filtrada por el read.
        db.hotel_content_pages.insert_one({
            "prop_id": prop,
            "special_requests": [{"label": "Piso alto", "unit_price": 0.0, "flags": ["high_floor"]}],
        })
        labels = {item["label"] for item in partner_hotel_content(prop)["special_requests"]}
        assert "Piso alto" not in labels
