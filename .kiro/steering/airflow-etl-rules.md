# Reglas criticas de Airflow y ETL

El proyecto implementa ETL, no ELT. Todo movimiento de datos debe ejecutarse con Python.

## Reglas comunes

- Airflow solo puede importar modulos desde `src/etl`, `src/database` y `config`.
- Airflow no debe importar `src.app`.
- Airflow no debe importar templates, static, HTML, CSS ni JS.
- No usar `BashOperator` para mover datos.
- No usar cargas manuales hacia MongoDB como flujo principal.
- No transformar datos crudos dentro de MongoDB como paso principal.
- No usar MongoDB Aggregation Pipeline como transformacion principal del ETL.
- MongoDB `aggregate()` solo puede usarse en dashboard o consultas posteriores al ETL.

## Flujo TAF01 implementado

TAF01 conserva el flujo historico:

```text
CSV -> Transformacion Python -> MongoDB
```

Fuente esperada:
- `data/raw/hotels.csv`

DAG:
- `hoteldata_taf01_etl_pipeline`

Tareas esperadas:
1. `validate_environment`
2. `seed_master_collections_check`
3. `extract_csv`
4. `validate_schema`
5. `transform_fact_events`
6. `validate_master_keys`
7. `load_fact_events`
8. `load_rejected_records`
9. `create_indexes`
10. `save_execution_report`

## Flujo TA02 implementado

TA02 agrega el flujo real de reservas:

```text
PocketBase -> JSONL -> Parquet -> Dimensiones + Hecho -> MongoDB
```

Fuente:
- PocketBase collection `hotel_reservation_events__2`

Archivos reales:
- `data/staging/pocketbase_full_extract.jsonl`
- `data/processed/hotel_reservations_full.parquet`
- `data/processed/fact_hotel_reservations_ta02.jsonl`
- `data/processed/rejected_records_ta02.jsonl`
- `data/processed/ta02_dimensions/*.jsonl`

DAG:
- `hoteldata_ta02_reservations_pipeline`

Tareas reales:
1. `validate_environment`
2. `extract_from_pocketbase`
3. `save_pocketbase_extract`
4. `convert_to_parquet`
5. `validate_parquet_schema`
6. `transform_dimensions`
7. `transform_fact_reservations`
8. `load_dimensions_to_mongodb`
9. `load_fact_to_mongodb`
10. `create_indexes`
11. `run_quality_checks`
12. `save_execution_report`

Evidencia TA02:
- `data/reports/ta02_execution_report.json`
- `data/reports/ta02_quality_report.json`
- `data/reports/ta02_crud_validation_report.json`
