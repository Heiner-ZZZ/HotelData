"""Helpers compartidos del pipeline mongo_to_clickhouse.

Replican los patrones de ``ga03_airflow/_common.py`` (estado atómico, reportes
JSON, helpers de tiempo) SIN importar de GA03 — para mantener los paquetes
desacoplados por decisión de diseño (ver docs/PLAN_ETL_MONGO_TO_CLICKHOUSE.md).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def elapsed_ms(start: float | None) -> int:
    if start is None:
        return 0
    return int((time.perf_counter() - start) * 1000)


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
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )


class AtomicJsonState:
    """Estado de ejecución con escritura atómica (tmp + replace)."""

    def __init__(self, path: Path):
        self.path = path

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            raise FileNotFoundError(f"No existe archivo de estado: {self.path}")
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write(self, update: dict[str, Any]) -> dict[str, Any]:
        state: dict[str, Any] = {}
        if self.path.exists():
            state = json.loads(self.path.read_text(encoding="utf-8"))
        state.update(update)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(state, indent=2, ensure_ascii=False, default=_json_default),
            encoding="utf-8",
        )
        tmp.replace(self.path)
        return state
