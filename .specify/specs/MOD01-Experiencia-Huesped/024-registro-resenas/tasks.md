# Tareas: Registro de Reseñas

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar `modules/reviews/services/reviews.py`: `create_review()` con validación de estancia completada
- [ ] T002 Implementar dual-write a `fact_reviews`
- [ ] T003 Validar una reseña por reserva (unique booking_id)
- [ ] T004 Agregar endpoints: POST /api/reviews, GET /api/hotels/{id}/reviews (top 5 aprobadas)

## Fase 2: Frontend

- [ ] T005 [P] Crear `ReviewForm` con rating (1-5 estrellas), título, comentario
- [ ] T006 [P] Mostrar reseñas aprobadas en `HotelDetailPage`

## Fase 3: Validación

- [ ] T007 Verificar que solo huéspedes post-estancia pueden reseñar
- [ ] T008 Verificar dual-write a fact_reviews
