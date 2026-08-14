"""Tests de la exportación .parquet por secciones del directorio Dato.

El pipeline M2C materializa sus tres secciones (Crudo / Procesado / Terminado)
como .parquet diarios fuera del proyecto, para trazabilidad y consumo por
herramientas externas sin tocar ClickHouse. Se prueban con directorios
temporales: no requieren MongoDB ni ClickHouse.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src.etl.mongo_to_clickhouse.parquet_export import (
    SECTIONS,
    export_procesado,
    export_section,
    record_dato_section,
    reset_dato_export,
    section_dir,
)


def test_sections_use_canonical_names():
    """Las secciones se llaman exactamente Crudo / Procesado / Terminado."""
    assert SECTIONS == ("Crudo", "Procesado", "Terminado")


def test_section_dir_creates_section_and_daily_subfolder(tmp_path):
    """``<base>/<Seccion>/<YYYY-MM-DD>`` se crea con la fecha diaria."""
    path = section_dir("Crudo", "2026-08-09", base_dir=tmp_path)
    assert path == tmp_path / "Crudo" / "2026-08-09"
    assert path.is_dir()


def test_section_dir_rejects_unknown_section(tmp_path):
    """Una sección no canónica es un error de contrato, no una carpeta nueva."""
    with pytest.raises(ValueError):
        section_dir("Bronce", "2026-08-09", base_dir=tmp_path)


def test_export_section_writes_one_parquet_per_table(tmp_path):
    """Crudo escribe un .parquet por tabla y devuelve los conteos."""
    payload = {
        "kpi_booking_daily": [
            {"date": "2026-08-09", "prop_id": 1, "bookings": 3},
        ],
        "kpi_inventory_daily": [
            {"date": "2026-08-09", "prop_id": 2, "available_rooms": 5},
        ],
    }
    counts = export_section("Crudo", payload, "2026-08-09", base_dir=tmp_path)
    assert counts == {"kpi_booking_daily": 1, "kpi_inventory_daily": 1}
    crudo = tmp_path / "Crudo" / "2026-08-09"
    assert (crudo / "kpi_booking_daily.parquet").exists()
    assert (crudo / "kpi_inventory_daily.parquet").exists()
    frame = pd.read_parquet(crudo / "kpi_booking_daily.parquet")
    assert frame.iloc[0]["prop_id"] == 1
    assert frame.iloc[0]["bookings"] == 3


def test_export_procesado_uses_table_columns_for_list_rows(tmp_path):
    """Las filas transformadas son listas posicionales; el parquet usa los nombres del contrato."""
    payload = {
        "kpi_inventory_daily": [
            ["2026-08-09", 7, "Hotel Siete", "RT-1", "Estándar", 4, 1, 5],
        ],
    }
    counts = export_procesado(payload, "2026-08-09", base_dir=tmp_path)
    assert counts == {"kpi_inventory_daily": 1}
    frame = pd.read_parquet(
        tmp_path / "Procesado" / "2026-08-09" / "kpi_inventory_daily.parquet"
    )
    assert list(frame.columns) == [
        "date", "prop_id", "hotel_label", "room_type_id", "room_type_label",
        "available_rooms", "blocked_rooms", "total_rooms",
    ]
    assert frame.iloc[0]["prop_id"] == 7
    assert frame.iloc[0]["total_rooms"] == 5


def test_empty_tables_do_not_generate_parquet(tmp_path):
    """Tablas sin filas no generan archivo vacío (evita .parquet sin esquema)."""
    payload = {
        "kpi_booking_daily": [],
        "kpi_review_daily": [{"date": "2026-08-09", "prop_id": 1, "reviews": 1}],
    }
    counts = export_section("Crudo", payload, "2026-08-09", base_dir=tmp_path)
    assert counts == {"kpi_review_daily": 1}
    crudo = tmp_path / "Crudo" / "2026-08-09"
    assert not (crudo / "kpi_booking_daily.parquet").exists()
    assert (crudo / "kpi_review_daily.parquet").exists()


def test_export_section_creates_terminado_section(tmp_path):
    """Terminado (salida final post-load) usa la misma estructura diaria."""
    payload = {
        "kpi_rate_daily": [{"date": "2026-08-09", "prop_id": 1, "published_rate": 99.5}],
    }
    counts = export_section("Terminado", payload, "2026-08-09", base_dir=tmp_path)
    assert counts == {"kpi_rate_daily": 1}
    terminado = tmp_path / "Terminado" / "2026-08-09"
    assert (terminado / "kpi_rate_daily.parquet").exists()
    frame = pd.read_parquet(terminado / "kpi_rate_daily.parquet")
    assert frame.iloc[0]["published_rate"] == 99.5


# ─── Registro de conteos por sección (m2c_dato_export.json) ────────────────


def test_record_dato_section_persists_counts_with_run_date(tmp_path):
    """Registrar una sección guarda sus conteos y la fecha diaria del run."""
    staging = tmp_path / "staging"
    record_dato_section(
        "Crudo",
        {"kpi_booking_daily": 3, "kpi_rate_daily": 1},
        "2026-08-09",
        staging_path=staging / "m2c_dato_export.json",
    )
    payload = json.loads((staging / "m2c_dato_export.json").read_text(encoding="utf-8"))
    assert payload["run_date"] == "2026-08-09"
    assert payload["sections"]["Crudo"] == {"kpi_booking_daily": 3, "kpi_rate_daily": 1}
    assert "generated_at" in payload


def test_record_dato_section_merges_across_sections(tmp_path):
    """Las tres secciones de una misma corrida conviven en el mismo registro."""
    staging = tmp_path / "staging"
    target = staging / "m2c_dato_export.json"
    record_dato_section("Crudo", {"kpi_booking_daily": 3}, "2026-08-09", staging_path=target)
    record_dato_section("Procesado", {"kpi_booking_daily": 2}, "2026-08-09", staging_path=target)
    record_dato_section("Terminado", {"kpi_booking_daily": 2}, "2026-08-09", staging_path=target)
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert set(payload["sections"].keys()) == {"Crudo", "Procesado", "Terminado"}
    assert payload["sections"]["Procesado"] == {"kpi_booking_daily": 2}
    assert payload["run_date"] == "2026-08-09"


def test_reset_dato_export_clears_previous_run(tmp_path):
    """Una corrida nueva arranca con secciones vacías (no mezcla corridas)."""
    staging = tmp_path / "staging"
    target = staging / "m2c_dato_export.json"
    record_dato_section("Crudo", {"kpi_booking_daily": 5}, "2026-08-08", staging_path=target)
    reset_dato_export("2026-08-09", staging_path=target)
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["run_date"] == "2026-08-09"
    assert payload["sections"] == {}
    assert "generated_at" in payload
