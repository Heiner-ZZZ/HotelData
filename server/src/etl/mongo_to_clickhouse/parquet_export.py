"""Exportación .parquet por secciones del directorio Dato (medallion táctico).

El pipeline M2C materializa sus tres secciones como .parquet diarios fuera del
proyecto, en ``<Dato>/<Seccion>/<YYYY-MM-DD>/<tabla>.parquet``:

- ``Crudo``      → salida de la extracción desde MongoDB (agregados tal cual).
- ``Procesado``  → filas transformadas/tipadas listas para ClickHouse.
- ``Terminado``  → producto final post-load (lo que quedó publicado).

La raíz ``Dato`` vive fuera del repo (``HOTELDATA_DATO_DIR`` en contenedores;
por defecto, la carpeta hermana ``Dato`` junto al proyecto en desarrollo local).
Cada sección se guarda en una subcarpeta por fecha diaria del run.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import get_settings
from src.etl.mongo_to_clickhouse._common import read_json_file, write_json_file
from src.etl.mongo_to_clickhouse.config import paths
from src.etl.mongo_to_clickhouse.transform import TABLE_COLUMNS

# Secciones canónicas del directorio Dato. Nombres exactos del contrato
# (Crudo / Procesado / Terminado): no renombrar ni traducir.
SECTIONS: tuple[str, ...] = ("Crudo", "Procesado", "Terminado")


def dato_root() -> Path:
    """Raíz del directorio Dato (configurable vía ``HOTELDATA_DATO_DIR``)."""
    return get_settings().dato_dir


def section_dir(
    section: str,
    run_date: str | None = None,
    *,
    base_dir: Path | None = None,
) -> Path:
    """Devuelve ``<base>/<Seccion>/<YYYY-MM-DD>`` y crea los directorios.

    ``run_date`` es la fecha diaria del run (``YYYY-MM-DD``); si no se pasa,
    se usa la fecha UTC actual. Solo acepta secciones canónicas.
    """
    if section not in SECTIONS:
        raise ValueError(
            f"Sección desconocida: {section!r} (válidas: {', '.join(SECTIONS)})"
        )
    day = run_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = (base_dir or dato_root()) / section / day
    path.mkdir(parents=True, exist_ok=True)
    return path


def _to_frame(table: str, rows: list[Any]):
    """Convierte filas a DataFrame con nombres de columna legibles.

    Las filas de ``Crudo`` son dicts (se infieren columnas); las de
    ``Procesado``/``Terminado`` son listas posicionales y usan el contrato
    ``TABLE_COLUMNS`` para que el parquet tenga nombres, no índices.
    """
    import pandas as pd

    if rows and isinstance(rows[0], dict):
        return pd.DataFrame.from_records(rows)
    columns = TABLE_COLUMNS.get(table)
    return pd.DataFrame(rows, columns=columns)


def export_section(
    section: str,
    payload: dict[str, list[Any]],
    run_date: str | None = None,
    *,
    base_dir: Path | None = None,
) -> dict[str, int]:
    """Escribe un .parquet por tabla dentro de ``<Seccion>/<run_date>/``.

    Devuelve ``{tabla: filas escritas}``. Las tablas sin filas no generan
    archivo (evita .parquet vacíos sin esquema).
    """
    out_dir = section_dir(section, run_date, base_dir=base_dir)
    counts: dict[str, int] = {}
    for table, rows in payload.items():
        if not rows:
            continue
        frame = _to_frame(table, rows)
        frame.to_parquet(out_dir / f"{table}.parquet", index=False)
        counts[table] = len(rows)
    return counts


def export_crudo(
    payload: dict[str, list[Any]],
    run_date: str | None = None,
    *,
    base_dir: Path | None = None,
) -> dict[str, int]:
    """Sección Crudo: salida de la extracción desde MongoDB."""
    return export_section("Crudo", payload, run_date, base_dir=base_dir)


def export_procesado(
    payload: dict[str, list[Any]],
    run_date: str | None = None,
    *,
    base_dir: Path | None = None,
) -> dict[str, int]:
    """Sección Procesado: filas transformadas listas para ClickHouse."""
    return export_section("Procesado", payload, run_date, base_dir=base_dir)


def export_terminado(
    payload: dict[str, list[Any]],
    run_date: str | None = None,
    *,
    base_dir: Path | None = None,
) -> dict[str, int]:
    """Sección Terminado: producto final post-load (lo publicado)."""
    return export_section("Terminado", payload, run_date, base_dir=base_dir)


def _dato_export_path(staging_path: Path | None) -> Path:
    return staging_path or paths()["dato_export_json"]


def _run_day(run_date: str | None) -> str:
    return run_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")


def reset_dato_export(
    run_date: str | None = None,
    *,
    staging_path: Path | None = None,
) -> dict[str, Any]:
    """Reinicia el registro de parquet al inicio de una corrida nueva.

    Evita mezclar secciones de corridas distintas: si un run falla a mitad,
    el registro solo contiene las secciones que esa corrida sí escribió.
    """
    payload: dict[str, Any] = {
        "run_date": _run_day(run_date),
        "sections": {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json_file(_dato_export_path(staging_path), payload)
    return payload


def record_dato_section(
    section: str,
    counts: dict[str, int],
    run_date: str | None = None,
    *,
    staging_path: Path | None = None,
) -> dict[str, Any]:
    """Persiste los conteos parquet de una sección para la UI de monitoreo.

    Merge por sección sobre el registro de la corrida actual
    (``m2c_dato_export.json``): Crudo/Procesado/Terminado conviven en el mismo
    archivo y la UI los muestra junto a la ruta del directorio Dato.
    """
    path = _dato_export_path(staging_path)
    previous = read_json_file(path)
    sections = previous.get("sections", {})
    sections[section] = dict(counts)
    payload = {
        **previous,
        "run_date": _run_day(run_date) or previous.get("run_date", ""),
        "sections": sections,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json_file(path, payload)
    return payload
