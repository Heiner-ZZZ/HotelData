# Tareas: Facturación

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar `modules/billing/services/billing.py`: `create_invoice()`, `cancel_invoice()`, `get_invoice()`, `list_invoices()`
- [ ] T002 Generar número único INV-YYYYMM-XXXX (secuencial por mes)
- [ ] T003 Calcular subtotal, taxes y total automáticamente
- [ ] T004 Implementar dual-write a `fact_reservation_invoices`

## Fase 2: Frontend

- [ ] T005 [P] Crear `InvoiceDetailPage` con detalle de factura
- [ ] T006 [P] Botón de cancelar factura (solo estado "issued")

## Fase 3: Validación

- [ ] T007 Verificar que factura requiere booking con check-out completado
- [ ] T008 Verificar número único de factura
