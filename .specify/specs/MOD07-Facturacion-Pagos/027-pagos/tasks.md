# Tareas: Pagos

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar `modules/billing/services/payments.py`: `register_payment()`, `refund_payment()`, `list_payments()`
- [ ] T002 Generar referencia única PAY-XXXXXX
- [ ] T003 Al registrar pago, actualizar invoice.status → "paid"
- [ ] T004 Implementar dual-write a `fact_reservation_payments`

## Fase 2: Frontend

- [ ] T005 [P] Crear `PaymentsListPage` con tabla de pagos
- [ ] T006 [P] Botón de registrar pago simulado (método: cash, credit_card, bank_transfer)
- [ ] T007 [P] Botón de reembolso con confirmación

## Fase 3: Validación

- [ ] T008 Verificar que reembolso cambia invoice.status → "refunded"
- [ ] T009 Verificar dual-write a fact_reservation_payments
