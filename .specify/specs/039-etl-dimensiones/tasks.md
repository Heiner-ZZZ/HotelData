# Tareas: ETL - Transformación de Dimensiones

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Implementación

- [ ] T001 Verificar que `ta02_dimensions.py` construye las 12 dimensiones con upsert
- [ ] T002 Verificar key fields de cada dimensión
- [ ] T003 Verificar que upsert no duplica registros

## Fase 2: Validación

- [ ] T004 Verificar carga incremental (insert si no existe, update si existe)
- [ ] T005 Verificar que dimensiones se cargan antes que fact tables
