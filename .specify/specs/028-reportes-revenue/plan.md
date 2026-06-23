# Plan de Implementación: Reportes de Revenue

**Branch**: `028-reportes-revenue` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Dashboard (Angular)
  → GET /api/reports/revenue?periodo=...
    → services/reports.py
      → MongoDB aggregation sobre fact_hotel_reservations + dimensiones
      → KPIs: eventos, reservas, clicks, revenue, precio promedio
      → Top hoteles, destinos, países
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/reports/revenue/summary | Dashboard resumen con KPIs |
| GET | /api/reports/revenue/top-hotels | Top hoteles por revenue |
| GET | /api/reports/revenue/top-destinations | Top destinos por demanda |
| GET | /api/reports/revenue/conversion | Reporte de conversión por segmento |

## Fuentes

- `fact_hotel_reservations` (hechos)
- `dim_hotels`, `dim_destinations`, `dim_visitor_countries`, `dim_dates` (dimensiones)
- Aggregation pipeline con $lookup para joins
