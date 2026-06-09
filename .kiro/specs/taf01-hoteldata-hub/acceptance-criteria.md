# Criterios de aceptacion TAF01 - HotelData Hub Analytics

## Estado implementado

TAF01 se acepta como base historica ya implementada. Los criterios describen lo que existe o debe conservarse al extender el proyecto.

1. Existe el DAG `hoteldata_taf01_etl_pipeline`.
2. El DAG usa `PythonOperator`.
3. El DAG no usa `BashOperator` para mover datos.
4. El DAG no importa `src.app`, templates, static, HTML, CSS ni JS.
5. MongoDB usa la base `hoteldata_hub`.
6. El ETL registra ejecuciones en `etl_executions`.
7. El ETL registra calidad en `data_quality_reports`.
8. Los registros invalidos se registran en `rejected_records`.
9. La web FastAPI consulta MongoDB y no participa en el ETL principal.
10. TA02 debe documentarse como extension de TAF01, no como reemplazo destructivo de la arquitectura.
