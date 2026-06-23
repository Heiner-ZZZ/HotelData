# Plan de Implementación: Operaciones Post-Booking

**Spec**: 010-operaciones-post-booking | **CU**: CU-O08, CU-O22, CU-O23
**Estado**: ✅ COMPLETADO

## Arquitectura
Módulos:
- `server/src/app/modules/partner/routes/manual_reservations.py` — Reserva manual
- `server/src/app/modules/reviews/service/` — Reseñas
- `server/src/app/modules/reservations/service/lifecycle.py` — Creación de booking con flag manual

## Tareas implementadas

### Reserva Manual
- [x] Formulario con selección de hotel, tipo habitación, fechas, huéspedes, tarifa
- [x] Crear booking_order con estado "confirmed" directamente (salta pending)
- [x] Asociar huéspedes en booking_guests
- [x] Registrar en booking_status_history con razón "manual_reservation"
- [x] `GET/POST /partner/manual-reservations/new` (web)
- [x] `POST /api/management/manual-reservations` (API)
- [x] Listar reservas manuales con filtros

### Reseñas
- [x] Crear colecciones `reviews` y `fact_reviews` con índices
- [x] `create_review()` con validación de booking + usuario + duplicado
- [x] `list_reviews()` con filtros (prop_id, user_id, moderation_status)
- [x] `get_review()` — detalle de reseña
- [x] `moderate_review()` (approved/rejected)
- [x] `respond_to_review()` (staff response)
- [x] `delete_review()`
- [x] Exponer endpoints API REST
- [x] Dual-write a `fact_reviews`
- [x] `ensure_reviews_collections()` en startup

## Archivos implementados

| Archivo | Propósito |
|---------|-----------|
| `partner/routes/manual_reservations.py` | Rutas de reserva manual |
| `reviews/service/lifecycle.py` | CRUD reseñas + moderación |
| `reviews/service/collections.py` | Colecciones e índices |
| `reviews/service/__init__.py` | Export módulo |
| `reviews/schemas.py` | Pydantic models |
| `reviews/routes.py` | Endpoints API |
| `reservations/service/lifecycle.py` | Creación de booking con flag manual |
| `spec.md` + `plan.md` | Documentación |

## Gaps identificados

| Gap | Prioridad | Descripción |
|-----|-----------|-------------|
| GAP-047 | 🔵 Bajo | Sin web UI (templates HTML) para reseñas |
| GAP-048 | 🔵 Bajo | Sin tests unitarios para el módulo de reseñas |
