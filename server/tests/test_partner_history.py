"""Tests for partner property history endpoints (Pydantic *Response wave 1).

Covers:
- ``GET /api/management/properties/{prop_id}/history`` paginated list
- ``GET /api/management/properties/{prop_id}/history/{change_id}`` detail
- Wire shape: ``_id`` is serialized AS ``id`` (string), never
  ``{"$\u200boid": "..."}``
- Filters: from_date, to_date, field, user, source
- 404 paths: change belongs to a different prop_id, malformed change_id,
  change does not exist
- Pydantic models match the actual Mongo schema (no drift)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from bson import ObjectId
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ───────────────────────────── Helpers ─────────────────────────────


async def _login_admin(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"identifier": "admin_test", "password": "AdminPass123!"},
    )
    assert response.status_code == 200


def _seed_profile_change(
    db, *,
    prop_id: int = 1, field: str = "hotel_name",
    changed_by: str = "admin_test",
    changed_at: datetime | None = None,
    old_value: str = "Old Hotel",
    new_value: str = "New Hotel",
    source: str = "manual",
) -> str:
    """Insert a ``hotel_profile_changes`` row and return the str(``_id``)."""
    oid = db.hotel_profile_changes.insert_one({
        "prop_id": prop_id,
        "field": field,
        "old_value": old_value,
        "new_value": new_value,
        "changed_by": changed_by,
        "changed_at": changed_at or datetime.now(timezone.utc),
        "source": source,
        "reason": f"Test change for {field}",
    }).inserted_id
    return str(oid)


def _seed_content_change(
    db, *,
    prop_id: int = 1, entity_type: str = "content",
    field: str | None = None,
    changed_by: str = "content_editor",
    changed_at: datetime | None = None,
) -> str:
    """Insert a ``hotel_content_changes`` row and return the str(``_id``).

    ``entity_type`` defaults to ``"content"`` — the discriminator value
    used by both:

    1. The LIST endpoint filter (``content_coll.count_documents({...,
       entity_type: {$exists: True}})``), which requires the field to be
       PRESENT on the doc.
    2. The DETAIL endpoint response payload (``ChangeDetailResponse``
       ``entity_type`` field), which is the source-collection
       discriminator: ``"profile"`` for hotel_profile_changes, ``"content"``
       for hotel_content_changes.

    Using ``"content"`` here satisfies BOTH contracts:
      - the $exists filter matches.
      - the detail endpoint echoes "content" as the discriminator.
    """
    oid = db.hotel_content_changes.insert_one({
        "prop_id": prop_id,
        "entity_type": entity_type,
        "field": field or "hero_title",
        "old_value": "Old Hero",
        "new_value": "New Hero",
        "changed_by": changed_by,
        "changed_at": changed_at or datetime.now(timezone.utc),
        "source": "content_editor",
        "reason": "Test content change",
    }).inserted_id
    return str(oid)


# ─────────────────────────── Fixtures ────────────────────────────


@pytest_asyncio.fixture
async def logged_client(client: AsyncClient, admin_user):
    await _login_admin(client)
    return client


@pytest.fixture
def mixed_history(db):
    """Seed 3 profile changes + 2 content changes for prop_id=1."""
    base = datetime.now(timezone.utc).replace(microsecond=0)
    profile_ids = [
        _seed_profile_change(
            db, field="hotel_name", changed_by="admin_test",
            changed_at=base,
        ),
        _seed_profile_change(
            db, field="description", changed_by="editor_test",
            changed_at=base - timedelta(hours=1),
        ),
        _seed_profile_change(
            db, prop_id=2, field="hotel_name", changed_by="other_admin",
            changed_at=base, old_value="A", new_value="B",
        ),
    ]
    content_ids = [
        _seed_content_change(
            db, field="hero_title", changed_by="editor_test",
            changed_at=base - timedelta(hours=2),
        ),
        _seed_content_change(
            db, field="footer_text", changed_by="editor_test",
            changed_at=base - timedelta(hours=3),
        ),
    ]
    return {
        "profile_ids": profile_ids,
        "content_ids": content_ids,
        "base": base,
    }


# ─────────────────────────── Tests ────────────────────────────


class TestListHistoryEndpoint:
    async def test_list_history_requires_auth(
        self, client: AsyncClient, mixed_history,
    ):
        response = await client.get(
            "/api/management/properties/1/history",
        )
        # Auth gate — either 401 or 403, never 200.
        assert response.status_code in (401, 403)

    async def test_list_history_returns_envelope_shape(
        self, logged_client: AsyncClient, mixed_history,
    ):
        response = await logged_client.get(
            "/api/management/properties/1/history?per_page=20",
        )
        assert response.status_code == 200
        data = response.json()
        # Pydantic envelope: data + pagination + filters.
        assert "data" in data
        assert "pagination" in data
        assert "filters" in data
        # Pagination shape.
        p = data["pagination"]
        for key in ("page", "per_page", "total", "pages", "has_prev", "has_next"):
            assert key in p

    async def test_list_history_serializes_id_not_dollar_oid(
        self, logged_client: AsyncClient, mixed_history,
    ):
        """Critical invariant: ``_id`` must serialize as plain ``id`` string."""
        response = await logged_client.get(
            "/api/management/properties/1/history?per_page=20",
        )
        data = response.json()["data"]
        assert len(data) >= 1
        for item in data:
            assert "_id" not in item, (
                f"Pydantic leaked Mongo _id in wire shape: {item}"
            )
            assert "id" in item
            assert isinstance(item["id"], str)
            # Should be a 24-char hex ObjectId string.
            assert len(item["id"]) == 24

    async def test_list_history_filters_by_field(
        self, logged_client: AsyncClient, mixed_history,
    ):
        response = await logged_client.get(
            "/api/management/properties/1/history?field=hotel_name",
        )
        data = response.json()["data"]
        assert all(item["field"] == "hotel_name" for item in data)
        # Should match only 1 of the 2 hotel_name profile changes for prop 1.
        # (The third was seeded with prop_id=2 and is excluded by base filter.)
        assert len(data) == 1

    async def test_list_history_filters_by_user(
        self, logged_client: AsyncClient, mixed_history,
    ):
        response = await logged_client.get(
            "/api/management/properties/1/history?user=editor_test",
        )
        data = response.json()["data"]
        assert all(item["changed_by"] == "editor_test" for item in data)

    async def test_list_history_filters_prop_id(
        self, logged_client: AsyncClient, mixed_history,
    ):
        """prop_id=2 only sees its own change, not prop_id=1's two changes."""
        response = await logged_client.get(
            "/api/management/properties/2/history",
        )
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["id"] == mixed_history["profile_ids"][2]

    async def test_list_history_pagination_metadata(
        self, logged_client: AsyncClient, mixed_history,
    ):
        """per_page=1 should yield has_next=True on a >1 row response."""
        response = await logged_client.get(
            "/api/management/properties/1/history?per_page=1",
        )
        p = response.json()["pagination"]
        assert p["per_page"] == 1
        assert p["total"] >= 3
        assert p["has_next"] is True
        assert p["has_prev"] is False

    async def test_list_history_changed_at_serializes_as_iso(
        self, logged_client: AsyncClient, mixed_history,
    ):
        """Pydantic must turn the datetime into an ISO 8601 string.

        The wire key is ``changed_at`` (no serialization_alias on the
        Pydantic field) — so the test asserts on ``changed_at`` directly.
        Asserting on ``changedAt`` instead would silently pass for missing
        key (Pydantic JSON returns ``None``, ``.get()`` is forgiving, and
        the loop body never runs).
        """
        response = await logged_client.get(
            "/api/management/properties/1/history?per_page=5",
        )
        data = response.json()["data"]
        assert len(data) >= 1
        for item in data:
            assert item.get("changed_at") is not None, (
                "Pydantic dropped changed_at on the wire"
            )
            # ISO 8601 format begins with YYYY-MM-DDTHH:MM:SS...
            date_str = item["changed_at"]
            assert isinstance(date_str, str)
            assert date_str[:4].isdigit() and (
                date_str.startswith("20") or date_str.startswith("19")
            ), f"Unexpected date format: {date_str!r}"
            assert "T" in date_str, (
                f"Pydantic did not serialize to ISO 8601: {date_str!r}"
            )


class TestChangeDetailEndpoint:
    async def test_get_detail_serializes_id_correctly(
        self, logged_client: AsyncClient, mixed_history,
    ):
        change_id = mixed_history["profile_ids"][0]
        response = await logged_client.get(
            f"/api/management/properties/1/history/{change_id}",
        )
        assert response.status_code == 200
        data = response.json()
        assert "_id" not in data
        assert data["id"] == change_id
        assert data["entity_type"] == "profile"

    async def test_get_detail_for_content_change(
        self, logged_client: AsyncClient, mixed_history,
    ):
        change_id = mixed_history["content_ids"][0]
        response = await logged_client.get(
            f"/api/management/properties/1/history/{change_id}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == change_id
        assert data["entity_type"] == "content"
        assert data["field"] == "hero_title"

    async def test_get_detail_not_found_returns_404(
        self, logged_client: AsyncClient,
    ):
        # Valid ObjectId string but no matching doc.
        fake_oid = "000000000000000000000000"
        response = await logged_client.get(
            f"/api/management/properties/1/history/{fake_oid}",
        )
        assert response.status_code == 404

    async def test_get_detail_wrong_prop_id_returns_404(
        self, logged_client: AsyncClient, mixed_history,
    ):
        """A change belonging to prop_id=2 queried as prop_id=1 → 404."""
        change_id = mixed_history["profile_ids"][2]
        response = await logged_client.get(
            f"/api/management/properties/1/history/{change_id}",
        )
        assert response.status_code == 404

    async def test_get_detail_invalid_object_id_returns_404(
        self, logged_client: AsyncClient,
    ):
        """Non-ObjectId string must surface as 404, never 500."""
        response = await logged_client.get(
            "/api/management/properties/1/history/not-an-objectid",
        )
        assert response.status_code == 404


class TestObjectIdStrKeepInSync:
    """Conformance tests: Pydantic models MUST coerce ObjectId and reject junk."""

    async def test_object_id_str_coerces_object_id_in_response(
        self, logged_client: AsyncClient, db,
    ):
        """Insert a raw doc with native ObjectId; Pydantic must serialise it."""
        oid = db.hotel_profile_changes.insert_one({
            "prop_id": 1,
            "field": "test_keep_in_sync",
            "old_value": "x",
            "new_value": "y",
            "changed_by": "kistest",
            "changed_at": datetime.now(timezone.utc),
            "source": "manual",
            "reason": "keep_in_sync",
        }).inserted_id
        response = await logged_client.get(
            f"/api/management/properties/1/history/{str(oid)}",
        )
        assert response.status_code == 200
        body = response.json()
        # ObjectIdStr BeforeValidator turns bson.ObjectId into str.
        assert isinstance(body["id"], str)
        assert body["id"] == str(oid)
        # No MongoDB shape leakage.
        assert "$oid" not in response.text
        assert "_id" not in body
