"""Regresión del lector de progreso de pipeline GA03.

El botón "Pipeline GA03" del monitoring escribe ``sections`` como LISTA de
``{key, label, complete}`` (``_write_pipeline_progress``), mientras el reader
``pipeline_progress`` asume un dict en ``{**default, **payload["sections"]}``.
Resultado: ``TypeError: 'list' object is not a mapping`` y 500 en
``/api/etl-status/consolidated`` mientras el archivo tiene la forma de lista.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.app.features.etl_status.services import progress_service


class _Settings:
    def __init__(self, reports_dir: Path) -> None:
        self.reports_dir = reports_dir
        self.target_records = 1000


def _write_progress(reports_dir: Path, sections: object) -> None:
    path = reports_dir / "progreso_pipeline_reservas_03.json"
    path.write_text(
        json.dumps(
            {
                "task_number": "03",
                "status": "running",
                "section": "extract",
                "percent": 10.0,
                "elapsed_ms": 100,
                "message": "running",
                "sections": sections,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )


def test_pipeline_progress_normalizes_legacy_list_sections(monkeypatch, tmp_path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    monkeypatch.setattr(progress_service, "get_settings", lambda: _Settings(reports_dir))
    _write_progress(
        reports_dir,
        [
            {"key": "extract", "label": "Extract", "complete": True},
            {"key": "parquet", "label": "Parquet", "complete": False},
            {"key": "transform", "label": "Transform", "complete": False},
            {"key": "mongodb", "label": "Carga MongoDB", "complete": False},
            {"key": "reports", "label": "Reportes", "complete": False},
        ],
    )

    result = progress_service.pipeline_progress()

    assert isinstance(result["sections"], dict)
    assert result["sections"]["extract"] == {"label": "Extract", "complete": True}
    # La lista legada usa "mongodb"; el contrato canónico es "load_mongodb".
    assert result["sections"]["load_mongodb"] == {"label": "Carga MongoDB", "complete": False}
    assert set(result["sections"]) == {"extract", "parquet", "transform", "load_mongodb", "reports"}


def test_write_pipeline_progress_emits_dict_sections(monkeypatch, tmp_path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    monkeypatch.setattr(progress_service, "get_settings", lambda: _Settings(reports_dir))

    progress_service._write_pipeline_progress("Pipeline solicitado", target_records=500)

    path = reports_dir / "progreso_pipeline_reservas_03.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload["sections"], dict)
    assert payload["sections"]["load_mongodb"] == {"label": "Carga MongoDB", "complete": False}
