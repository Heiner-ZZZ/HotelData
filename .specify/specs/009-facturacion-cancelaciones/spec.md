# Especificación: Facturación y Cancelaciones

**Versión**: 1.0 | **Estado**: Implementado

**Casos de uso TAF06**: CU-O07 (Cancelar reserva según política), CU-O24 (Facturación), CU-O25 (Pago simulado)

## 1. Objetivo

Gestionar la facturación post-estancia y las cancelaciones de reservas con trazabilidad completa. El módulo permite crear facturas, registrar pagos simulados, gestionar reembolsos, y cancelar reservas con validación de políticas. Unifica la cancelación de reservas (cliente/staff) con el ciclo financiero (facturación y pagos).

## 2. Contexto

Las reservas que llegan a check-out generan facturas. Los pagos son simulados (sin pasarela real). Las cancelaciones pueden ocurrir en cualquier momento del ciclo de vida y deben liberar inventario si la reserva estaba confirmada. Toda operación financiera y de cancelación queda registrada con trazabilidad completa.

## 3. Actores

| Actor | Descripción |
|-------|-------------|
| Cliente / Viajero | Cancela su propia reserva (sujeto a políticas) |
| Staff / Partner hotelero | Gestiona facturación, pagos y cancelaciones |
| Super admin | Acceso global a facturación y cancelaciones |

## 4. Requisitos funcionales

### Cancelaciones

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Validar que la reserva existe y pertenece al usuario (cliente) o propiedad (staff) | Alta |
| RF-002 | Validar política de cancelación del hotel si está configurada | Alta |
| RF-003 | Cambiar estado a "cancelled" en booking_orders | Alta |
| RF-004 | Registrar en booking_status_history: estado anterior → cancelled | Alta |
| RF-005 | Liberar inventario en room_inventory_calendar si la reserva estaba confirmada | Alta |
| RF-006 | POST /api/reservations/{booking_id}/cancel | Alta |

### Facturación

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-101 | Crear factura para una reserva post-estancia | Alta |
| RF-102 | Listar facturas (por reserva, estado) | Alta |
| RF-103 | Ver detalle de factura (subtotal, taxes, total) | Alta |
| RF-104 | Cancelar factura (solo si estado "issued") | Alta |
| RF-105 | POST /api/billing/invoices | Alta |
| RF-106 | GET /api/billing/invoices | Alta |

### Pagos (Simulados)

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-201 | Registrar pago simulado asociado a factura | Alta |
| RF-202 | Listar pagos por reserva | Alta |
| RF-203 | Ver detalle de pago | Alta |
| RF-204 | Reembolsar pago (cascada a factura → refunded) | Alta |
| RF-205 | POST /api/billing/payments | Alta |
| RF-206 | POST /api/billing/payments/{id}/refund | Alta |

## 5. Endpoints API

### Cancelaciones

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/reservations/{booking_id}/cancel` | Cancelar reserva (libera inventario) |

### Facturación

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/billing/invoices` | Crear factura |
| GET | `/api/billing/invoices` | Listar facturas (?booking_id, ?status) |
| GET | `/api/billing/invoices/{id}` | Ver detalle de factura |
| POST | `/api/billing/invoices/{id}/cancel` | Cancelar factura (solo "issued") |

### Pagos

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/billing/payments` | Registrar pago simulado |
| GET | `/api/billing/payments` | Listar pagos (?booking_id) |
| GET | `/api/billing/payments/{id}` | Ver detalle de pago |
| POST | `/api/billing/payments/{id}/refund` | Reembolsar pago |

## 6. Modelo de datos

### reservation_invoices

| Campo | Tipo | Descripción |
|-------|------|-------------|
| booking_id | string | ID de la reserva (BK-...) |
| invoice_number | string | Nº único INV-YYYYMM-XXXX |
| subtotal | float | Subtotal |
| taxes | float | Impuestos |
| total | float | Subtotal + taxes |
| status | string | issued / paid / cancelled / refunded |
| notes | string | Opcional |

### reservation_payments

| Campo | Tipo | Descripción |
|-------|------|-------------|
| booking_id | string | ID de la reserva |
| invoice_id | ObjectId/null | Factura asociada |
| amount | float | Monto |
| method | string | Método de pago (simulado) |
| status | string | confirmed / refunded |
| reference | string | PAY-XXXXXX |

## 7. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-001 | Una cancelación desde "confirmed" libera inventario (spec 009 RF-005) |
| RN-002 | Una cancelación desde "pending" no afecta inventario (nunca se consumió) |
| RN-003 | Solo facturas en estado "issued" pueden cancelarse |
| RN-004 | Un reembolso cambia el pago a "refunded" y la factura a "refunded" |
| RN-005 | Los pagos son simulados — no hay integración bancaria real |
| RN-006 | Toda cancelación se registra en booking_status_history con razón y actor |

## 8. Dependencias

- `booking_orders` — Reservas a cancelar
- `booking_status_history` — Historial de cancelaciones
- `room_inventory_calendar` — Liberación de inventario
- `reservation_invoices` — Facturas
- `reservation_payments` — Pagos simulados
- `server/src/app/modules/billing/service/` — Lógica de facturación
- `server/src/app/modules/reservations/service/cleanup.py` — Lógica de cancelación

## 9. Fuera de alcance

### Cubiertos por otros specs
- Notificaciones de facturación por email → spec 054 (Alertas operativas)
- Reportes financieros avanzados (ingresos, impuestos, etc.) → spec 028 (Reportes Revenue)
- Validación de datos de huéspedes (pasaportes, visas, etc.) → spec 031 (Contratos API)

### Pendientes de evaluar (posibles specs dedicados)
- Pasarela de pagos real (Stripe, PayPal, Mercado Pago)
- Facturación recurrente o suscripciones (memberships)
- EXCEL export de facturas y pagos
- FACTURACIÓN electrónica (CFDI, e-invoicing) (IMPORTANTE!)
- Historial de cancelaciones con motivos y actor (cliente/staff)
- Conciliación bancaria automática
- EXPORT de reportes financieros (ingresos, impuestos, etc.)
- Gestión de impuestos compleja (exenciones, tasas variables, múltiples jurisdicciones)
- Cargos por cancelación tardía automatizados (cálculo automático según política)
- Reembolso automático (cascada a pago simulado o pasarela real)
- Gestión de cancelaciones para grupos o eventos especiales (multi-room)
- Notificaciones al cliente sobre cancelación (email/SMS)
