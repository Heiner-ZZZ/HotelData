# Especificacion: ETL - Transformacion de Dimensiones

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T12 (Ejecutar y validar pipeline Airflow)

## 1. Objetivo

Transformar datos a 12 dimensiones del modelo estrella con upsert.

## 2. Dimensiones

| Dimension | Key Field | Coleccion |
|-----------|-----------|-----------|
| dim_hotels | prop_id | dim_hotels |
| dim_destinations | srch_destination_id | dim_destinations |
| dim_visitor_countries | visitor_location_country_id | dim_visitor_countries |
| dim_sites | site_id | dim_sites |
| dim_dates | date_key (YYYYMMDD) | dim_dates |
| dim_promotions | promotion_flag | dim_promotions |
| dim_click_status | click_bool | dim_click_status |
| dim_reservation_status | reserva_bool | dim_reservation_status |
| dim_occupancy_profile | occupancy_profile_id | dim_occupancy_profile |
| dim_stay_length_category | stay_length_category_id | dim_stay_length_category |
| dim_booking_window_category | booking_window_category_id | dim_booking_window_category |
| dim_price_category | price_category_id | dim_price_category |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Construir y cargar las 12 dimensiones con upsert | Alta |
| RF-002 | No duplicar registros en operaciones upsert | Alta |

## 4. Dependencias

- server/src/etl/ta02_dimensions.py
- Datos Parquet del paso de ingesta
