"""TDD: el detalle del folio debe resolver el nombre del hotel aunque el
documento viejo lo haya persistido vacío.

``create_folio`` resuelve ``hotel_label`` desde ``dim_hotels.display_name``,
pero folios creados antes de que la dimensión tuviera esa propiedad (p. ej.
folios de penalización no-show sembrados por migraciones) quedaron con
``hotel_label: ""`` y la UI cae al fallback "Hotel #<prop_id>" en la barra de
huésped y en "Información del Folio".

El re-refresh de ``get_folio`` solo consultaba ``hotel_booking_context``;
estos tests fijan que también caiga a ``dim_hotels`` (la misma fuente del
create) cuando aquella no aporta label, y que el self-heal persista.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from tests.conftest import login

_UTC = timezone.utc


def _seed(db, booking_id: str, prop_id: int) -> None:
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": prop_id,
            "guest_name": "Huésped Sin Label",
            "total_price": 100.0,
            "total_nights": 1,
            "status": "no_show",
            "created_at": datetime.now(_UTC),
        }
    )
    db.guest_folios.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": prop_id,
            # Legacy: created before dim_hotels carried this property.
            "hotel_label": "",
            "folio_number": f"FL-NS-{booking_id}",
            "status": "open",
            "total_room": 100.0,
            "total_charges": 0.0,
            "total_discounts": 0.0,
            "total_payments": 0.0,
            "total_due": 100.0,
            "postings": [
                {
                    "posting_id": ObjectId(),
                    "type": "room",
                    "category": "Habitación",
                    "concept": "Habitación Standard",
                    "amount": 100.0,
                    "quantity": 1,
                    "unit_price": 100.0,
                    "reference_id": booking_id,
                    "reference_type": "booking",
                    "posted_at": datetime.now(_UTC),
                }
            ],
            "posting_count": 1,
            "created_at": datetime.now(_UTC),
        }
    )


class TestFolioHotelLabelFallback:
    @pytest.mark.asyncio
    async def test_get_folio_resolves_label_from_dim_hotels(self, client, db, admin_user):
        """Sin hotel_booking_context, dim_hotels.display_name completa el label."""
        _seed(db, "BK-FOLIO-NOLABEL", 941)
        db.dim_hotels.insert_one({"prop_id": 941, "display_name": "Hotel Cusco Norte"})

        assert await login(client, admin_user["username"], admin_user["password"]) == 200
        resp = await client.get("/api/billing/folios/BK-FOLIO-NOLABEL?prop_id=941")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["hotel_label"] == "Hotel Cusco Norte"

        # Self-heal persisted: the stored document no longer carries "".
        stored = db.guest_folios.find_one({"booking_id": "BK-FOLIO-NOLABEL"})
        assert stored["hotel_label"] == "Hotel Cusco Norte"

    @pytest.mark.asyncio
    async def test_existing_context_label_still_wins(self, client, db, admin_user):
        """Sin regresión: si hotel_booking_context tiene label, ese manda."""
        _seed(db, "BK-FOLIO-CTX-LABEL", 942)
        db.hotel_booking_context.insert_one({"prop_id": 942, "hotel_label": "Contexto Primero"})

        assert await login(client, admin_user["username"], admin_user["password"]) == 200
        resp = await client.get("/api/billing/folios/BK-FOLIO-CTX-LABEL?prop_id=942")

        assert resp.status_code == 200, resp.text
        assert resp.json()["hotel_label"] == "Contexto Primero"
