from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from config.settings import get_settings
from src.app.features.etl_status.services.progress_service import (
    preparation_progress,
    pipeline_progress,
)


def _csv_path_candidates(path_value: str) -> list[Path]:
    settings = get_settings()
    raw_candidates = [
        path_value,
        str(settings.project_root / "data" / "uploads" / "ga03_source.csv"),
        str(settings.project_root / "data" / "processed" / "expedia_reservations_clean.csv"),
        str(settings.project_root.parent / "data" / "processed" / "expedia_reservations_clean.csv"),
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


def _resolve_available_path(path_value: str) -> tuple[Path, list[Path]]:
    candidates = _csv_path_candidates(path_value)
    for candidate in candidates:
        if candidate.exists():
            return candidate, candidates
    return candidates[0], candidates


def _pocketbase_headers() -> dict[str, str]:
    token = os.getenv("POCKETBASE_AUTH_TOKEN")
    if token:
        return {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    settings = get_settings()
    email = os.getenv("POCKETBASE_ADMIN_EMAIL")
    password = os.getenv("POCKETBASE_ADMIN_PASSWORD")
    if not email or not password:
        return {"Accept": "application/json"}
    response = requests.post(
        f"{settings.pocketbase_url.rstrip('/')}/api/collections/_superusers/auth-with-password",
        json={"identity": email, "password": password},
        timeout=5,
    )
    response.raise_for_status()
    return {"Accept": "application/json", "Authorization": f"Bearer {response.json()['token']}"}


def config_status() -> dict:
    settings = get_settings()
    configured_source_csv = os.getenv("GA03_SOURCE_CSV", "C:/HotelData/data/processed/expedia_reservations_clean.csv")
    upload_path = settings.project_root / "data" / "uploads" / "ga03_source.csv"
    source_csv = str(upload_path) if upload_path.exists() else configured_source_csv
    resolved_source_csv, source_csv_candidates = _resolve_available_path(source_csv)

    prep_progress = preparation_progress()
    pipeline_progress_data = pipeline_progress()
    target_pb = prep_progress.get("target_records", settings.target_records)
    target_mongo = pipeline_progress_data.get("target_records", settings.target_records)

    return {
        "task_number": settings.task_number,
        "target_records": settings.target_records,
        "target_records_pb": target_pb,
        "target_records_mongo": target_mongo,
        "pocketbase_collection": settings.pocketbase_collection_03,
        "source_csv": source_csv,
        "source_csv_configured": configured_source_csv,
        "uploaded_source_csv": str(upload_path),
        "uploaded_source_csv_exists": upload_path.exists(),
        "source_csv_resolved": str(resolved_source_csv),
        "source_csv_candidates": [str(candidate) for candidate in source_csv_candidates],
        "source_csv_exists": resolved_source_csv.exists(),
        "full_reload_facts": os.getenv("GA03_FULL_RELOAD_FACTS", "true").lower() == "true",
    }


def pocketbase_status() -> dict:
    settings = get_settings()
    collection = settings.pocketbase_collection_03
    progress_path = settings.reports_dir / "progreso_preparacion_reservas_03.json"
    if progress_path.exists():
        try:
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            target = int(progress.get("target_records", 0) or 0)
        except (json.JSONDecodeError, ValueError, OSError):
            target = 0
    else:
        target = 0
    if target <= 0:
        target = settings.target_records
    if collection == "hotel_reservation_events__2":
        return {
            "available": False,
            "collection": collection,
            "count": None,
            "state": "error",
            "message": "La colección GA03 no puede apuntar a hotel_reservation_events__2.",
        }
    try:
        headers = _pocketbase_headers()
        response = requests.get(
            f"{settings.pocketbase_url.rstrip('/')}/api/collections/{collection}/records",
            params={"page": 1, "perPage": 1},
            headers=headers,
            timeout=5,
        )
        response.raise_for_status()
        count = int(response.json().get("totalItems", 0) or 0)
    except requests.HTTPError as exc:
        detail = str(exc)
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 404:
            message = "Colección GA03 no creada todavía. Prepare la fuente para crearla."
            state = "not_found"
        else:
            message = "No disponible."
            state = "unavailable"
        return {
            "available": False,
            "collection": collection,
            "count": None,
            "state": state,
            "message": message,
            "technical_detail": detail,
        }
    except Exception as exc:
        return {
            "available": False,
            "collection": collection,
            "count": None,
            "state": "unavailable",
            "message": "No disponible.",
            "technical_detail": str(exc),
        }

    if count >= target:
        state = "ready"
        message = "Fuente lista."
    elif count < target:
        state = "incomplete"
        message = "Fuente incompleta."
    return {
        "available": True,
        "collection": collection,
        "count": count,
        "target_records": target,
        "state": state,
        "message": message,
    }
