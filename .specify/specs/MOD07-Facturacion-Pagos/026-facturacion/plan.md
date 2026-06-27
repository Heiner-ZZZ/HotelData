# Plan de Implementación: Facturación

**Branch**: `026-facturacion` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Sistema (post-checkout) / Recepcionista
  → POST /api/billing/invoices
    → services/billing.py
      → reservation_invoices (issued | cancelled)
      → fact_reservation_invoices (dual-write)
      → Genera número único: INV-YYYYMM-XXXX
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| POST | /api/billing/invoices | Generar factura para reserva |
| GET | /api/billing/bookings/{id}/invoices | Listar facturas de una reserva |
| GET | /api/billing/invoices/{id} | Detalle de factura |
| POST | /api/billing/invoices/{id}/cancel | Cancelar factura (solo issued) |

## Reglas de negocio

- Factura requiere booking con check-out completado
- Número único INV-YYYYMM-XXXX (secuencial por mes)
- Subtotal, taxes (%, configurable) y total calculados automáticamente
- Solo se puede cancelar en estado "issued"
- Dual-write obligatorio a fact_reservation_invoices
