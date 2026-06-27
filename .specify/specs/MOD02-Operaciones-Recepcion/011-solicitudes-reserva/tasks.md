# Tareas: Solicitudes de Reserva

**Spec**: 011-solicitudes-reserva | **CU**: CU-O09

## Fase 1: Backend — Consulta de solicitudes
- [x] Endpoint GET /api/reservations?estado=pending
- [x] Filtro por prop_id del gerente autenticado
- [x] Endpoint GET /api/reservations/{booking_id} con datos completos
- [x] Manejo de caso vacío (204 No Content / mensaje)

## Fase 2: Backend — Gestión de solicitudes
- [x] Endpoint POST /api/reservations/{booking_id}/confirm
- [x] Endpoint POST /api/reservations/{booking_id}/reject
- [x] Endpoint POST /api/reservations/{booking_id}/cancel
- [x] Validación de permisos (rol gerente_hotel)
- [x] Transiciones de estado: pending → confirmed / pending → cancelled
- [x] Razón obligatoria al rechazar

## Fase 3: Backend — Reglas de negocio
- [x] _check_availability() antes de confirmar
- [x] _calculate_total_price() para vista previa
- [x] Actualización de inventario al confirmar
- [x] guest_phone y room_type_id en la solicitud

## Fase 4: Frontend
- [x] Formulario de solicitud con guest_phone y preview de precio (spec 007)
- [x] Detalle de solicitud con precio y teléfono (spec 006)
- [x] Botón de confirmar/rechazar desde UI de staff (futuro)

## Fase 5: Auto-cancelación
- [x] Lógica de cancelación automática para pending > 24h
- [x] Integración con historial de cambios (booking_status_history)

## Fase 6: Pendiente
- [ ] Notificaciones al cliente sobre resultado de la solicitud
- [ ] Dashboard en tiempo real de solicitudes
- [ ] Confirmación automática configurable por hotel
- [ ] Pruebas unitarias de transiciones (confirm/reject/cancel)
