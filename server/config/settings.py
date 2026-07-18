from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")


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
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    app_base_url: str
    nvidia_api_key: str
    nvidia_api_base: str
    nvidia_chat_model: str
    nvidia_chat_temperature: float
    nvidia_chat_top_p: float
    nvidia_chat_max_tokens: int
    cors_allowed_origins: tuple[str, ...]
    cors_allowed_methods: tuple[str, ...]
    cors_allowed_headers: tuple[str, ...]


def _csv_env(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


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

    _DEFAULT_RECORDS = "0"

    return Settings(
        project_root=root,
        mongo_uri=os.getenv("MONGO_URI", "mongodb://localhost:27018"),
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
        ga03_expected_records=int(os.getenv("GA03_EXPECTED_RECORDS", os.getenv("TARGET_RECORDS", _DEFAULT_RECORDS))),
        task_number=task_number,
        target_records=int(os.getenv("TARGET_RECORDS", _DEFAULT_RECORDS)),
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_from=os.getenv("SMTP_FROM", "noreply@hoteldata.local"),
        app_base_url=os.getenv("APP_BASE_URL", "http://localhost:4200"),
        nvidia_api_key=os.getenv("NVIDIA_API_KEY", ""),
        nvidia_api_base=os.getenv("NVIDIA_API_BASE", "https://integrate.api.nvidia.com/v1"),
        nvidia_chat_model=os.getenv("NVIDIA_CHAT_MODEL", "deepseek-ai/deepseek-v4-pro"),
        nvidia_chat_temperature=float(os.getenv("NVIDIA_CHAT_TEMPERATURE", "1")),
        nvidia_chat_top_p=float(os.getenv("NVIDIA_CHAT_TOP_P", "0.95")),
        nvidia_chat_max_tokens=int(os.getenv("NVIDIA_CHAT_MAX_TOKENS", "16384")),
        cors_allowed_origins=_csv_env(
            "CORS_ALLOWED_ORIGINS",
            "http://127.0.0.1:4200,http://localhost:4200,http://localhost:80,http://localhost",
        ),
        cors_allowed_methods=_csv_env(
            "CORS_ALLOWED_METHODS",
            "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        ),
        cors_allowed_headers=_csv_env(
            "CORS_ALLOWED_HEADERS",
            "Authorization,Content-Type,X-Requested-With,Cookie",
        ),
    )
