# Plan de Implementación: Pipeline ETL

**Branch**: `033-pipeline-etl` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Airflow DAG: hoteldata_ga03_etl (14 tareas, PythonOperator)
  → Extraer desde PocketBase
  → Validar esquema
  → JSONL (staging)
  → Parquet (processed)
  → Transformar 12 dimensiones (upsert)
  → Transformar fact tables (batch insert 5k)
  → Generar reporte de calidad
```

## Tareas del DAG

| Tarea | Módulo | Propósito |
|-------|--------|-----------|
| extract_from_pocketbase | tasks.py | Extraer datos vía API |
| validate_schema | transform_clean.py | Validar columnas requeridas |
| convert_to_jsonl | tasks.py | Convertir a JSONL |
| convert_to_parquet | tasks.py | Convertir a Parquet |
| build_dimensions (8 tareas) | ta02_dimensions.py | Construir dimensiones |
| build_fact | ta02_fact.py | Construir fact table |
| load_to_mongodb | ta02_load_mongodb.py | Cargar a MongoDB |
| generate_quality_report | validate.py | Reporte de calidad |

## Reglas

- Solo PythonOperator (no BashOperator)
- Chunk size: 50k filas
- Batch insert: 5k documentos
- Reportes en data/reports/ + MongoDB
- Rejected records con razón exacta
