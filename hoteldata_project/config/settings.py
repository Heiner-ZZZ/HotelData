from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    project_root: Path
    mongo_uri: str
    mongo_database: str
    raw_csv_path: Path
    staging_dir: Path
    processed_dir: Path
    reports_dir: Path
    chunk_size: int
    batch_size: int
    min_dataset_rows: int
    demo_row_limit: int
    full_reload: bool
    pocketbase_url: str
    pocketbase_collection: str
    pocketbase_collection_03: str
    pocketbase_page_size: int
    pocketbase_auth_token: str | None
    reservations_parquet_path: Path
    ga03_expected_records: int
    task_number: str
    target_records: int


def get_settings() -> Settings:
    default_root = Path(__file__).resolve().parents[1]
    root = Path(os.getenv("HOTELDATA_PROJECT_ROOT", str(default_root))).resolve()
    raw_csv = Path(os.getenv("HOTELDATA_RAW_CSV", "data/raw/hotels.csv"))
    if not raw_csv.is_absolute():
        raw_csv = root / raw_csv
    task_number = os.getenv("TASK_NUMBER", "03")
    generic_pocketbase_collection = os.getenv("POCKETBASE_COLLECTION")
    default_ga03_collection = "hotel_reservation_events_03"
    if task_number == "03" and generic_pocketbase_collection and generic_pocketbase_collection != "hotel_reservation_events__2":
        ga03_collection = generic_pocketbase_collection
    else:
        ga03_collection = default_ga03_collection

    return Settings(
        project_root=root,
        mongo_uri=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        mongo_database=os.getenv("MONGO_DATABASE", "hoteldata_hub"),
        raw_csv_path=raw_csv,
        staging_dir=root / "data" / "staging",
        processed_dir=root / "data" / "processed",
        reports_dir=root / "data" / "reports",
        chunk_size=int(os.getenv("HOTELDATA_CHUNK_SIZE", "50000")),
        batch_size=int(os.getenv("HOTELDATA_BATCH_SIZE", "5000")),
        min_dataset_rows=int(os.getenv("HOTELDATA_MIN_DATASET_ROWS", "100000")),
        demo_row_limit=int(os.getenv("HOTELDATA_DEMO_ROW_LIMIT", "100000")),
        full_reload=os.getenv("HOTELDATA_FULL_RELOAD", "true").lower() == "true",
        pocketbase_url=os.getenv("POCKETBASE_URL", "http://127.0.0.1:8090"),
        pocketbase_collection=os.getenv("POCKETBASE_COLLECTION", "hotel_reservation_events__2"),
        pocketbase_collection_03=os.getenv("POCKETBASE_COLLECTION_03", ga03_collection),
        pocketbase_page_size=int(os.getenv("POCKETBASE_PAGE_SIZE", "500")),
        pocketbase_auth_token=os.getenv("POCKETBASE_AUTH_TOKEN") or None,
        reservations_parquet_path=root / "data" / "staging" / "hotel_reservations.parquet",
        ga03_expected_records=int(os.getenv("GA03_EXPECTED_RECORDS", os.getenv("TARGET_RECORDS", "300000"))),
        task_number=task_number,
        target_records=int(os.getenv("TARGET_RECORDS", os.getenv("GA03_EXPECTED_RECORDS", "300000"))),
    )
