# Modelo de colecciones

Coleccion de hechos reconstruible desde el dataset transaccional:

- `fact_hotel_events`

Colecciones maestras preservadas (12 dimensiones activas; fuente de verdad
`docs/ga03/diseno_base_datos_ga03.md`):

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

Colecciones dimensionales legadas (no eliminar, fuera de uso principal):

- `dim_countries`
- `dim_date`

Colecciones historicas y operativas:

- `data_quality_reports`
- `etl_executions`
- `search_logs`
- `rejected_records`
- `system_catalogs`
