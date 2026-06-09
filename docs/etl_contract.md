# Contrato ETL estricto

El DAG `hoteldata_taf01_etl_pipeline` solo importa `src.etl`, `src.database` y `config`.

## Flujo

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

## Reglas

- No se usa `BashOperator`.
- Todo movimiento y transformacion de datos se hace en Python.
- MongoDB recibe colecciones ya transformadas.
- `fact_hotel_events` puede reconstruirse en carga completa.
- Las colecciones maestras no se borran durante el ETL.
- `system_catalogs` y `search_logs` no se borran durante el ETL.
- La web consulta MongoDB y no participa en el proceso ETL.
