# Tareas: Inventario y Disponibilidad

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar `partner/services/inventory.py`: `get_monthly_calendar()`, `update_inventory()` con optimistic locking
- [ ] T002 Implementar `batch_update()` para rangos de fecha
- [ ] T003 Agregar endpoints REST con validación de versión (optimistic locking)

## Fase 2: Frontend

- [ ] T004 [P] Crear `InventoryCalendar` con vista mensual
- [ ] T005 [P] Implementar drag & drop para actualizar totals
- [ ] T006 Manejar error 409 (conflict) recargando datos

## Fase 3: Validación

- [ ] T007 Verificar que `version` se incrementa correctamente
- [ ] T008 Verificar que `_id` semántico `{hotel_id}_{room_type_id}_{date}` es único
