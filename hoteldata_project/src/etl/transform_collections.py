from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

import pandas as pd

from config.settings import get_settings


BUSINESS_COLLECTIONS = [
    "hotels",
    "locations",
    "contacts",
    "websites",
    "facilities",
    "attractions",
    "hotel_quality",
]


def _split_multi_value(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    parts = re.split(r"\s*(?:,|;|\||/)\s*", str(value))
    return sorted({part.strip() for part in parts if part.strip()})


def _quality_score(row: pd.Series) -> tuple[int, str, list[str]]:
    required_fields = ["HotelName", "Address", "cityName", "PhoneNumber"]
    optional_fields = ["Description", "HotelWebsiteUrl", "HotelFacilities", "Attractions", "PinCode"]
    issues = []
    score = 100
    for field in required_fields:
        if not row.get(field):
            score -= 15
            issues.append(f"missing_{field}")
    for field in optional_fields:
        if not row.get(field):
            score -= 5
            issues.append(f"missing_{field}")
    if row.get("HotelRating") is None or pd.isna(row.get("HotelRating")):
        score -= 10
        issues.append("missing_or_invalid_rating")
    score = max(score, 0)
    if score >= 90:
        level = "excellent"
    elif score >= 75:
        level = "good"
    elif score >= 50:
        level = "review"
    else:
        level = "critical"
    return score, level, issues


def _append_jsonl(collection_name: str, documents: list[dict]) -> int:
    if not documents:
        return 0
    settings = get_settings()
    path = settings.processed_dir / f"{collection_name}.jsonl"
    with path.open("a", encoding="utf-8") as target:
        for document in documents:
            target.write(json.dumps(document, ensure_ascii=False) + "\n")
    return len(documents)


def _dataset_id(cleaned_path) -> tuple[str, str]:
    digest = hashlib.sha256()
    with cleaned_path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    content_hash = digest.hexdigest()
    return f"hotels_{content_hash[:12]}", content_hash


def transform_dataset_container() -> dict:
    settings = get_settings()
    cleaned_path = settings.processed_dir / "hotels_clean.jsonl"
    dataset_id, content_hash = _dataset_id(cleaned_path)
    record_count = sum(1 for _ in cleaned_path.open("r", encoding="utf-8"))
    document = {
        "dataset_id": dataset_id,
        "source_system": "hotels_csv",
        "record_count": record_count,
        "content_hash": content_hash,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    target = settings.processed_dir / "dataset_container.jsonl"
    target.write_text(json.dumps(document, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"dataset_id": dataset_id, "record_count": record_count, "path": str(target)}


def transform_business_collections() -> dict:
    settings = get_settings()
    cleaned_path = settings.processed_dir / "hotels_clean.jsonl"
    container_path = settings.processed_dir / "dataset_container.jsonl"
    dataset_container = json.loads(container_path.read_text(encoding="utf-8").splitlines()[0])
    dataset_id = dataset_container["dataset_id"]

    for collection_name in BUSINESS_COLLECTIONS:
        path = settings.processed_dir / f"{collection_name}.jsonl"
        if path.exists():
            path.unlink()

    counts = {name: 0 for name in BUSINESS_COLLECTIONS}
    for chunk in pd.read_json(cleaned_path, lines=True, dtype=False, chunksize=settings.chunk_size):
        hotels = []
        locations = []
        contacts = []
        websites = []
        facilities = []
        attractions = []
        hotel_quality = []
        for _, row in chunk.iterrows():
            hotel_code = str(row["HotelCode"])
            hotels.append({
                "hotel_code": hotel_code,
                "hotel_name": row.get("HotelName"),
                "description": row.get("Description"),
                "rating": None if pd.isna(row.get("HotelRating")) else float(row.get("HotelRating")),
                "dataset_id": dataset_id,
            })
            locations.append({
                "hotel_code": hotel_code,
                "address": row.get("Address"),
                "map": row.get("Map"),
                "pin_code": row.get("PinCode"),
                "city_code": row.get("cityCode"),
                "city_name": row.get("cityName"),
                "county_code": row.get("countyCode"),
                "county_name": row.get("countyName"),
                "dataset_id": dataset_id,
            })
            contacts.append({
                "hotel_code": hotel_code,
                "phone_number": row.get("PhoneNumber"),
                "fax_number": row.get("FaxNumber"),
                "dataset_id": dataset_id,
            })
            websites.append({
                "hotel_code": hotel_code,
                "url": row.get("HotelWebsiteUrl"),
                "dataset_id": dataset_id,
            })
            for facility in _split_multi_value(row.get("HotelFacilities")):
                facilities.append({"hotel_code": hotel_code, "facility": facility, "dataset_id": dataset_id})
            for attraction in _split_multi_value(row.get("Attractions")):
                attractions.append({"hotel_code": hotel_code, "attraction": attraction, "dataset_id": dataset_id})
            score, level, issues = _quality_score(row)
            hotel_quality.append({
                "hotel_code": hotel_code,
                "quality_score": score,
                "quality_level": level,
                "issues": issues,
                "dataset_id": dataset_id,
            })

        chunk_counts = {
            "hotels": _append_jsonl("hotels", hotels),
            "locations": _append_jsonl("locations", locations),
            "contacts": _append_jsonl("contacts", contacts),
            "websites": _append_jsonl("websites", websites),
            "facilities": _append_jsonl("facilities", facilities),
            "attractions": _append_jsonl("attractions", attractions),
            "hotel_quality": _append_jsonl("hotel_quality", hotel_quality),
        }
        for name, count in chunk_counts.items():
            counts[name] += count

    return {"dataset_id": dataset_id, "collections": counts}

