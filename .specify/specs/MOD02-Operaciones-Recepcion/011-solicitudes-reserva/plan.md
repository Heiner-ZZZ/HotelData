# Plan de Implementación: Solicitudes de Reserva

**Spec**: 011-solicitudes-reserva | **CU**: CU-O09
**Estado**: ✅ COMPLETADO

## Arquitectura

Módulo único dentro del módulo `reservations`:
- `server/src/app/modules/reservations/service/lifecycle.py` — Transiciones de estado (confirm, reject)
- `server/src/app/modules/reservations/service/_transitions.py` — Funciones `confirm_booking()`, `reject_booking()`
- `server/src/app/modules/reservations/service/_helpers.py` — Validación de estados permitidos
- `server/src/app/modules/reservations/service/queries.py` — Consultas de booking_orders con filtros
- `server/src/app/modules/reservations/service/cleanup.py` — Auto-cancelación de pending > 24h
- `server/src/app/modules/reservations/routes.py` — Endpoints `/confirm`, `/reject`
- `server/src/app/modules/reservations/service/__init__.py` — Exportación de funciones

## Tareas implementadas

### Consulta de solicitudes
- [x] GET `/api/reservations?estado=pending` — Listar solicitudes pendientes
- [x] GET `/api/reservations/{booking_id}` — Detalle completo de solicitud
- [x] Filtrado por `prop_id` del gerente autenticado
- [x] Mensaje "No hay solicitudes pendientes" cuando no existen

### Gestión de solicitudes
- [x] POST `/api/reservations/{booking_id}/confirm` — Confirmar (pending → confirmed)
- [x] POST `/api/reservations/{booking_id}/reject` — Rechazar (pending → cancelled con razón)
- [x] POST `/api/reservations/{booking_id}/cancel` — Cancelación manual genérica
- [x] Validación de que solo el gerente del hotel puede gestionar sus solicitudes
- [x] Razón obligatoria al rechazar

### Reglas de negocio
- [x] `ALLOWED_STATUSES` define transiciones válidas (pending → confirmed/cancelled)
- [x] `_check_availability()` — Verifica inventario al confirmar
- [x] `_calculate_total_price()` — Calcula precio para mostrar en vista previa
- [x] Roles: `require_login` en endpoints de modificación

### Auto-cancelación
- [x] `cancel_booking()` en `cleanup.py` — Cancela reservas pending expiradas
- [x] Verificación de estado "pending" antes de cancelar

## Archivos implementados

| Archivo | Propósito |
|---------|-----------|
| `reservations/service/lifecycle.py` | Ciclo de vida: create_booking, _check_availability, _calculate_total_price |
| `reservations/service/_transitions.py` | confirm_booking(), reject_booking() |
| `reservations/service/_helpers.py` | ReservationInput, ALLOWED_STATUSES |
| `reservations/service/validation.py` | Validación de entrada con guest_phone, room_type_id |
| `reservations/service/cleanup.py` | cancel_booking() para auto-cancelación |
| `reservations/service/queries.py` | Consultas a booking_orders con filtros |
| `reservations/service/_history_lookup.py` | Historial de cambios de estado |
| `reservations/service/_view_ops.py` | Operaciones de vista (detail, list) |
| `reservations/service/__init__.py` | Exportación del módulo |
| `reservations/routes.py` | Endpoints REST |
| `frontend/.../reservation-new-page/` | UI de solicitud con preview de precio |
| `frontend/.../reservation-detail-page/` | Detalle con precio y teléfono |

## Próximos pasos (mejoras futuras)

| Mejora | Prioridad | Descripción |
|--------|-----------|-------------|
| Notificación push/email al confirmar o rechazar | 🟡 Media | Depende de spec 054 (Alertas operativas) |
| Dashboard en tiempo real de solicitudes entrantes | 🟢 Baja | WebSocket o polling en UI de staff |
| Confirmación automática para hoteles con auto_confirm | 🟢 Baja | Configuración por propiedad |
| Rechazo con sugerencia de fechas alternativas | 🟢 Baja | IA o fechas disponibles más cercanas |
