# Criterios de aceptacion TA02

## Estado implementado

TA02 ya fue implementada y validada. Estos criterios describen el estado real que debe conservarse.

1. El DAG `hoteldata_ta02_reservations_pipeline` existe.
2. El DAG usa `PythonOperator`.
3. El DAG no contiene `BashOperator` para mover datos.
4. El DAG no importa `src.app`.
5. La fuente PocketBase real es `hotel_reservation_events__2`.
6. La extraccion genera `data/staging/pocketbase_full_extract.jsonl`.
7. La conversion genera `data/processed/hotel_reservations_full.parquet`.
8. La transformacion genera `data/processed/fact_hotel_reservations_ta02.jsonl`.
9. La transformacion genera `data/processed/rejected_records_ta02.jsonl`.
10. La transformacion genera dimensiones en `data/processed/ta02_dimensions/*.jsonl`.
11. MongoDB usa la base `hoteldata_hub`.
12. MongoDB contiene el hecho `fact_hotel_reservations`.
13. MongoDB contiene las 12 dimensiones TA02.
14. `fact_hotel_reservations` contiene `201000` registros cargados.
15. TA02 registra `0` rechazados.
16. `data/reports/ta02_execution_report.json` registra ejecucion `success`.
17. `data/reports/ta02_quality_report.json` registra `source_rows` 201000 y `valid_fact_records` 201000.
18. `data/reports/ta02_crud_validation_report.json` valida CRUD de hecho y dimensiones.
19. La web TA02 esta disponible en `/ta02`.
20. El CRUD visual esta disponible en `/ta02/crud`.
21. El API CRUD esta disponible bajo `/api/{collection_name}`.
22. Los listados CRUD no devuelven mas de 25 documentos por pagina.
