# Tareas: ETL - Ingesta de Datos

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Extracción

- [ ] T001 Verificar que `tasks.py` extrae datos desde PocketBase vía API REST con paginación
- [ ] T002 Verificar que extrae datos desde CSV local
- [ ] T003 Verificar chunk size de 50k filas

## Fase 2: Validación y conversión

- [ ] T004 Verificar que `transform_clean.py` valida columnas requeridas del esquema
- [ ] T005 Verificar conversión a JSONL (staging)
- [ ] T006 Verificar conversión a Parquet (processed) con PyArrow

## Fase 3: Validación

- [ ] T007 Verificar que no se carga dataset completo en memoria
- [ ] T008 Verificar schema mínimo: srch_id, date_time, prop_id, price_usd
