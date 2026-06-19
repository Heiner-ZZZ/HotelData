from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGING_PATH = PROJECT_ROOT / "data" / "staging" / "pocketbase_sample.jsonl"
PARQUET_PATH = PROJECT_ROOT / "data" / "processed" / "pocketbase_sample.parquet"
SAMPLE_SIZE = 1000
PAGE_SIZE = 500

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()


def fetch_page(collection: str, page: int, per_page: int) -> tuple[int, dict]:
    base_url = os.getenv("POCKETBASE_URL", "http://127.0.0.1:8090").rstrip("/")
    token = os.getenv("POCKETBASE_AUTH_TOKEN")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    query = urlencode({"page": page, "perPage": per_page})
    request = Request(f"{base_url}/api/collections/{collection}/records?{query}", headers=headers)
    with urlopen(request, timeout=30) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def extract_sample(collection: str, limit: int = SAMPLE_SIZE) -> list[dict]:
    records: list[dict] = []
    page = 1
    while len(records) < limit:
        status_code, payload = fetch_page(collection, page, PAGE_SIZE)
        if status_code != 200:
            raise RuntimeError(f"PocketBase returned status code {status_code}")

        items = payload.get("items", [])
        if not items:
            break

        records.extend(items)
        if page >= int(payload.get("totalPages") or page):
            break
        page += 1

    return records[:limit]


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as target:
        for record in records:
            target.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    collection = os.getenv("POCKETBASE_COLLECTION", "hotel_reservation_events")
    print(f"POCKETBASE_COLLECTION: {collection}")
    print(f"Extrayendo muestra de {SAMPLE_SIZE} registros desde PocketBase...")

    records = extract_sample(collection, SAMPLE_SIZE)
    write_jsonl(STAGING_PATH, records)
    print(f"JSONL generado: {STAGING_PATH}")

    dataframe = pd.DataFrame(records)
    PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_parquet(PARQUET_PATH, index=False)
    print(f"Parquet generado: {PARQUET_PATH}")

    parquet_df = pd.read_parquet(PARQUET_PATH)
    print(f"total de filas: {len(parquet_df)}")
    print("columnas:")
    print(json.dumps(list(parquet_df.columns), indent=2, ensure_ascii=False))
    print("tipos de datos:")
    print(parquet_df.dtypes.to_string())


if __name__ == "__main__":
    main()
