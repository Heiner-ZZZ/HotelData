from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

from src.etl.ga03_airflow_tasks import run_pipeline_03

LOCK_PATH = PROJECT_ROOT / "data" / "reports" / "pipeline_reservas_03.lock"


def acquire_lock() -> None:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        raise RuntimeError(f"Pipeline GA03 ya parece estar en ejecución. Lock: {LOCK_PATH}")
    LOCK_PATH.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "started_at": datetime.now(timezone.utc).isoformat(),
                "script": str(Path(__file__).resolve()),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def release_lock() -> None:
    if LOCK_PATH.exists():
        LOCK_PATH.unlink()


def main() -> None:
    acquire_lock()
    try:
        result = run_pipeline_03()
        print(result)
    finally:
        release_lock()


if __name__ == "__main__":
    main()
