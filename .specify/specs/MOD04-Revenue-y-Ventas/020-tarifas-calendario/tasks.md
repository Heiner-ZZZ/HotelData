# Tareas: Tarifas Calendario

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar `partner/services/rates.py`: `get_rate_calendar()`, `update_rate_calendar()`, `batch_update_rates()`
- [ ] T002 Agregar endpoints con `_id` semántico `{hotel_id}_{rate_plan_id}_{YYYY-MM-DD}`

## Fase 2: Frontend

- [ ] T003 [P] Crear calendario de precios mensual por plan tarifario
- [ ] T004 [P] Permitir edición inline de precio por fecha
- [ ] T005 [P] Actualización batch por rango de fechas

## Fase 3: Validación

- [ ] T006 Verificar que precio por fecha puede diferir de `base_price`
