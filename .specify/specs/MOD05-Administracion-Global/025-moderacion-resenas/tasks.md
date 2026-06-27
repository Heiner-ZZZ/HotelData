# Tareas: Moderación de Reseñas

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar `modules/reviews/services/reviews.py`: `approve_review()`, `reject_review()`, `respond_to_review()`
- [ ] T002 Validar permisos: solo marketing_hotelero y super_admin moderan
- [ ] T003 Validar que no se puede responder reseña rechazada

## Fase 2: Frontend

- [ ] T004 [P] Crear `ModeratePage` con tabla de reseñas pendientes
- [ ] T005 [P] Botones de aprobar/rechazar con confirmación
- [ ] T006 [P] Formulario de respuesta del hotel en reseña aprobada

## Fase 3: Validación

- [ ] T007 Verificar que reseñas aprobadas son visibles en detalle del hotel
