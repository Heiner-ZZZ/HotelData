# Especificación: Solicitudes de Reserva

**Versión**: 1.0 | **Estado**: Implementado

**Casos de uso TAF06**: CU-O09 (Consultar solicitudes de reserva)

## 1. Objetivo

Permitir que el gerente de hotel consulte todas las solicitudes de reserva en estado "pending" para su propiedad, y pueda confirmarlas o rechazarlas. Este spec detalla el flujo de gestión de solicitudes entrantes que el cliente inició desde el canal digital (spec 007).

## 2. Contexto

Cuando un cliente solicita una reserva (spec 007), la reserva queda en estado "pending". El gerente del hotel debe revisar estas solicitudes y decidir si confirma la disponibilidad o la rechaza. Este flujo es el puente entre la solicitud del cliente (spec 007) y la confirmación que permite el check-in (spec 012). Sin esta gestión, las reservas quedarían en un limbo sin confirmar.

## 3. Actores

| Actor | Descripción |
|-------|-------------|
| Gerente de hotel | Consulta y gestiona solicitudes pendientes de su propiedad |
| Sistema | Ejecuta reglas de negocio (auto-cancelación 24h) y notifica resultados |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Listar solicitudes pendientes filtradas por `prop_id` del gerente autenticado | Alta |
| RF-002 | Mostrar datos clave: booking_id, nombre del huésped, fechas, tipo habitación, total, tiempo desde la solicitud | Alta |
| RF-003 | Ver detalle completo de una solicitud (GET /api/reservations/{booking_id}) | Alta |
| RF-004 | Confirmar solicitud: cambia estado "pending" → "confirmed", descuenta inventario | Alta |
| RF-005 | Rechazar solicitud: cambia estado "pending" → "cancelled" con razón | Alta |
| RF-006 | Mostrar mensaje "No hay solicitudes pendientes" si no existen | Media |
| RF-007 | Alertar al gerente si hay conflicto de inventario al confirmar | Alta |
| RF-008 | Cancelación automática de solicitudes pending > 24h (vía job programado) | Media |
| RF-009 | Notificar al cliente cuando su solicitud es confirmada o rechazada | Baja |

## 5. Endpoints API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/reservations?estado=pending` | Listar solicitudes pendientes (staff) |
| GET | `/api/reservations?estado=pending&prop_id={id}` | Listar por propiedad específica |
| GET | `/api/reservations/{booking_id}` | Detalle de una solicitud |
| POST | `/api/reservations/{booking_id}/confirm` | Confirmar solicitud (cambia a "confirmed") |
| POST | `/api/reservations/{booking_id}/reject` | Rechazar solicitud (cancela con motivo) |
| POST | `/api/reservations/{booking_id}/cancel` | Cancelación manual (genérica) |

## 6. Modelo de datos

### booking_orders (campos relevantes para solicitudes)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| status | string | "pending" / "confirmed" / "cancelled" / "checked_in" / "checked_out" |
| prop_id | int | ID del hotel |
| created_at | datetime | Fecha de la solicitud |
| total_price | float | Precio total calculado |
| currency | string | Moneda |
| total_nights | int | Noches totales |
| room_type_id | string | Tipo de habitación solicitado |
| guest_phone | string? | Teléfono del huésped |

### booking_guests

| Campo | Tipo | Descripción |
|-------|------|-------------|
| booking_id | ObjectId | Reserva asociada |
| full_name | string | Nombre del huésped |
| email | string | Email |

### booking_status_history

| Campo | Tipo | Descripción |
|-------|------|-------------|
| booking_id | ObjectId | Reserva asociada |
| from_status | string | Estado anterior |
| to_status | string | Nuevo estado |
| changed_by | string | Quién realizó el cambio |
| reason | string | Motivo del cambio (ej: "confirmed_by_manager", "rejected_no_inventory") |
| created_at | datetime | Fecha del cambio |

## 7. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-O09-01 | Una solicitud en "pending" que no se confirma en 24 horas se cancela automáticamente |
| RN-O09-02 | Solo el gerente del hotel puede confirmar o rechazar solicitudes de su propiedad |
| RN-O09-03 | Al confirmar, se descuenta el inventario en `room_inventory_calendar` (si aplica) |
| RN-O09-04 | Si hay conflicto de inventario, el sistema alerta al gerente (no bloquea automáticamente) |
| RN-O09-05 | Al rechazar, se debe registrar una razón obligatoria |
| RN-O09-06 | El cliente recibe notificación del resultado (cuando el módulo de notificaciones esté implementado) |

## 8. Dependencias

- `booking_orders` — Colección de reservas
- `booking_guests` — Huéspedes asociados
- `booking_status_history` — Historial de cambios de estado
- `room_inventory_calendar` — Inventario para descontar al confirmar
- `server/src/app/modules/reservations/service/lifecycle.py` — Lógica de ciclo de vida
- `server/src/app/modules/reservations/service/_transitions.py` — Transiciones de estado (confirm/reject)
- `server/src/app/modules/reservations/service/cleanup.py` — Auto-cancelación por tiempo
- `server/src/app/modules/reservations/routes.py` — Endpoints de reservas
- `server/src/etl/ga03_airflow/` — ETL que actualiza dimensiones y hechos

## 9. Fuera de alcance

### Cubiertos por otros specs
- Solicitud de reserva inicial por parte del cliente → spec 007 (Solicitar Reserva)
- Check-in y Check-out presencial → spec 012 (Check-In) y spec 013 (Check-Out)
- Pagos asociados a la confirmación → spec 009 (Facturación y Cancelaciones)
- Notificaciones al cliente push/email → spec 054 (Alertas operativas)
- Reportes de solicitudes → spec 028 (Reportes Revenue)
- Cancelación automática batch → spec 009 (Facturación y Cancelaciones)

### Pendientes de evaluar
- Web UI completa de gestión de solicitudes para el staff
- Confirmación automática si el hotel tiene "auto_confirm" habilitado
- Rechazo con sugerencia de fechas alternativas
- Cola de prioridad para solicitudes urgentes
- Límite de solicitudes pendientes por hotel
- Dashboard en tiempo real de solicitudes entrantes
