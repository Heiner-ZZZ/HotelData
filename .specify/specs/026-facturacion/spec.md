# Especificacion: Facturacion

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O24 (Generar comprobante o factura de reserva)

## 1. Objetivo

Generar comprobantes y facturas asociados a reservas post-estancia con estados, numero de factura unico y dual-write a fact_invoices para analitica.

## 2. Contexto

Al completar el check-out, el sistema o el recepcionista puede generar una factura para la reserva. La factura incluye subtotal, impuestos y total.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Sistema | Genera factura automaticamente al check-out |
| Recepcionista | Genera factura manualmente |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe generar factura con booking_id, subtotal, taxes, total y numero unico | Alta |
| RF-002 | El sistema debe generar numero de factura unico (INV-YYYYMM-XXXX) | Alta |
| RF-003 | El sistema debe permitir listar facturas por booking_id y estado | Alta |
| RF-004 | El sistema debe permitir cancelar factura (solo en estado issued) | Alta |
| RF-005 | El sistema debe hacer dual-write a fact_reservation_invoices | Alta |
| RF-006 | El sistema debe calcular taxes automaticamente | Alta |

## 5. Reglas de negocio

- Factura requiere booking con check-out completado
- Numero unico INV-YYYYMM-XXXX (secuencial por mes)
- Subtotal, taxes y total calculados automaticamente
- Solo se puede cancelar en estado issued
- Dual-write obligatorio a fact_reservation_invoices

## 6. Entradas

```json
{
  "booking_id": "BK-2026-001",
  "tax_percentage": 19
}
```

## 7. Salidas

```json
{
  "success": true,
  "data": {
    "invoice_id": "inv_001",
    "invoice_number": "INV-202606-0001",
    "booking_id": "BK-2026-001",
    "subtotal": 450.00,
    "tax_percentage": 19,
    "taxes": 85.50,
    "total": 535.50,
    "status": "issued",
    "created_at": "2026-06-22T10:30:00Z"
  }
}
```

## 8. Escenarios

### Escenario 1: Generar factura post-checkout
```gherkin
Dado que la reserva BK-2026-001 tiene check-out completado
Cuando el recepcionista genera la factura
Entonces el sistema crea la factura con numero unico
Y escribe en fact_reservation_invoices
```

### Escenario 2: Cancelar factura
```gherkin
Dado que existe una factura en estado issued
Cuando el recepcionista la cancela
Entonces el sistema cambia status a cancelled
```

## 9. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Factura se genera con numero unico |
| CA-002 | Calculo de taxes y total es correcto |
| CA-003 | Solo se puede cancelar factura issued |
| CA-004 | Dual-write a fact_reservation_invoices funciona |

## 10. Dependencias

- Coleccion reservation_invoices
- Coleccion fact_reservation_invoices (dual-write)
- Modulo modules/billing/services/billing.py

## 11. Fuera de alcance

- Facturacion electronica (DFE, SAT, etc.)
- Multiples monedas
- Notas de credito
