# Plan de Implementación: ETL - Ingesta de Datos

**Branch**: `038-etl-ingesta` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
PocketBase API → Extract (chunks 50k) → Validate Schema → JSONL → Parquet
```

## Componentes (existentes)

| Archivo | Propósito |
|---------|-----------|
| `server/src/etl/tasks.py` | Extracción desde PocketBase y CSV |
| `server/src/etl/transform_clean.py` | Validación y limpieza inicial |
| `server/config/settings.py` | Chunk size, batch size, conexiones |

## Flujo

1. Extraer desde PocketBase vía API REST (paginado, 50k filas por chunk)
2. Validar columnas requeridas del esquema
3. Convertir a JSONL (staging)
4. Convertir a Parquet (processed) con PyArrow

## Reglas

- Chunk size: 50,000 filas
- Nunca cargar dataset completo en memoria
- Schema mínimo: `srch_id`, `date_time`, `prop_id`, `price_usd`, etc.
