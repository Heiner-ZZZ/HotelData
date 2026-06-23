# Plan de Implementación: Frontend - Facturación

**Branch**: `047-frontend-facturacion` | **Spec**: [spec.md](spec.md)

## Componentes

| Componente | Ruta | CU asociado |
|-----------|------|-------------|
| InvoicesListPage | /billing/invoices | CU-O24 |
| InvoiceDetailPage | /billing/invoices/:id | CU-O24 |
| PaymentsListPage | /billing/payments | CU-O25 |
| PaymentDetailPage | /billing/payments/:id | CU-O25 |
| CreateInvoiceDialog | — | CU-O24 |
| RegisterPaymentDialog | — | CU-O25 |

## Módulo existente

`frontend/src/app/features/billing/` con rutas lazy-loaded.

## Entregables

Este spec documenta la UI de facturación existente: listado/detalle de facturas y pagos, creación de factura y registro de pago simulado.
