# Plan de Implementación: Facturación y Cancelaciones

**Spec**: 009-facturacion-cancelaciones | **CU**: CU-O07, CU-O24, CU-O25
**Estado**: ✅ COMPLETADO

## Arquitectura
Módulos:
- `server/src/app/modules/billing/` — Facturación y pagos
- `server/src/app/modules/reservations/service/cleanup.py` — Cancelación

## Tareas implementadas

### Cancelaciones
- [x] Validar que la reserva existe y pertenece al usuario/propiedad
- [x] Validar política de cancelación del hotel si está configurada
- [x] Cambiar estado a "cancelled" en booking_orders
- [x] Registrar en booking_status_history con trazabilidad
- [x] Liberar inventario en room_inventory_calendar si estaba confirmada
- [x] `POST /api/reservations/{booking_id}/cancel`

### Facturación
- [x] Crear factura para una reserva post-estancia
- [x] Listar facturas (por reserva, estado)
- [x] Ver detalle de factura (subtotal, taxes, total)
- [x] Cancelar factura (solo si estado "issued")
- [x] `POST /api/billing/invoices`
- [x] `GET /api/billing/invoices`
- [x] `GET /api/billing/invoices/{id}`
- [x] `POST /api/billing/invoices/{id}/cancel`

### Pagos (Simulados)
- [x] Registrar pago simulado asociado a factura
- [x] Listar pagos por reserva
- [x] Ver detalle de pago
- [x] Reembolsar pago (cascada factura → refunded)
- [x] `POST /api/billing/payments`
- [x] `GET /api/billing/payments`
- [x] `GET /api/billing/payments/{id}`
- [x] `POST /api/billing/payments/{id}/refund`

## Archivos implementados

| Archivo | Propósito |
|---------|-----------|
| `billing/service/lifecycle.py` | CRUD facturas + pagos con dual-write |
| `billing/service/collections.py` | Colecciones e índices |
| `billing/service/__init__.py` | Export módulo |
| `billing/schemas.py` | Pydantic models |
| `billing/routes.py` | Endpoints API |
| `billing/tests/test_billing.py` | Tests de integración |
| `reservations/service/cleanup.py` | Lógica de cancelación + liberación inventario |
| `spec.md` + `plan.md` | Documentación |

## Modelo de datos

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
