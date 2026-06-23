# Tareas: Reportes de Calidad

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar `services/quality.py`: `list_executions()`, `get_execution_detail()`, `list_rejected()`
- [ ] T002 Agregar endpoints con paginación y filtros

## Fase 2: Frontend

- [ ] T003 [P] Crear tabla de ejecuciones ETL con fecha, estado, duración
- [ ] T004 [P] Detalle de calidad por ejecución: total, aceptados, rechazados, completitud por columna
- [ ] T005 [P] Tabla de registros rechazados con razón y raw_record
- [ ] T006 [P] Exportar reporte a PDF/CSV

## Fase 3: Validación

- [ ] T007 Verificar que `rejected_records` contiene `raw_record` y `rejection_reason`
