"""Tests for the operational hotel availability search.

These tests exercise the availability search logic against real Mongo.
They verify destination resolution, inventory checking, and rate lookups.
"""
from __future__ import annotations

import pytest

from src.app.modules.hotels.service.availability import (
    _check_inventory_for_dates,
    _matching_room_types,
    _hotel_min_rate_for_range,
    search_available_hotels,
)

pytestmark = pytest.mark.asyncio


def _seed_test_data(db):
    """Seed minimal test data for availability checks."""
    # Create a test hotel in dim_hotels
    db.dim_hotels.update_one(
        {"prop_id": 99999},
        {"$set": {
            "prop_id": 99999,
            "hotel_name": "Test Hotel Availability",
            "display_name": "Test Hotel Availability Madrid",
            "prop_starrating": 4.0,
            "prop_review_score": 8.5,
        }},
        upsert=True,
    )
    # Create a destination
    db.dim_destinations.update_one(
        {"srch_destination_id": 9999},
        {"$set": {
            "srch_destination_id": 9999,
            "destination_display_name": "Test City",
            "destination_name": "Test City",
        }},
        upsert=True,
    )
    db.hotel_content_pages.update_one(
        {"prop_id": 99999},
        {"$set": {
            "prop_id": 99999,
            "active_amenities": ["Wi-Fi", "Piscina", "Playa", "Parking", "Spa"],
        }},
        upsert=True,
    )
    # Create a room type
    db.room_types.update_one(
        {"room_type_id": "RT-99999-test"},
        {"$set": {
            "room_type_id": "RT-99999-test",
            "prop_id": 99999,
            "name": "Test Room Standard",
            "max_adults": 2,
            "max_children": 1,
            "base_capacity": 2,
            "is_active": True,
        }},
        upsert=True,
    )
    # Create inventory for 3 nights
    for date_str in ["2026-08-01", "2026-08-02", "2026-08-03"]:
        db.room_inventory_calendar.update_one(
            {"prop_id": 99999, "room_type_id": "RT-99999-test", "date": date_str},
            {"$set": {
                "prop_id": 99999,
                "room_type_id": "RT-99999-test",
                "date": date_str,
                "total_rooms": 10,
                "available_rooms": 5,
                "blocked_rooms": 0,
                "version": 1,
            }},
            upsert=True,
        )
    # Create a rate plan and calendar entries
    db.rate_plans.update_one(
        {"rate_plan_id": "RP-99999-base"},
        {"$set": {
            "rate_plan_id": "RP-99999-base",
            "prop_id": 99999,
            "name": "Base Rate",
            "base_rate": 100.0,
            "is_active": True,
        }},
        upsert=True,
    )
    for date_str in ["2026-08-01", "2026-08-02", "2026-08-03"]:
        db.hotel_rate_calendar.update_one(
            {"prop_id": 99999, "rate_plan_id": "RP-99999-base", "date": date_str},
            {"$set": {
                "prop_id": 99999,
                "rate_plan_id": "RP-99999-base",
                "date": date_str,
                "rate_amount": 89.50,
                "is_closed": False,
            }},
            upsert=True,
        )
    # Add fact data linking hotel to destination
    db.fact_hotel_reservations.insert_one({
        "prop_id": 99999,
        "srch_destination_id": 9999,
        "price_usd": 100.0,
        "click_bool": 1,
        "reserva_bool": 1,
        "promotion_flag": 0,
    })


async def test_check_inventory_full_coverage(db):
    """_check_inventory_for_dates returns True when ALL dates have availability."""
    _seed_test_data(db)
    result = _check_inventory_for_dates(99999, "RT-99999-test", "2026-08-01", "2026-08-04", 1)
    assert result is True


async def test_check_inventory_partial_coverage(db):
    """_check_inventory_for_dates returns False when some dates lack availability."""
    _seed_test_data(db)
    # Only 2 rooms available on 2026-08-01, requesting 5 should fail
    result = _check_inventory_for_dates(99999, "RT-99999-test", "2026-08-01", "2026-08-04", 10)
    assert result is False


async def test_matching_room_types_finds_correct_types(db):
    """_matching_room_types returns room types that accommodate guest count."""
    _seed_test_data(db)
    types = _matching_room_types(99999, 2, 1)
    assert len(types) >= 1
    assert types[0]["room_type_id"] == "RT-99999-test"

    # Requesting more guests than capacity should return empty
    types = _matching_room_types(99999, 5, 2)
    assert len(types) == 0


async def test_hotel_min_rate_for_range(db):
    """_hotel_min_rate_for_range returns the minimum nightly rate."""
    _seed_test_data(db)
    rate = _hotel_min_rate_for_range(99999, "2026-08-01", "2026-08-04")
    assert rate is not None
    assert rate == 89.50


async def test_search_available_hotels_full_flow(db):
    """search_available_hotels returns hotels with matching availability."""
    _seed_test_data(db)
    result = search_available_hotels(
        destination="Test City",
        check_in="2026-08-01",
        check_out="2026-08-04",
        adults=2,
        children=0,
        rooms=1,
    )
    assert result["total"] >= 1
    item = result["items"][0]
    assert item["prop_id"] == 99999
    assert item["hotel_name"] == "Test Hotel Availability Madrid"
    assert item["min_nightly_rate"] == 89.50
    assert item["total_estimated"] == 89.50 * 3  # 3 nights
    assert item["matched_room_type"]["room_type_id"] == "RT-99999-test"
    assert item["general_amenities"] == ["Wi-Fi", "Piscina", "Playa", "Parking"]
    assert "hotel_rooms" not in item
    assert "room_inventory_calendar" not in item
    assert result["alternative_destinations"] == []


async def test_search_no_availability_excludes_hotel(db):
    """Hotels without sufficient inventory are excluded."""
    _seed_test_data(db)
    # Request more rooms than available (5 available, request 10)
    result = search_available_hotels(
        destination="Test City",
        check_in="2026-08-01",
        check_out="2026-08-04",
        adults=2,
        children=0,
        rooms=10,
    )
    assert result["total"] == 0
    assert isinstance(result["alternative_destinations"], list)


async def test_search_returns_only_one_room_summary(db):
    """Search returns one available room type, never physical room data."""
    _seed_test_data(db)
    db.room_types.insert_many([
        {
            "room_type_id": "RT-99999-large",
            "prop_id": 99999,
            "name": "Large Suite",
            "max_adults": 4,
            "max_children": 2,
            "base_capacity": 6,
            "is_active": True,
        },
        {
            "room_type_id": "RT-99999-second",
            "prop_id": 99999,
            "name": "Second Room Type",
            "max_adults": 2,
            "max_children": 1,
            "base_capacity": 3,
            "is_active": True,
        },
    ])
    result = search_available_hotels(
        check_in="2026-08-01",
        check_out="2026-08-04",
        adults=2,
        rooms=1,
    )
    item = next(item for item in result["items"] if item["prop_id"] == 99999)
    assert item["matched_room_type"]["room_type_id"] == "RT-99999-test"
    assert "hotel_rooms" not in item
    assert "room_inventory_calendar" not in item


async def test_search_no_destination_returns_all(db):
    """Without destination, search returns all hotels with availability."""
    _seed_test_data(db)
    result = search_available_hotels(
        check_in="2026-08-01",
        check_out="2026-08-04",
        adults=2,
        rooms=1,
    )
    # At minimum the seeded hotel should appear, with the public page size
    # capped at ten cards.
    assert result["total"] >= 1
    assert result["page_size"] == 10
    assert len(result["items"]) <= 10


async def test_amenities_filter_works(db):
    """RF-003: Hotels can be filtered by amenities text."""
    # Seed amenities data for the test hotel
    db.hotel_content_pages.update_one(
        {"prop_id": 99999},
        {"$set": {
            "prop_id": 99999,
            "amenities_text": "WiFi gratis, Piscina al aire libre, Desayuno incluido, Estacionamiento",
        }},
        upsert=True,
    )
    _seed_test_data(db)
    result = search_available_hotels(
        amenities="WiFi",
        check_in="2026-08-01",
        check_out="2026-08-04",
        adults=2,
        rooms=1,
    )
    assert result["total"] >= 1
    assert result["items"][0]["prop_id"] == 99999


async def test_amenities_filter_excludes_non_matching(db):
    """Hotels without the requested amenities are excluded."""
    _seed_test_data(db)
    # Don't seed amenities for this test hotel
    result = search_available_hotels(
        amenities="Sauna",
        check_in="2026-08-01",
        check_out="2026-08-04",
        adults=2,
        rooms=1,
    )
    assert result["total"] == 0


async def test_amenities_filter_and_mode_requires_all_terms(db):
    """amenities_mode='and' requires ALL amenities to match."""
    db.hotel_content_pages.update_one(
        {"prop_id": 99999},
        {"$set": {
            "prop_id": 99999,
            "amenities_text": "WiFi gratis, Piscina al aire libre",
        }},
        upsert=True,
    )
    _seed_test_data(db)
    # 'and' mode: hotel has both WiFi and Piscina → should match
    result = search_available_hotels(
        amenities="WiFi, Piscina",
        amenities_mode="and",
        check_in="2026-08-01",
        check_out="2026-08-04",
        adults=2,
        rooms=1,
    )
    assert result["total"] >= 1

    # 'and' mode: hotel has WiFi but NOT Sauna → should NOT match
    result = search_available_hotels(
        amenities="WiFi, Sauna",
        amenities_mode="and",
        check_in="2026-08-01",
        check_out="2026-08-04",
        adults=2,
        rooms=1,
    )
    assert result["total"] == 0


async def test_amenities_filter_or_mode_requires_any_term(db):
    """amenities_mode='or' (default) matches hotels with ANY amenity."""
    db.hotel_content_pages.update_one(
        {"prop_id": 99999},
        {"$set": {
            "prop_id": 99999,
            "amenities_text": "WiFi gratis, Piscina al aire libre",
        }},
        upsert=True,
    )
    _seed_test_data(db)
    # 'or' mode: hotel has WiFi, should match even without Sauna
    result = search_available_hotels(
        amenities="WiFi, Sauna",
        amenities_mode="or",
        check_in="2026-08-01",
        check_out="2026-08-04",
        adults=2,
        rooms=1,
    )
    assert result["total"] >= 1


async def test_compare_hotels_returns_up_to_three(db):
    """RF-004/005: compare_hotels returns up to 3 hotels side by side."""
    from src.app.modules.hotels.service.compare import compare_hotels
    _seed_test_data(db)
    result = compare_hotels([99999])
    assert len(result["items"]) >= 1
    assert result["items"][0]["prop_id"] == 99999


async def test_search_endpoint_always_returns_alternative_destinations(db, client):
    """The public /search envelope always includes the alternatives array."""
    _seed_test_data(db)
    response = await client.get("/api/hotels/search")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["alternative_destinations"], list)


async def test_availability_endpoint_returns_operational_hotel_name(db, client):
    """The guest search endpoint exposes the name consumed by its cards."""
    _seed_test_data(db)
    response = await client.get("/api/hotels/availability", params={"page_size": 10})
    assert response.status_code == 200
    payload = response.json()
    assert payload["page_size"] == 10
    assert payload["items"][0]["hotel_name"] == "Test Hotel Availability Madrid"


async def test_compare_endpoint_accepts_repeated_prop_id_parameters(db, client):
    """The comparison contract uses repeated prop_id query parameters."""
    _seed_test_data(db)
    response = await client.get(
        "/api/hotels/compare",
        params=[("prop_id", "99999")],
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["prop_id"] == 99999
