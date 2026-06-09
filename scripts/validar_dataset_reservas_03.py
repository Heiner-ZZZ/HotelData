from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings
from src.database.connection import get_database


load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "validacion_dataset_reservas_03.json"
TA02_COLLECTION_NAME = "hotel_reservation_events__2"


def authenticate(base_url: str) -> dict[str, str]:
    token = os.getenv("POCKETBASE_AUTH_TOKEN")
    if token:
        return {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    email = os.getenv("POCKETBASE_ADMIN_EMAIL")
    password = os.getenv("POCKETBASE_ADMIN_PASSWORD")
    if not email or not password:
        raise RuntimeError("Faltan credenciales PocketBase")
    response = requests.post(
        f"{base_url}/api/collections/_superusers/auth-with-password",
        json={"identity": email, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return {"Accept": "application/json", "Authorization": f"Bearer {response.json()['token']}"}


def main() -> None:
    settings = get_settings()
    base_url = settings.pocketbase_url.rstrip("/")
    collection_name = settings.pocketbase_collection_03
    if collection_name == TA02_COLLECTION_NAME:
        raise RuntimeError("La coleccion destino GA03 no puede apuntar a la coleccion TA02")
    headers = authenticate(base_url)
    response = requests.get(
        f"{base_url}/api/collections/{collection_name}/records",
        params={"page": 1, "perPage": 1},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    total_items = int(response.json().get("totalItems", 0) or 0)
    db = get_database()
    db.command("ping")
    collections = db.list_collection_names()
    report = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "pocketbase_url": base_url,
        "pocketbase_collection": collection_name,
        "pocketbase_total_items": total_items,
        "task_number": settings.task_number,
        "target_records": settings.target_records,
        "expected_records": settings.target_records,
        "pocketbase_valid": total_items == settings.target_records,
        "mongo_database": settings.mongo_database,
        "mongo_connected": True,
        "fact_hotel_reservations_exists": "fact_hotel_reservations" in collections,
        "modified_data": False,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["pocketbase_valid"] or not report["fact_hotel_reservations_exists"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
