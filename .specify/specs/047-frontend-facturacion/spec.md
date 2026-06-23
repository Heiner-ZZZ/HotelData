# Especificacion: Frontend - Facturacion

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O24, CU-O25 (Facturacion y pagos)

## 1. Objetivo

UI de facturacion: listado/detalle de facturas y pagos, creacion de factura y registro de pago.

## 2. Componentes

| Componente | Ruta | CU asociado |
|------------|------|-------------|
| InvoicesListPage | /billing/invoices | CU-O24 |
| InvoiceDetailPage | /billing/invoices/:id | CU-O24 |
| PaymentsListPage | /billing/payments | CU-O25 |
| PaymentDetailPage | /billing/payments/:id | CU-O25 |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | InvoicesListPage con tabla de facturas por booking y estado | Alta |
| RF-002 | InvoiceDetailPage con detalle de factura | Alta |
| RF-003 | PaymentsListPage con tabla de pagos | Alta |
| RF-004 | Crear factura desde detalle de reserva | Alta |
| RF-005 | Registrar pago simulado desde detalle de factura | Alta |

## 4. Dependencias

- frontend/src/app/features/billing/
- modules/billing/routes.py
