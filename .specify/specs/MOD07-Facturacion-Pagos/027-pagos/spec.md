# Especificacion: Pagos

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O25 (Registrar pago asociado a reserva)

## 1. Objetivo

Registrar pagos simulados asociados a reservas y facturas, con metodos de pago, estados y dual-write a fact_payments para analitica. Incluye reembolsos simulados.

## 2. Contexto

Los pagos en HotelData son simulados (sin integracion bancaria real). El sistema registra pagos contra facturas, permite reembolsos, y actualiza el estado de la factura.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Recepcionista | Registra pago en recepcion |
| Sistema | Asocia pago a factura automaticamente |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir registrar pago con booking_id, amount, method | Alta |
| RF-002 | El sistema debe generar referencia unica de pago (PAY-XXXXXX) | Alta |
| RF-003 | El sistema debe asociar pago a una factura (invoice_id) | Alta |
| RF-004 | El sistema debe actualizar estado de la factura a paid al registrar pago | Alta |
| RF-005 | El sistema debe permitir reembolsar pago | Alta |
| RF-006 | El sistema debe hacer dual-write a fact_reservation_payments | Alta |

## 5. Reglas de negocio

- Pagos simulados (sin integracion bancaria real)
- Metodos: cash, credit_card, bank_transfer (simulados)
- Al registrar pago, factura pasa a paid
- Un reembolso cambia payment.status a refunded, invoice.status a refunded
- No se cumple PCI DSS (proyecto educacional)

## 6. Entradas

```json
{
  "booking_id": "BK-2026-001",
  "invoice_id": "inv_001",
  "amount": 535.50,
  "method": "credit_card"
}
```

## 7. Salidas

```json
{
  "success": true,
  "data": {
    "payment_id": "pay_001",
    "payment_reference": "PAY-A3F2K1",
    "booking_id": "BK-2026-001",
    "invoice_id": "inv_001",
    "amount": 535.50,
    "method": "credit_card",
    "status": "completed",
    "invoice_status": "paid",
    "created_at": "2026-06-22T10:30:00Z"
  }
}
```

## 8. Escenarios

### Escenario 1: Registrar pago exitoso
```gherkin
Dado que existe una factura issued para BK-2026-001
Cuando el recepcionista registra un pago
Entonces el sistema crea el pago con referencia unica
Y actualiza la factura a paid
Y escribe en fact_reservation_payments
```

### Escenario 2: Reembolsar pago
```gherkin
Dado que existe un pago completado para la factura inv_001
Cuando el recepcionista reembolsa el pago
Entonces el sistema cambia el pago a refunded
Y actualiza la factura a refunded
```

## 9. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Pago se registra con referencia unica |
| CA-002 | Factura se actualiza a paid |
| CA-003 | Reembolso cambia ambos estados |
| CA-004 | Dual-write a fact_reservation_payments funciona |

## 10. Dependencias

- Coleccion reservation_payments
- Coleccion fact_reservation_payments (dual-write)
- Coleccion reservation_invoices (actualizacion de estado)
- Modulo modules/billing/services/payments.py

## 11. Fuera de alcance

- Integracion con pasarelas de pago reales (Stripe, MercadoPago, etc.)
- PCI DSS compliance
- Pagos recurrentes
