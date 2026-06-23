# Tareas: Políticas Hoteleras

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar `partner/services/content/save.py`: `update_policies()`, `get_policies()`
- [ ] T002 Validar que `check_out_time > check_in_time`
- [ ] T003 Validar que `min_stay >= 1` y `max_stay >= min_stay`

## Fase 2: Frontend

- [ ] T004 [P] Crear `PoliciesPage` con formulario: check-in/out, cancelación, mascotas, niños
- [ ] T005 [P] Time pickers para check-in/out, inputs numéricos para fees

## Fase 3: Validación

- [ ] T006 Verificar registro en `hotel_content_changes` al actualizar
