# Especificación: Solicitar Reserva

**Versión**: 1.0 | **Estado**: Draft

**Casos de uso TAF06**: CU-O05 (Solicitar reserva)

## 1. Objetivo

Permitir que el cliente solicite una reserva seleccionando tipo de habitación, fechas, huéspedes y datos de contacto, creando un booking_order en estado "pending" con trazabilidad completa.

## 2. Contexto

El cliente encontró el hotel deseado y procede a reservar. Debe seleccionar tipo de habitación, ingresar datos de huéspedes y confirmar la solicitud. La reserva queda en estado pendiente hasta que el gerente del hotel la confirme.

## 3. Actores

- Cliente / Viajero

## 4-13. Resumen

| ID | Descripción |
|----|-------------|
| RF-001 | Seleccionar tipo de habitación y cantidad |
| RF-002 | Ingresar datos de huéspedes (nombre, email, teléfono) |
| RF-003 | Mostrar resumen con fechas, tarifa total, políticas de cancelación |
| RF-004 | Confirmar reserva → crear booking_order con estado "pending" |
| RF-005 | Crear booking_guests con datos de huéspedes |
| RF-006 | Registrar en booking_status_history: "created" |
| RF-007 | POST /api/reservations crea la reserva |

**Escenarios**: Cliente reserva habitación deluxe por 3 noches, ingresa 2 huéspedes, confirma → booking creado en pending.

**Criterios**: CA-001: Reserva se crea en booking_orders; CA-002: Huéspedes en booking_guests; CA-003: Historial en booking_status_history.

**Restricciones**: No se puede reservar en fechas sin disponibilidad.

**Dependencias**: booking_orders, booking_guests, booking_status_history, room_inventory_calendar

**Fuera de alcance**: Pago en línea al reservar (solo facturación post-estancia)
