# Tareas: Bloqueos de Disponibilidad

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar `partner/services/blackouts.py`: `create_blackout()`, `list_blackouts()`, `delete_blackout()`
- [ ] T002 Validar que rangos no se solapen para mismo room_type
- [ ] T003 Al crear bloqueo, actualizar `room_inventory_calendar.blocked` para fechas afectadas

## Fase 2: Frontend

- [ ] T004 [P] Crear sección "Bloqueos" dentro de InventoryCalendar
- [ ] T005 [P] Formulario de bloqueo por rango de fechas con selector de room_type

## Fase 3: Validación

- [ ] T006 Verificar que bloqueo se refleja en calendario de inventario
