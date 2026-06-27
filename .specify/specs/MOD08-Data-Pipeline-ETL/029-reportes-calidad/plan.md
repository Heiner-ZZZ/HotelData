# Plan de Implementación: Reportes de Calidad

**Branch**: `029-reportes-calidad` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Auditor
  → ReportesCalidadPage
    → GET /api/reports/quality/executions
    → GET /api/reports/quality/executions/{id}
    → GET /api/reports/quality/rejected
      → services/quality.py
        → etl_executions collection
        → data_quality_reports collection
        → rejected_records collection
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/reports/quality/executions | Listar ejecuciones ETL |
| GET | /api/reports/quality/executions/{id} | Detalle de calidad por ejecución |
| GET | /api/reports/quality/rejected | Listar registros rechazados |
| GET | /api/reports/quality/export/{id} | Exportar reporte a PDF/CSV |

## Colecciones

- `etl_executions`: historial de ejecuciones
- `data_quality_reports`: reporte de calidad por ejecución
- `rejected_records`: registros rechazados con razón exacta
