# Plan de Implementación: Balanced Scorecard

**Branch**: `034-balanced-scorecard` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Gerente General
  → BSCPage (4 perspectivas con KPIs, semáforos, tendencias)
    → GET /api/reports/bsc
      → services/bsc.py
        → fact_hotel_reservations (aggregation)
        → dim_* dimensions
```

## KPIs por Perspectiva

| Perspectiva | KPIs |
|-------------|------|
| Financiera | Revenue bruto, precio promedio, CAC |
| Cliente | Tasa de conversión, CTR, reseñas promedio, NPS |
| Procesos Internos | Ejecuciones ETL exitosas, registros rechazados, uptime |
| Aprendizaje | Cobertura de integraciones, adopción de módulos |

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/reports/bsc | Balanced Scorecard completo |
| GET | /api/reports/bsc/export | Exportar a PDF/Excel |
