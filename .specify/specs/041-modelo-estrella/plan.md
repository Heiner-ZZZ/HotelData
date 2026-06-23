# Plan de Implementación: Modelo Estrella

**Branch**: `041-modelo-estrella` | **Spec**: [spec.md](spec.md)

## Estructura

```
12 dimensiones (upsert)
  ← fact_hotel_reservations (batch insert, grain: sesión-búsqueda)
  ← fact_hotel_events (legacy TAF01)
  ← data_quality_reports (por ejecución)
  ← etl_executions (historial)
  ← rejected_records (rechazos)
```

## Integridad Referencial

- Todas las fact tables referencian dimensiones por key field
- Las dimensiones se cargan primero (upsert)
- Los hechos se cargan después con validación de foreign keys

## Colecciones MongoDB

### Dimensiones (12)
`dim_hotels`, `dim_destinations`, `dim_visitor_countries`, `dim_sites`, `dim_dates`, `dim_promotions`, `dim_click_status`, `dim_reservation_status`, `dim_occupancy_profile`, `dim_stay_length_category`, `dim_booking_window_category`, `dim_price_category`

### Fact tables (2 principales)
`fact_hotel_reservations`, `fact_hotel_events`

### Control
`data_quality_reports`, `etl_executions`, `rejected_records`
