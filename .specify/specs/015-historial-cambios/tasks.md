# Tareas: Historial de Cambios

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Crear `partner/services/history.py` con `list_hotel_changes(filters)` y `get_change_detail()`
- [ ] T002 Agregar endpoint `GET /api/partner/properties/{id}/history` con paginación y filtros (fecha, campo, usuario)
- [ ] T003 Agregar endpoint `GET /api/partner/properties/{id}/history/{change_id}` para detalle

## Fase 2: Frontend

- [ ] T004 [P] Crear `HistoryPage` con tabla de auditoría filtrable
- [ ] T005 [P] Agregar modal de detalle de cambio con old/new value

## Fase 3: Validación

- [ ] T006 Verificar índices en `hotel_profile_changes` y `hotel_content_changes`
