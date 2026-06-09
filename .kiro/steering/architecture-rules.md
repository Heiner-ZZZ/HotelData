# Arquitectura del proyecto

Estructura principal:

```text
config/
dags/
src/database/
src/etl/
src/app/
data/staging/
data/processed/
data/reports/
docs/
scripts/
tests/
```

## Responsabilidades

`dags/`
- Contiene solo DAGs de Airflow.
- Orquesta tareas ETL.
- No contiene logica web.
- DAG TAF01: `hoteldata_taf01_etl_pipeline`.
- DAG TA02: `hoteldata_ta02_reservations_pipeline`.

`src/etl/`
- Contiene la logica del proceso ETL.
- Puede ser importado por Airflow.
- Incluye modulos TAF01 y modulos TA02 `src/etl/ta02_*`.

`src/database/`
- Contiene conexion, indices y repositorios de MongoDB.
- Puede ser usado por ETL y por la web.

`src/app/`
- Contiene la aplicacion FastAPI.
- No puede ser importado por Airflow.
- Expone rutas generales de dashboard, registros, calidad, colecciones, empresa, problemas y auditoria.
- Expone TA02 en `/ta02`.
- Expone CRUD visual TA02 en `/ta02/crud`.
- Expone API CRUD TA02 en `/api/{collection_name}`.

`data/staging/`
- Contiene archivos intermedios de extraccion.
- TA02 usa `data/staging/pocketbase_full_extract.jsonl`.

`data/processed/`
- Contiene archivos transformados temporales.
- TA02 usa `data/processed/hotel_reservations_full.parquet`.
- TA02 usa `data/processed/fact_hotel_reservations_ta02.jsonl`.
- TA02 usa `data/processed/rejected_records_ta02.jsonl`.
- TA02 usa `data/processed/ta02_dimensions/*.jsonl`.

`data/reports/`
- Contiene evidencia de ejecucion, calidad y validaciones.
- TA02 conserva `ta02_execution_report.json`, `ta02_quality_report.json` y `ta02_crud_validation_report.json`.

`docs/`
- Contiene documentacion academica y tecnica.

MongoDB es el destino final de los datos transformados. La base real es `hoteldata_hub`.
