from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

from config.settings import get_settings

DEFAULT_POCKETBASE_URL = "http://127.0.0.1:8090"
DEFAULT_COLLECTION = "hotel_reservation_events__2"
DEFAULT_PAGE_SIZE = 500
INSERT_BATCH_SIZE = 5000


def _paths() -> dict[str, Path]:
    settings = get_settings()
    dimension_dir = settings.processed_dir / "ta02_dimensions"
    return {
        "state": settings.staging_dir / "ta02_execution_state.json",
        "extract_jsonl": settings.staging_dir / "pocketbase_full_extract.jsonl",
        "parquet": settings.processed_dir / "hotel_reservations_full.parquet",
        "fact_jsonl": settings.processed_dir / "fact_hotel_reservations_ta02.jsonl",
        "rejected_jsonl": settings.processed_dir / "rejected_records_ta02.jsonl",
        "dimension_dir": dimension_dir,
        "quality_report": settings.reports_dir / "ta02_quality_report.json",
        "execution_report": settings.reports_dir / "ta02_execution_report.json",
    }


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _read_state() -> dict[str, Any]:
    state_path = _paths()["state"]
    if not state_path.exists():
        raise FileNotFoundError(f"No existe estado TA 02: {state_path}")
    return json.loads(state_path.read_text(encoding="utf-8"))


def _write_state(update: dict[str, Any]) -> dict[str, Any]:
    paths = _paths()
    paths["state"].parent.mkdir(parents=True, exist_ok=True)
    state = {}
    if paths["state"].exists():
        state = json.loads(paths["state"].read_text(encoding="utf-8"))
    state.update(update)
    paths["state"].write_text(json.dumps(state, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    return state


def _pocketbase_config() -> dict[str, str | int | None]:
    settings = get_settings()
    return {
        "base_url": os.getenv("POCKETBASE_URL", settings.pocketbase_url or DEFAULT_POCKETBASE_URL).rstrip("/"),
        "collection": os.getenv("POCKETBASE_COLLECTION", settings.pocketbase_collection or DEFAULT_COLLECTION),
        "page_size": int(os.getenv("POCKETBASE_PAGE_SIZE", str(DEFAULT_PAGE_SIZE))),
        "auth_token": os.getenv("POCKETBASE_AUTH_TOKEN") or settings.pocketbase_auth_token,
        "admin_email": os.getenv("POCKETBASE_ADMIN_EMAIL", "hzambranor@uteq.edu.ec"),
        "admin_password": os.getenv("POCKETBASE_ADMIN_PASSWORD", "Heiner2005*"),
    }


def _auth_headers(session: requests.Session, config: dict[str, str | int | None]) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if config.get("auth_token"):
        headers["Authorization"] = f"Bearer {config['auth_token']}"
        return headers

    email = config.get("admin_email")
    password = config.get("admin_password")
    if email and password:
        response = session.post(
            f"{config['base_url']}/api/collections/_superusers/auth-with-password",
            json={"identity": email, "password": password},
            timeout=30,
        )
        response.raise_for_status()
        headers["Authorization"] = f"Bearer {response.json()['token']}"
    return headers


def _write_jsonl(path: Path, documents: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as target:
        for document in documents:
            target.write(json.dumps(document, ensure_ascii=False, default=_json_default) + "\n")
    return len(documents)


def _iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as source:
        return sum(1 for line in source if line.strip())
