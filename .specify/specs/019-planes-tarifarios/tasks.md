# Tareas: Planes Tarifarios

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar CRUD en `partner/services/rates.py`: `create_rate_plan()`, `update_rate_plan()`, `list_rate_plans()`, `delete_rate_plan()`
- [ ] T002 Validar que no se eliminen planes con reservas activas
- [ ] T003 Asociar plan a tipo de habitación

## Fase 2: Frontend

- [ ] T004 [P] Crear `RatePlansPage` con tabla de planes y reglas
- [ ] T005 [P] Formulario de creación/edición con selector de room_type

## Fase 3: Validación

- [ ] T006 Verificar que `base_price > 0` en plan tarifario
