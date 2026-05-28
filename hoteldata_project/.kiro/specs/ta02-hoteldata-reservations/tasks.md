# Tareas TA02 - HotelData Reservations

## Estado actual

TA02 esta implementada sobre HotelData Hub Analytics. Las tareas reflejan el estado real validado y no promesas futuras.

- [x] Crear spec TA02 en `.kiro/specs/ta02-hoteldata-reservations`.
- [x] Documentar empresa, modelo dimensional, casos, historias y UML.
- [x] Agregar configuracion PocketBase y Parquet.
- [x] Implementar extraccion PocketBase con Python.
- [x] Extraer desde PocketBase collection `hotel_reservation_events__2`.
- [x] Generar `data/staging/pocketbase_full_extract.jsonl`.
- [x] Convertir a `data/processed/hotel_reservations_full.parquet`.
- [x] Transformar hecho `fact_hotel_reservations`.
- [x] Transformar 12 dimensiones TA02.
- [x] Generar `data/processed/fact_hotel_reservations_ta02.jsonl`.
- [x] Generar `data/processed/rejected_records_ta02.jsonl`.
- [x] Generar dimensiones en `data/processed/ta02_dimensions/*.jsonl`.
- [x] Cargar dimensiones y `fact_hotel_reservations` a MongoDB `hoteldata_hub`.
- [x] Agregar DAG Airflow `hoteldata_ta02_reservations_pipeline` con `PythonOperator`.
- [x] Mantener restriccion de no usar `BashOperator`.
- [x] Mantener restriccion de no importar `src.app` desde Airflow.
- [x] Agregar indices MongoDB para el nuevo hecho y dimensiones.
- [x] Exponer CRUD paginado para hecho y dimensiones bajo `/api/{collection_name}`.
- [x] Integrar pantallas HTML especificas para administracion visual CRUD.
- [x] Exponer web TA02 en `/ta02`.
- [x] Exponer CRUD visual en `/ta02/crud`.
- [x] Ejecutar ETL completo contra PocketBase real.
- [x] Cargar `201000` registros en `fact_hotel_reservations`.
- [x] Confirmar `0` registros rechazados.
- [x] Registrar evidencia en `data/reports/ta02_execution_report.json`.
- [x] Registrar calidad en `data/reports/ta02_quality_report.json`.
- [x] Validar CRUD para hecho y dimensiones.
- [x] Registrar evidencia en `data/reports/ta02_crud_validation_report.json`.

## Evidencia

- Airflow TA02 ejecutado exitosamente.
- `fact_hotel_reservations`: `201000` registros.
- `rejected_records`: `0` registros para TA02.
- CRUD TA02 validado para listar, crear, actualizar, eliminar y buscar.
