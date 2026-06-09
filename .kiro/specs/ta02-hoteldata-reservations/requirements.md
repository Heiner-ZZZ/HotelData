# Requisitos TA02 - HotelData Reservations

## Estado real consolidado TAF01 + TA02

TA02 extiende HotelData Hub Analytics sobre la base historica TAF01. No crea un proyecto independiente. TA02 agrega analitica de reservas hoteleras desde PocketBase, Parquet obligatorio, modelo dimensional, DAG Airflow propio, CRUD de hecho/dimensiones y evidencia de ejecucion real.

TAF01 conserva el flujo CSV hacia MongoDB y el DAG `hoteldata_taf01_etl_pipeline`. TA02 agrega el flujo:

```text
PocketBase -> JSONL -> Parquet -> Dimensiones + Hecho -> MongoDB
```

## Datos reales TA02

- Proyecto: HotelData Hub Analytics.
- Base MongoDB: `hoteldata_hub`.
- Fuente: PocketBase.
- Coleccion PocketBase: `hotel_reservation_events__2`.
- JSONL: `data/staging/pocketbase_full_extract.jsonl`.
- Parquet: `data/processed/hotel_reservations_full.parquet`.
- Hecho procesado: `data/processed/fact_hotel_reservations_ta02.jsonl`.
- Rechazados procesados: `data/processed/rejected_records_ta02.jsonl`.
- Dimensiones procesadas: `data/processed/ta02_dimensions/*.jsonl`.
- DAG Airflow: `hoteldata_ta02_reservations_pipeline`.
- Hecho MongoDB: `fact_hotel_reservations`.
- Registros extraidos/cargados: `201000`.
- Registros rechazados: `0`.
- Web TA02: `/ta02`.
- CRUD visual: `/ta02/crud`.
- API CRUD: `/api/{collection_name}`.

## Requisitos funcionales implementados

### RF01 - Extraer desde PocketBase
El sistema extrae registros desde PocketBase usando Python, variables `POCKETBASE_URL`, `POCKETBASE_COLLECTION`, paginacion y autenticacion cuando corresponde.

### RF02 - Persistir JSONL
El sistema guarda el dataset extraido en `data/staging/pocketbase_full_extract.jsonl`.

### RF03 - Convertir a Parquet
El sistema convierte el JSONL a `data/processed/hotel_reservations_full.parquet` antes de cargar MongoDB.

### RF04 - Transformar modelo dimensional
El sistema limpia tipos, crea `date_key`, conserva indicadores `click_bool` y `reserva_bool`, calcula `reservas_brutas_usd` y deriva categorias de precio, estancia, anticipacion y perfil de ocupacion.

### RF05 - Cargar hecho y dimensiones en MongoDB
El sistema carga el hecho `fact_hotel_reservations` y 12 dimensiones reales:
- `dim_hotels`
- `dim_destinations`
- `dim_visitor_countries`
- `dim_sites`
- `dim_dates`
- `dim_promotions`
- `dim_click_status`
- `dim_reservation_status`
- `dim_occupancy_profile`
- `dim_stay_length_category`
- `dim_booking_window_category`
- `dim_price_category`

### RF06 - Registrar control operativo
El sistema guarda registros rechazados, ejecuciones ETL y reportes de calidad en `rejected_records`, `etl_executions` y `data_quality_reports`.

### RF07 - Orquestar con Airflow
Airflow usa `PythonOperator` y funciones de `src.etl`. No usa `BashOperator` para mover datos y no importa `src.app`.

### RF08 - Exponer CRUD paginado
FastAPI expone CRUD paginado para `fact_hotel_reservations` y todas las dimensiones TA02 bajo `/api/{collection_name}`.

### RF09 - Mostrar interfaz empresarial TA02
La web muestra TA02 en `/ta02` y el CRUD visual en `/ta02/crud`.

## Campos principales del hecho TA02

- `source_record_id`
- `srch_id`
- `date_time`
- `date_key`
- `site_id`
- `visitor_location_country_id`
- `prop_country_id`
- `prop_id`
- `price_usd`
- `promotion_flag`
- `click_bool`
- `reserva_bool`
- `reservas_brutas_usd`
- `srch_destination_id`
- `srch_length_of_stay`
- `srch_booking_window`
- `srch_adults_count`
- `srch_children_count`
- `srch_room_count`
- `occupancy_profile_id`
- `stay_length_category_id`
- `booking_window_category_id`
- `price_category_id`
- `loaded_at`
- `execution_id`

## Requisitos no funcionales

- MongoDB es la unica base final.
- Python ejecuta extraccion, conversion, transformacion y carga.
- Airflow no usa `BashOperator` para mover datos.
- Airflow no importa `src.app`.
- Los listados CRUD TA02 usan paginacion con maximo real de 25 documentos por pagina.
- MongoDB tiene indices sobre claves del hecho, dimensiones, ejecucion y auditoria.
- La documentacion debe distinguir estado actual, evidencia real y relacion con TAF01.
