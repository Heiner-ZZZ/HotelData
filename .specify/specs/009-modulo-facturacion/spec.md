# Especificación: Módulo de Facturación

**Versión**: 1.0 | **Estado**: Implementado

**Casos de uso**: CU-O24 (Facturación), CU-O25 (Pago simulado)

## 1. Objetivo

Gestionar la facturación y pagos simulados de las reservas. El módulo permite crear facturas post-estancia, registrar pagos simulados (sin pasarela real), y gestionar reembolsos.

## 2. Actores

- Staff / Partner hotelero
- Super admin

## 3. Funcionalidades

| ID | Descripción | Estado |
|----|-------------|--------|
| RF-001 | Crear factura para una reserva | ✅ |
| RF-002 | Listar facturas (por reserva, estado) | ✅ |
| RF-003 | Ver detalle de factura | ✅ |
| RF-004 | Cancelar factura (solo si "issued") | ✅ |
| RF-005 | Registrar pago simulado | ✅ |
| RF-006 | Listar pagos (por reserva) | ✅ |
| RF-007 | Ver detalle de pago | ✅ |
| RF-008 | Reembolsar pago (cascada a factura) | ✅ |

## 4. Endpoints API

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/billing/invoices` | Crear factura |
| GET | `/api/billing/invoices` | Listar facturas (?booking_id, ?status) |
| GET | `/api/billing/invoices/{id}` | Ver factura |
| POST | `/api/billing/invoices/{id}/cancel` | Cancelar factura |
| POST | `/api/billing/payments` | Registrar pago |
| GET | `/api/billing/payments` | Listar pagos (?booking_id) |
| GET | `/api/billing/payments/{id}` | Ver pago |
| POST | `/api/billing/payments/{id}/refund` | Reembolsar pago |

## 5. Modelo de datos

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
