# Plan de Implementación: ETL - Fact Tables

**Branch**: `040-etl-fact-tables` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Parquet → build_ta02_fact() → Validar calidad → Batch insert 5k → MongoDB
                                                      → Rechazos → rejected_records
```

## Fact Tables

| Tabla | Grain | Documentos |
|-------|-------|-----------|
| fact_hotel_reservations | 1 evento de búsqueda | ~600k |

## Validaciones

| Validación | Acción |
|-----------|--------|
| Campos obligatorios faltantes | Rechazar con razón |
| price_usd < 0 | Rechazar (precios negativos) |
| adults=0 o rooms=0 | Rechazar (ocupación inválida) |
| srch_id duplicado | Rechazar |
| price_usd > 3σ | Rechazar (valores atípicos) |

## Reglas

- Batch insert: 5,000 documentos por operación
- Registros rechazados → `rejected_records` con `raw_record` y `rejection_reason`
- Conteo de insertados vs rechazados en reporte de calidad
