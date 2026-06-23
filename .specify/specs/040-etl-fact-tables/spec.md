# Especificacion: ETL - Fact Tables

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T12 (Ejecutar y validar pipeline Airflow)

## 1. Objetivo

Transformar datos a fact tables con batch insert, validacion de calidad y rejected_records.

## 2. Fact Tables

| Fact Table | Grain | Coleccion |
|------------|-------|-----------|
| fact_hotel_reservations | 1 evento de busqueda | fact_hotel_reservations |
| fact_hotel_events | Evento legacy TAF01 | fact_hotel_events |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Cargar fact_hotel_reservations con batch insert de 5k documentos | Alta |
| RF-002 | Validar campos obligatorios: srch_id, date_key, prop_id, price_usd | Alta |
| RF-003 | Rechazar price_usd < 0, occupancy invalida, srch_id duplicados | Alta |
| RF-004 | Reportar conteos de insertados vs rechazados | Alta |

## 4. Dependencias

- server/src/etl/ta02_fact.py
- server/src/etl/validate.py
- Datos Parquet y dimensiones cargadas previamente
