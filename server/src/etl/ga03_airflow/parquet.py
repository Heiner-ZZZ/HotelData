from __future__ import annotations

from typing import Any

import pandas as pd

from src.etl.ga03_airflow._common import file_sha256, read_json_file, write_json_file
from src.etl.ga03_airflow.config import PIPELINE_PROGRESS_STEPS, paths
from src.etl.ga03_airflow.progress import write_pipeline_progress, read_state, write_state
from src.etl.ga03_audit import utc_now_iso
from src.etl.ta02_fact import REQUIRED_FACT_COLUMNS


def convert_to_parquet_03() -> dict[str, Any]:
    all_paths = paths()
    if not all_paths["extract_jsonl"].exists():
        raise FileNotFoundError(f"No existe JSONL GA03: {all_paths['extract_jsonl']}")
    state = read_state()
    expected = int(state["expected_records"])
    extract_report = state.get("extract_report", {})
    parquet_meta = read_json_file(all_paths["parquet_meta"])
    parquet_cache_valid = (
        all_paths["parquet"].exists()
        and parquet_meta.get("jsonl_sha256") == extract_report.get("jsonl_sha256")
        and int(parquet_meta.get("records", 0) or 0) == expected
        and parquet_meta.get("collection") == extract_report.get("collection")
    )
    if parquet_cache_valid:
        report = {
            "records": parquet_meta["records"],
            "columns": parquet_meta.get("columns", []),
            "parquet_path": str(all_paths["parquet"]),
            "parquet_sha256": parquet_meta.get("parquet_sha256"),
            "cached": True,
        }
        write_pipeline_progress(
            status="running",
            section="parquet",
            percent=PIPELINE_PROGRESS_STEPS["parquet"],
            message="Parquet existente validado y reutilizado.",
            detail=report,
        )
        write_state({"parquet_report": report})
        return report
    write_pipeline_progress(
        status="running",
        section="parquet",
        percent=35,
        message="Convirtiendo JSONL a Parquet.",
        detail={"jsonl_path": str(all_paths["extract_jsonl"])},
    )
    frames = []
    try:
        for chunk in pd.read_json(all_paths["extract_jsonl"], lines=True, dtype=False, chunksize=50000):
            frames.append(chunk)
    except ValueError as exc:
        raise ValueError(
            "JSONL GA03 inválido. Vuelva a ejecutar el pipeline para regenerar "
            f"{all_paths['extract_jsonl']} desde PocketBase."
        ) from exc
    if not frames:
        raise ValueError(f"JSONL GA03 vacío: {all_paths['extract_jsonl']}")
    dataframe = pd.concat(frames, ignore_index=True)
    dataframe.to_parquet(all_paths["parquet"], index=False, compression="snappy")
    parquet_sha256 = file_sha256(all_paths["parquet"])
    report = {
        "records": len(dataframe),
        "columns": list(dataframe.columns),
        "parquet_path": str(all_paths["parquet"]),
        "parquet_sha256": parquet_sha256,
        "cached": False,
    }
    if len(dataframe) != expected:
        raise ValueError(f"Parquet GA03 debe tener {expected} filas, actual={len(dataframe)}")
    write_json_file(
        all_paths["parquet_meta"],
        {
            "records": len(dataframe),
            "columns": list(dataframe.columns),
            "parquet_path": str(all_paths["parquet"]),
            "parquet_sha256": parquet_sha256,
            "jsonl_sha256": extract_report.get("jsonl_sha256"),
            "collection": extract_report.get("collection"),
            "expected_records": expected,
            "created_at": utc_now_iso(),
        },
    )
    write_pipeline_progress(
        status="running",
        section="parquet",
        percent=PIPELINE_PROGRESS_STEPS["parquet"],
        message="Parquet generado.",
        detail={"records": len(dataframe), "parquet_path": str(all_paths["parquet"])},
    )
    write_state({"parquet_report": report})
    return report


def validate_parquet_schema_03() -> dict[str, Any]:
    all_paths = paths()
    dataframe = pd.read_parquet(all_paths["parquet"])
    missing = [column for column in REQUIRED_FACT_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Parquet GA03 sin columnas requeridas: {missing}")
    expected = int(read_state()["expected_records"])
    if len(dataframe) != expected:
        raise ValueError(f"Parquet GA03 esperado={expected}, actual={len(dataframe)}")
    report = {"valid": True, "records": len(dataframe), "columns": list(dataframe.columns)}
    write_state({"schema_report": report})
    write_pipeline_progress(
        status="running",
        section="transform",
        percent=PIPELINE_PROGRESS_STEPS.get("parquet", 50),
        message="Esquema de Parquet validado correctamente.",
        detail=report,
    )
    return report
