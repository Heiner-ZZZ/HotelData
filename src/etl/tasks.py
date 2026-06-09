from __future__ import annotations

from config.settings import get_settings
from src.database.connection import get_database
from src.database.indexes import create_indexes as create_mongo_indexes
from src.etl.extract import extract_csv as extract_csv_file
from src.etl.load import load_business_collections as load_businesses
from src.etl.load import load_fact_events as load_facts
from src.etl.load import load_rejected_records as load_rejections
from src.etl.load_reservations import load_fact_hotel_reservations as load_reservation_facts
from src.etl.load_reservations import load_reservation_dimensions as load_reservation_dims
from src.etl.master_keys import seed_master_collections_check as check_master_collections
from src.etl.master_keys import validate_master_keys as validate_keys
from src.etl.parquet_io import convert_pocketbase_staging_to_parquet as convert_to_parquet
from src.etl.pocketbase import extract_pocketbase_reservations as extract_pb_reservations
from src.etl.reports import save_execution_report as write_execution_report
from src.etl.reservations import transform_reservations_from_parquet as build_reservations
from src.etl.transform_clean import transform_clean_dataset as clean_dataset
from src.etl.transform_collections import (
    transform_business_collections as build_business_collections,
    transform_dataset_container as build_dataset_container,
)
from src.etl.transform_fact import transform_fact_events as build_fact_events
from src.etl.validate import validate_staged_schema


def validate_environment() -> dict:
    settings = get_settings()
    settings.staging_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    marker = settings.staging_dir / "execution_id.txt"
    if marker.exists():
        marker.unlink()
    if not settings.raw_csv_path.exists():
        raise FileNotFoundError(f"Expected raw CSV at {settings.raw_csv_path}")
    return {
        "project_root": str(settings.project_root),
        "raw_csv_path": str(settings.raw_csv_path),
        "mongo_database": settings.mongo_database,
        "full_reload": settings.full_reload,
    }


def validate_ta02_environment() -> dict:
    settings = get_settings()
    settings.staging_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    marker = settings.staging_dir / "execution_id.txt"
    if marker.exists():
        marker.unlink()
    return {
        "project_root": str(settings.project_root),
        "pocketbase_url": settings.pocketbase_url,
        "pocketbase_collection": settings.pocketbase_collection,
        "parquet_path": str(settings.reservations_parquet_path),
        "mongo_database": settings.mongo_database,
        "full_reload": settings.full_reload,
    }


def seed_master_collections_check() -> dict:
    return check_master_collections()


def extract_csv() -> dict:
    return extract_csv_file()


def extract_pocketbase_reservations() -> dict:
    return extract_pb_reservations()


def convert_reservations_to_parquet() -> dict:
    return convert_to_parquet()


def transform_reservations_from_parquet() -> dict:
    return build_reservations()


def transform_clean_dataset() -> dict:
    return clean_dataset()


def transform_dataset_container() -> dict:
    return build_dataset_container()


def transform_business_collections() -> dict:
    return build_business_collections()


def validate_schema() -> dict:
    return validate_staged_schema()


def transform_fact_events() -> dict:
    return build_fact_events()


def validate_master_keys() -> dict:
    return validate_keys()


def load_fact_events() -> dict[str, int]:
    return load_facts()


def load_business_collections() -> dict[str, int]:
    return load_businesses()


def load_rejected_records() -> dict[str, int]:
    return load_rejections()


def load_reservation_dimensions() -> dict[str, int]:
    return load_reservation_dims()


def load_fact_hotel_reservations() -> dict[str, int]:
    return load_reservation_facts()


def create_indexes() -> dict[str, list[str]]:
    return create_mongo_indexes(get_database())


def save_execution_report() -> dict:
    return write_execution_report()
