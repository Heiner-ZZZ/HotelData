from __future__ import annotations

import pandas as pd

from src.etl.transform_collections import _quality_score


def test_quality_score_marks_complete_record_excellent():
    row = pd.Series(
        {
            "HotelName": "Hotel Test",
            "Address": "Main Street",
            "cityName": "Quito",
            "PhoneNumber": "123",
            "Description": "Nice",
            "HotelWebsiteUrl": "https://example.com",
            "HotelFacilities": "Wifi",
            "Attractions": "Museum",
            "PinCode": "170101",
            "HotelRating": 4.0,
        }
    )
    score, level, issues = _quality_score(row)
    assert score == 100
    assert level == "excellent"
    assert issues == []


def test_quality_score_detects_missing_required_fields():
    row = pd.Series({"HotelName": None, "Address": None, "cityName": None, "PhoneNumber": None})
    score, level, issues = _quality_score(row)
    assert score < 50
    assert level == "critical"
    assert "missing_HotelName" in issues
