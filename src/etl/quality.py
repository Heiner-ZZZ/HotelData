from __future__ import annotations

import json
from datetime import datetime, timezone

from config.settings import get_settings


def _count_jsonl(path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as source:
        return sum(1 for line in source if line.strip())


def _execution_id() -> str:
    settings = get_settings()
    marker = settings.staging_dir / "execution_id.txt"
    if marker.exists():
        return marker.read_text(encoding="utf-8").strip()
    return f"etl_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def generate_quality_report() -> dict:
    settings = get_settings()
    metadata_path = settings.staging_dir / "extract_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    reservations_path = settings.processed_dir / "fact_hotel_reservations.jsonl"
    if reservations_path.exists():
        candidate_count = _count_jsonl(reservations_path)
        valid_count = candidate_count
    else:
        candidate_count = _count_jsonl(settings.processed_dir / "fact_hotel_events_candidate.jsonl")
        valid_count = _count_jsonl(settings.processed_dir / "fact_hotel_events.jsonl")
    transform_rejected_count = _count_jsonl(settings.processed_dir / "rejected_records_transform.jsonl")
    key_rejected_count = _count_jsonl(settings.processed_dir / "rejected_records_keys.jsonl")
    rejected_count = transform_rejected_count + key_rejected_count
    total_after_extract = candidate_count + transform_rejected_count

    report = {
        "execution_id": _execution_id(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_rows": int(metadata.get("rows", 0)),
        "candidate_records": candidate_count,
        "valid_fact_records": valid_count,
        "rejected_records": rejected_count,
        "transform_rejected_records": transform_rejected_count,
        "master_key_rejected_records": key_rejected_count,
        "completeness_score": round(valid_count / total_after_extract, 4) if total_after_extract else 0,
        "nulls_by_column": {},
    }
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    (settings.reports_dir / "quality_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report
