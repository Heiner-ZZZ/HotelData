# Especificacion: Modelo Estrella

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: Todos los CU analiticos

## 1. Objetivo

Diseno del modelo estrella con 12 dimensiones y 5 fact tables.

## 2. Estructura

### Fact Tables (5)
fact_hotel_reservations, fact_hotel_events, data_quality_reports, etl_executions, rejected_records

### Dimensiones (12)
dim_hotels, dim_destinations, dim_visitor_countries, dim_sites, dim_dates, dim_promotions, dim_click_status, dim_reservation_status, dim_occupancy_profile, dim_stay_length_category, dim_booking_window_category, dim_price_category

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Mantener 12 dimensiones con upsert y key fields | Alta |
| RF-002 | Mantener fact_hotel_reservations como fact table principal | Alta |
| RF-003 | Asegurar integridad referencial | Alta |

## 4. Dependencias

- Colecciones: 12 dim_*, fact_hotel_reservations, fact_hotel_events
- Modulos: src/etl/ta02_dimensions.py, src/etl/ta02_fact.py
