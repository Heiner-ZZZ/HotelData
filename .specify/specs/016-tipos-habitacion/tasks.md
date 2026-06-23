# Tareas: Tipos de Habitación

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar CRUD completo en `partner/services/rooms.py`: `create_room_type()`, `update_room_type()`, `delete_room_type()`, `list_room_types()`
- [ ] T002 Validar que no se eliminen tipos con reservas activas
- [ ] T003 Validar unicidad de nombre por propiedad

## Fase 2: Frontend

- [ ] T004 [P] Crear `RoomTypesPage` con tabla CRUD
- [ ] T005 [P] Agregar formulario de creación/edición con validaciones

## Fase 3: Validación

- [ ] T006 Verificar que `max_guests >= 1` y `base_rate > 0`
