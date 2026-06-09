from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings
from src.database.connection import get_database
from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS, build_ta02_dimensions
from src.etl.ta02_fact import transform_fact_hotel_reservations, utc_now_iso
from src.etl.ta02_load_mongodb import (
    collection_counts,
    create_ta02_indexes,
    insert_execution_report,
    insert_fact_hotel_reservations,
    insert_quality_report,
    insert_rejected_records,
    upsert_dimensions,
)


PARQUET_PATH = PROJECT_ROOT / "data" / "processed" / "pocketbase_sample.parquet"


def execution_id() -> str:
    return f"ta02_sample_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def main() -> None:
    if not PARQUET_PATH.exists():
        raise FileNotFoundError(f"No existe el Parquet de muestra: {PARQUET_PATH}")

    settings = get_settings()
    db = get_database()
    run_id = execution_id()
    loaded_at = utc_now_iso()

    print(f"Leyendo Parquet: {PARQUET_PATH}")
    dataframe = pd.read_parquet(PARQUET_PATH)
    print(f"Filas leidas desde Parquet: {len(dataframe)}")

    facts, rejected, valid_fact_frame = transform_fact_hotel_reservations(dataframe, run_id, loaded_at)
    dimensions = build_ta02_dimensions(valid_fact_frame, loaded_at)

    print("Transformacion completada.")
    print(f"Hechos validos: {len(facts)}")
    print(f"Registros rechazados: {len(rejected)}")
    print("Dimensiones generadas:")
    print(json.dumps({name: len(items) for name, items in dimensions.items()}, indent=2, ensure_ascii=False))

    create_ta02_indexes(db)
    dimension_write_counts = upsert_dimensions(db, dimensions)
    fact_count = insert_fact_hotel_reservations(db, facts)
    rejected_count = insert_rejected_records(db, rejected)

    source_rows = len(dataframe)
    quality_report = {
        "execution_id": run_id,
        "generated_at": loaded_at,
        "source": str(PARQUET_PATH),
        "source_rows": source_rows,
        "valid_fact_records": len(facts),
        "rejected_records": len(rejected),
        "completeness_score": round(len(facts) / source_rows, 4) if source_rows else 0,
        "dimensions": {name: len(items) for name, items in dimensions.items()},
    }
    execution_report = {
        "execution_id": run_id,
        "executed_at": loaded_at,
        "status": "success",
        "database": settings.mongo_database,
        "source": str(PARQUET_PATH),
        "loaded_collections": {
            **dimension_write_counts,
            "fact_hotel_reservations": fact_count,
            "rejected_records": rejected_count,
        },
    }
    insert_quality_report(db, quality_report)
    insert_execution_report(db, execution_report)

    collections = [
        *DIMENSION_KEY_FIELDS.keys(),
        "fact_hotel_reservations",
        "rejected_records",
        "etl_executions",
        "data_quality_reports",
    ]
    final_counts = collection_counts(db, collections)

    print("Carga MongoDB completada.")
    print("Conteos escritos en esta ejecucion:")
    print(json.dumps(execution_report["loaded_collections"], indent=2, ensure_ascii=False))
    print("Conteos finales por coleccion:")
    print(json.dumps(final_counts, indent=2, ensure_ascii=False))
    print(f"execution_id: {run_id}")


if __name__ == "__main__":
    main()
