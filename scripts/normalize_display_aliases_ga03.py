from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "normalize_display_aliases_ga03.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def non_empty_filter(field_name: str) -> dict:
    return {field_name: {"$exists": True, "$nin": [None, ""]}}


def main() -> int:
    db = get_database()
    total_sites = db.dim_sites.count_documents({})
    existing_before = db.dim_sites.count_documents(non_empty_filter("site_name"))
    missing_before = total_sites - existing_before

    updated = 0
    touched_site_ids: list[int] = []
    cursor = db.dim_sites.find({}, {"_id": 1, "site_id": 1, "site_name": 1, "site_display_name": 1, "site_label": 1})
    for item in cursor:
        current_value = str(item.get("site_name") or "").strip()
        if current_value:
            continue
        site_id = item.get("site_id")
        alias = (
            str(item.get("site_display_name") or "").strip()
            or str(item.get("site_label") or "").strip()
            or f"Sitio {site_id}"
        )
        result = db.dim_sites.update_one({"_id": item["_id"]}, {"$set": {"site_name": alias}})
        if result.modified_count:
            updated += 1
            if site_id is not None:
                touched_site_ids.append(int(site_id))

    existing_after = db.dim_sites.count_documents(non_empty_filter("site_name"))
    report = {
        "generated_at": utc_now_iso(),
        "collection": "dim_sites",
        "total_documents": total_sites,
        "site_name_before": existing_before,
        "site_name_missing_before": missing_before,
        "updated_documents": updated,
        "site_name_after": existing_after,
        "site_name_missing_after": total_sites - existing_after,
        "touched_site_ids": sorted(touched_site_ids),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"report_path={REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
