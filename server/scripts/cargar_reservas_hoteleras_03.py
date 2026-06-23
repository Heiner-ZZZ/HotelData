from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


_computed_project_root = Path(__file__).resolve().parents[2]
_env_project_root = os.getenv("HOTELDATA_PROJECT_ROOT")
PROJECT_ROOT = Path(_env_project_root) if _env_project_root else _computed_project_root
SERVER_ROOT = PROJECT_ROOT / "server"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings


load_dotenv(PROJECT_ROOT / ".env")

TA02_COLLECTION_NAME = "hotel_reservation_events__2"
GENERIC_COLLECTION = os.getenv("POCKETBASE_COLLECTION")
COLLECTION_NAME = os.getenv("POCKETBASE_COLLECTION_03") or (
    GENERIC_COLLECTION
    if os.getenv("TASK_NUMBER", "03") == "03" and GENERIC_COLLECTION and GENERIC_COLLECTION != TA02_COLLECTION_NAME
    else "hotel_reservation_events_03"
)
DEFAULT_CSV = Path("C:/HotelData/data/processed/expedia_reservations_clean.csv")
BATCH_SIZE = 1000
PROGRESS_PATH = PROJECT_ROOT / "data" / "reports" / "progreso_preparacion_reservas_03.json"

TEXT_FIELDS = {"date_time"}
BOOL_FIELDS = {"prop_brand_bool", "promotion_flag", "click_bool", "reserva_bool"}
NUMBER_FIELDS = {
    "srch_id",
    "site_id",
    "visitor_location_country_id",
    "visitor_hist_starrating",
    "visitor_hist_adr_usd",
    "prop_country_id",
    "prop_id",
    "prop_starrating",
    "prop_review_score",
    "prop_location_score1",
    "price_usd",
    "srch_destination_id",
    "srch_length_of_stay",
    "srch_booking_window",
    "srch_adults_count",
    "srch_children_count",
    "srch_room_count",
    "reservas_brutas_usd",
}
EXPECTED_COLUMNS = [*sorted(NUMBER_FIELDS | BOOL_FIELDS | TEXT_FIELDS)]
OPTIONAL_FIELDS = {"visitor_hist_starrating", "visitor_hist_adr_usd", "prop_review_score"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Carga semilla GA03 hacia PocketBase.")
    parser.add_argument("--csv", default=os.getenv("GA03_SOURCE_CSV", str(DEFAULT_CSV)), help="CSV limpio de reservas.")
    parser.add_argument("--reload", action="store_true", help="Borra y recarga solo hotel_reservation_events_03.")
    parser.add_argument("--confirm-reload", default="", help="Debe ser hotel_reservation_events_03 para permitir --reload.")
    parser.add_argument("--target", type=int, default=0, help="Registros a cargar (0 = usa TARGET_RECORDS).")
    return parser.parse_args()


def csv_path_candidates(path_value: str) -> list[Path]:
    raw_candidates = [
        path_value,
        str(PROJECT_ROOT / "data" / "uploads" / "ga03_source.csv"),
        str(PROJECT_ROOT / "data" / "processed" / "expedia_reservations_clean.csv"),
        str(PROJECT_ROOT.parent / "data" / "processed" / "expedia_reservations_clean.csv"),
        "/HotelData/data/processed/expedia_reservations_clean.csv",
        "C:/HotelData/data/processed/expedia_reservations_clean.csv",
        "/mnt/c/HotelData/data/processed/expedia_reservations_clean.csv",
    ]
    extra_candidates = os.getenv("GA03_SOURCE_CSV_CANDIDATES", "")
    if extra_candidates:
        raw_candidates.extend(candidate.strip() for candidate in extra_candidates.split(";") if candidate.strip())

    candidates: list[Path] = []
    seen: set[str] = set()
    for raw_candidate in raw_candidates:
        if not raw_candidate:
            continue
        candidate = Path(raw_candidate)
        key = str(candidate)
        if key not in seen:
            candidates.append(candidate)
            seen.add(key)
        if len(raw_candidate) > 2 and raw_candidate[1:3] == ":/":
            drive = raw_candidate[0].lower()
            rest = raw_candidate[3:]
            wsl_candidate = Path(f"/mnt/{drive}") / rest
            key = str(wsl_candidate)
            if key not in seen:
                candidates.append(wsl_candidate)
                seen.add(key)
    return candidates


def resolve_available_path(path_value: str) -> Path:
    candidates = csv_path_candidates(path_value)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    attempted = "\n".join(f"- {candidate}" for candidate in candidates)
    raise FileNotFoundError(f"No existe CSV GA03. Rutas revisadas:\n{attempted}")


def write_progress(
    *,
    status: str,
    loaded: int,
    target: int,
    batch_number: int = 0,
    last_batch_records: int = 0,
    csv_path: Path | None = None,
    message: str = "",
) -> None:
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    remaining = max(target - loaded, 0)
    percent = round((loaded / target) * 100, 2) if target else 0
    payload = {
        "task_number": "03",
        "collection": COLLECTION_NAME,
        "status": status,
        "loaded_records": loaded,
        "target_records": target,
        "remaining_records": remaining,
        "percent": percent,
        "last_batch_number": batch_number,
        "last_batch_records": last_batch_records,
        "csv_path": str(csv_path) if csv_path else "",
        "message": message,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    tmp = PROGRESS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.rename(PROGRESS_PATH)


def authenticate(base_url: str) -> dict[str, str]:
    token = os.getenv("POCKETBASE_AUTH_TOKEN")
    if token:
        return {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    email = os.getenv("POCKETBASE_ADMIN_EMAIL")
    password = os.getenv("POCKETBASE_ADMIN_PASSWORD")
    if not email or not password:
        raise RuntimeError("Faltan POCKETBASE_ADMIN_EMAIL/POCKETBASE_ADMIN_PASSWORD o POCKETBASE_AUTH_TOKEN")
    response = requests.post(
        f"{base_url}/api/collections/_superusers/auth-with-password",
        json={"identity": email, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return {"Accept": "application/json", "Authorization": f"Bearer {response.json()['token']}"}


def field_schema(name: str) -> dict[str, Any]:
    if name in TEXT_FIELDS:
        return {"name": name, "type": "text", "required": name not in OPTIONAL_FIELDS, "options": {"max": 5000}}
    if name in BOOL_FIELDS:
        return {"name": name, "type": "bool", "required": False, "options": {}}
    return {"name": name, "type": "number", "required": False, "options": {"min": None, "max": None, "noDecimal": False}}


def get_collection(base_url: str, headers: dict[str, str], collection_name: str) -> dict[str, Any] | None:
    response = requests.get(f"{base_url}/api/collections/{collection_name}", headers=headers, timeout=30)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def create_collection(base_url: str, headers: dict[str, str]) -> None:
    fields_schema = [field_schema(name) for name in EXPECTED_COLUMNS]
    payload = {
        "name": COLLECTION_NAME,
        "type": "base",
        "listRule": None,
        "viewRule": None,
        "createRule": None,
        "updateRule": None,
        "deleteRule": None,
        "schema": fields_schema,
    }
    response = requests.post(f"{base_url}/api/collections", headers=headers, json=payload, timeout=30)
    if response.status_code != 200:
        print(f"Create collection error: {response.status_code} {response.text[:500]}")
    response.raise_for_status()
    print(f"Coleccion creada: {COLLECTION_NAME}")


def ensure_collection(base_url: str, headers: dict[str, str]) -> None:
    collection = get_collection(base_url, headers, COLLECTION_NAME)
    if collection is None:
        create_collection(base_url, headers)
        collection = get_collection(base_url, headers, COLLECTION_NAME)
    if collection is None:
        raise RuntimeError(f"No se pudo crear {COLLECTION_NAME}")
    field_names = {field["name"] for field in collection.get("schema", collection.get("fields", []))}
    missing = [name for name in EXPECTED_COLUMNS if name not in field_names]
    if missing:
        raise RuntimeError(f"Coleccion {COLLECTION_NAME} sin campos requeridos: {missing}")


def count_records(base_url: str, headers: dict[str, str]) -> int:
    response = requests.get(
        f"{base_url}/api/collections/{COLLECTION_NAME}/records",
        params={"page": 1, "perPage": 1},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return int(response.json().get("totalItems", 0) or 0)


def delete_all_records(base_url: str, headers: dict[str, str]) -> None:
    while True:
        response = requests.get(
            f"{base_url}/api/collections/{COLLECTION_NAME}/records",
            params={"page": 1, "perPage": 500},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
        if not items:
            break
        batch = [{"method": "DELETE", "url": f"/api/collections/{COLLECTION_NAME}/records/{item['id']}"} for item in items]
        batch_response = requests.post(f"{base_url}/api/batch", json={"requests": batch}, headers=headers, timeout=60)
        batch_response.raise_for_status()
        print(f"Eliminados {len(items)} registros de {COLLECTION_NAME}")


def validate_csv(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe CSV GA03: {path}")
    columns = pd.read_csv(path, nrows=0).columns.tolist()
    missing = [column for column in EXPECTED_COLUMNS if column not in columns]
    if missing:
        raise RuntimeError(f"CSV sin columnas requeridas GA03: {missing}")


def clean_value(field: str, value: Any) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if field in BOOL_FIELDS:
        return bool(int(value)) if not isinstance(value, bool) else value
    if field in NUMBER_FIELDS:
        return float(value)
    return str(value)


def batch_create(base_url: str, headers: dict[str, str], rows: list[dict[str, Any]]) -> None:
    requests_batch = []
    for row in rows:
        payload = {field: clean_value(field, row.get(field)) for field in EXPECTED_COLUMNS}
        requests_batch.append({"method": "POST", "url": f"/api/collections/{COLLECTION_NAME}/records", "body": payload})
    response = requests.post(f"{base_url}/api/batch", json={"requests": requests_batch}, headers=headers, timeout=120)
    if response.status_code not in {200, 204}:
        raise RuntimeError(f"Lote rechazado por PocketBase: {response.status_code} {response.text}")


def main() -> None:
    args = parse_args()
    settings = get_settings()
    meta_pb = int(os.getenv("META_PB", "0"))
    expected = args.target if args.target > 0 else (meta_pb if meta_pb > 0 else settings.target_records)
    csv_path: Path | None = None
    loaded = 0
    batch_number = 0
    try:
        base_url = settings.pocketbase_url.rstrip("/")
        csv_path = resolve_available_path(args.csv)
        write_progress(
            status="running",
            loaded=0,
            target=expected,
            csv_path=csv_path,
            message="Preparación GA03 iniciada.",
        )
        if COLLECTION_NAME == TA02_COLLECTION_NAME:
            raise RuntimeError("La coleccion destino GA03 no puede apuntar a la coleccion TA02")
        headers = authenticate(base_url)
        validate_csv(csv_path)
        ensure_collection(base_url, headers)
        current = count_records(base_url, headers)
        loaded = current
        write_progress(
            status="running",
            loaded=loaded,
            target=expected,
            csv_path=csv_path,
            message="Colección verificada.",
        )
        if args.reload:
            if args.confirm_reload != COLLECTION_NAME:
                raise RuntimeError(f"Para --reload use --confirm-reload {COLLECTION_NAME}")
            delete_all_records(base_url, headers)
            current = 0
            loaded = 0
            write_progress(
                status="running",
                loaded=loaded,
                target=expected,
                csv_path=csv_path,
                message="Recarga confirmada. Colección limpiada.",
            )
        if current == expected:
            write_progress(
                status="completed",
                loaded=expected,
                target=expected,
                csv_path=csv_path,
                message=f"{COLLECTION_NAME} ya contiene {expected} registros.",
            )
            print(f"{COLLECTION_NAME} ya contiene {expected} registros. No se insertan duplicados.")
            return
        if current > expected:
            raise RuntimeError(f"{COLLECTION_NAME} tiene {current} registros, supera esperado {expected}. No se borra sin --reload.")
        if current > 0:
            raise RuntimeError(
                f"{COLLECTION_NAME} ya tiene {current} registros. "
                "Para evitar duplicados, use --reload con confirmacion. "
                "La continuacion parcial queda bloqueada porque no se puede garantizar duplicados cero."
            )
        print(
            "Preparando fuente operacional: "
            f"task_number={settings.task_number}, collection={COLLECTION_NAME}, actual={current}, target_records={expected}"
        )
        remaining = expected - current
        csv_iter = pd.read_csv(csv_path, chunksize=BATCH_SIZE, skiprows=range(1, current + 1))
        for chunk in csv_iter:
            if remaining <= 0:
                break
            chunk = chunk.head(min(len(chunk), remaining))
            batch_create(base_url, headers, chunk.to_dict("records"))
            loaded += len(chunk)
            remaining -= len(chunk)
            batch_number += 1
            write_progress(
                status="running",
                loaded=loaded,
                target=expected,
                batch_number=batch_number,
                last_batch_records=len(chunk),
                csv_path=csv_path,
                message=f"Último lote cargado: {len(chunk)} registros.",
            )
            print(f"[GA03 BATCH OK] Registros en PocketBase: {loaded}", flush=True)
        final_count = count_records(base_url, headers)
        if final_count != expected:
            raise RuntimeError(f"Carga GA03 incompleta: final={final_count}, esperado={expected}")
        write_progress(
            status="completed",
            loaded=final_count,
            target=expected,
            batch_number=batch_number,
            csv_path=csv_path,
            message="Preparación GA03 completada.",
        )
        print(json.dumps({"collection": COLLECTION_NAME, "totalItems": final_count}, indent=2, ensure_ascii=False))
    except Exception as exc:
        write_progress(
            status="failed",
            loaded=loaded,
            target=expected,
            batch_number=batch_number,
            csv_path=csv_path,
            message=str(exc),
        )
        raise


if __name__ == "__main__":
    main()
