# Plan de Implementación: Análisis de Mercados

**Branch**: `035-analisis-mercados` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Revenue Manager / Marketing
  → AnalisisMercadosPage
    → GET /api/reports/markets
      → Aggregation sobre fact_hotel_reservations
        → dim_visitor_countries (top países)
        → dim_destinations (top destinos)
        → dim_sites (canales)
        → dim_hotels (top propiedades)
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/reports/markets/visitors | Top países por eventos y conversión |
| GET | /api/reports/markets/destinations | Top destinos por demanda y revenue |
| GET | /api/reports/markets/channels | Distribución por canal (CTR, conversión) |
| GET | /api/reports/markets/top-hotels | Hoteles con mayor rendimiento |

## KPIs por dimensión

| Dimensión | KPIs |
|-----------|------|
| dim_visitor_countries | Eventos, reservas, conversión, revenue por país |
| dim_destinations | Búsquedas, revenue, precio promedio por destino |
| dim_sites | Eventos, clicks, CTR, reservas por canal |
| dim_hotels | Revenue, ocupación, rating por propiedad |
