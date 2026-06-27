# Tareas: Editar Nombre Comercial

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Crear función `update_hotel_profile()` en `partner/services/profile.py` que reciba whitelist de campos editables
- [ ] T002 Implementar registro de cambios en `hotel_profile_changes` con old/new value por campo
- [ ] T003 Agregar endpoint `PUT /api/partner/properties/{id}/profile` con validación de propiedad asignada
- [ ] T004 [P] Agregar endpoint `GET /api/partner/properties/{id}/profile` para obtener perfil actual

## Fase 2: Frontend

- [ ] T005 [P] Crear formulario de edición de nombre comercial en `PropertyEditPage`
- [ ] T006 Mostrar indicador de `verified_at` (última verificación)

## Fase 3: Validación

- [ ] T007 Verificar que `prop_id` no se modifica
- [ ] T008 Verificar que cambios quedan registrados en `hotel_profile_changes`
