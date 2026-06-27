# Checklist: Solicitudes de Reserva

**Spec**: 011-solicitudes-reserva | **CU**: CU-O09

## Backend

- [x] Endpoint `GET /api/reservations?estado=pending` implementado
- [x] Filtro por `prop_id` del gerente
- [x] Endpoint `GET /api/reservations/{booking_id}` implementado
- [x] Endpoint `POST /api/reservations/{booking_id}/confirm` implementado
- [x] Endpoint `POST /api/reservations/{booking_id}/reject` implementado
- [x] Endpoint `POST /api/reservations/{booking_id}/cancel` implementado
- [x] Validación de autenticación (`Depends(require_login)`)
- [x] Validación de rol gerente_hotel
- [x] `ALLOWED_STATUSES` define transiciones válidas
- [x] Razón obligatoria al rechazar
- [x] Auto-cancelación de pending > 24h
- [x] Historial de cambios registrado en `booking_status_history`
- [x] `_check_availability()` implementada
- [x] `_calculate_total_price()` implementada

## Frontend

- [x] Formulario de solicitud con campo guest_phone
- [x] Preview de precio en paso de revisión
- [x] Detalle de solicitud con precio, moneda, noches
- [x] Detalle de solicitud con teléfono del huésped

## Reglas de negocio

- [x] RN-O09-01: Auto-cancelación 24h implementada
- [x] RN-O09-02: Solo gerente del hotel puede gestionar solicitudes
- [x] RN-O09-03: Descuento de inventario al confirmar
- [x] RN-O09-04: Alerta de conflicto de inventario
- [x] RN-O09-05: Razón obligatoria al rechazar
- [x] RN-O09-06: Notificación al cliente (pendiente — spec 054)
