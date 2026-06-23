# Plan de Implementación: ETL - Transformación de Dimensiones

**Branch**: `039-etl-dimensiones` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Parquet → build_ta02_dimensions() → Upsert a MongoDB
```

## Dimensiones

| Dimensión | Key Field | Tipo |
|-----------|-----------|------|
| dim_hotels | prop_id | Propiedades hoteleras |
| dim_destinations | srch_destination_id | Destinos |
| dim_visitor_countries | visitor_location_country_id | Países |
| dim_sites | site_id | Canales |
| dim_dates | date_key (YYYYMMDD) | Calendario |
| dim_promotions | promotion_flag | Flag |
| dim_click_status | click_bool | Flag |
| dim_reservation_status | reserva_bool | Flag |
| dim_occupancy_profile | occupancy_profile_id | Perfil ocupación |
| dim_stay_length_category | stay_length_category_id | Categoría estancia |
| dim_booking_window_category | booking_window_category_id | Ventana reserva |
| dim_price_category | price_category_id | Categoría precio |

## Reglas

- Upsert basado en key field (insert si no existe, update si existe)
- Carga incremental sin duplicados
- Módulo existente: `server/src/etl/ta02_dimensions.py`
