# Plan de Implementación: Pagos

**Branch**: `027-pagos` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Recepcionista
  → POST /api/billing/payments
    → services/payments.py
      → reservation_payments (pending | completed | refunded)
      → Actualiza factura.status: "paid"
      → fact_reservation_payments (dual-write)
      → Referencia PAY-XXXXXX
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| POST | /api/billing/payments | Registrar pago simulado |
| GET | /api/billing/invoices/{id}/payments | Listar pagos de una factura |
| GET | /api/billing/payments/{id} | Detalle de pago |
| POST | /api/billing/payments/{id}/refund | Reembolsar pago |

## Reglas de negocio

- Pagos simulados (sin integración bancaria real)
- Métodos: cash, credit_card, bank_transfer (simulados)
- Al registrar pago, factura pasa a "paid"
- Un reembolso cambia payment.status → "refunded", invoice.status → "refunded"
- No se cumple PCI DSS (proyecto educacional)
