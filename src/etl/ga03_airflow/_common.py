from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests

from src.etl.ga03_airflow.config import pocketbase_config
from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS


def elapsed_ms(start: float | None) -> int:
    if start is None:
        return 0
    return int((time.perf_counter() - start) * 1000)


def request_with_retries(method: str, url: str, *, retries: int = 3, **kwargs):
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = requests.request(method, url, timeout=kwargs.pop("timeout", 60), **kwargs)
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Fallo request {method} {url}: {last_error}") from last_error


def auth_headers(config: dict[str, str | int | None]) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if config.get("auth_token"):
        headers["Authorization"] = f"Bearer {config['auth_token']}"
        return headers
    email = config.get("admin_email")
    password = config.get("admin_password")
    if email and password:
        session = requests.Session()
        response = session.post(
            f"{config['base_url']}/api/collections/_superusers/auth-with-password",
            json={"identity": email, "password": password},
            timeout=30,
        )
        response.raise_for_status()
        headers["Authorization"] = f"Bearer {response.json()['token']}"
    return headers


def iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, documents: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as target:
        for document in documents:
            target.write(json.dumps(document, ensure_ascii=False, default=_json_default) + "\n")
    return len(documents)


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as source:
        return sum(1 for line in source if line.strip())


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")


def reuse_existing_dimensions_enabled() -> bool:
    return os.getenv("GA03_REUSE_EXISTING_DIMENSIONS", "true").strip().lower() in {"1", "true", "yes", "on"}


def dimension_collection_counts(db) -> dict[str, int]:
    return {collection_name: db[collection_name].count_documents({}) for collection_name in DIMENSION_KEY_FIELDS}


def existing_dimensions_ready(db) -> tuple[bool, dict[str, int]]:
    counts = dimension_collection_counts(db)
    ready = bool(counts) and all(count > 0 for count in counts.values())
    return ready, counts
