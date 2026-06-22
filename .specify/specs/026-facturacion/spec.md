# Especificación: Facturación y Cargos Adicionales

**Versión**: 1.1 | **Estado**: Actualizado | **Última actualización**: 2026-06-21

**Casos de uso TA07**: CU-O24 (Generar comprobante/factura + registrar cargos adicionales), CU-O25 (Registrar pago)

## 1. Objetivo
Generar comprobantes/facturas asociadas a reservas con dual-write a fact_invoices y registrar cargos adicionales (absorbidos de CU-O34).

## 2. Contexto
Este spec fue expandido para incluir el registro de cargos adicionales (room service, daños, late check-out, extras) que anteriormente estaba en CU-O34.

## 3. Actores
| Actor | Descripción |
|-------|-------------|
| Recepcionista | Genera facturas y registra cargos adicionales |
| Sistema | Dual-write a colecciones analíticas |

## 4. Requisitos funcionales
| ID | Requisito |
|----|-----------|
| RF-001 | Generar comprobante/factura con datos de reserva |
| RF-002 | Registrar pago asociado a reserva |
| RF-003 | Registrar cargos adicionales (upgrade, late check-out, extras) |
| RF-004 | Actualizar booking_orders.total con cargos |
| RF-005 | Dual-write a fact_invoices y fact_payments |
