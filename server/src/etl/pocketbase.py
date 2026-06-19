from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config.settings import get_settings


def extract_pocketbase_reservations() -> dict:
    settings = get_settings()
    settings.staging_dir.mkdir(parents=True, exist_ok=True)
    target = settings.staging_dir / "pocketbase_reservations.jsonl"
    if target.exists():
        target.unlink()

    headers = {"Accept": "application/json"}
    if settings.pocketbase_auth_token:
        headers["Authorization"] = f"Bearer {settings.pocketbase_auth_token}"

    page = 1
    total_rows = 0
    columns: set[str] = set()
    base_url = settings.pocketbase_url.rstrip("/")
    collection = settings.pocketbase_collection

    while True:
        query = urlencode({"page": page, "perPage": settings.pocketbase_page_size})
        request = Request(f"{base_url}/api/collections/{collection}/records?{query}", headers=headers)
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))

        items = payload.get("items", [])
        if not items:
            break

        with target.open("a", encoding="utf-8") as sink:
            for item in items:
                item.pop("collectionId", None)
                item.pop("collectionName", None)
                item.pop("expand", None)
                columns.update(item.keys())
                sink.write(json.dumps(item, ensure_ascii=False) + "\n")
                total_rows += 1

        if page >= int(payload.get("totalPages") or page):
            break
        page += 1

    metadata = {
        "source_system": "pocketbase",
        "pocketbase_url": base_url,
        "collection": collection,
        "staging_path": str(target),
        "rows": total_rows,
        "columns": sorted(columns),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }
    (settings.staging_dir / "extract_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return metadata
