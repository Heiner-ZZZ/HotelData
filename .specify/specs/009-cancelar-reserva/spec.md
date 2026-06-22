# Especificación: Cancelar Reserva

**Versión**: 1.0 | **Estado**: Draft

**Casos de uso TAF06**: CU-O07 (Cancelar reserva según política)

## 1. Objetivo

Permitir que el cliente cancele una reserva existente según las políticas de cancelación del hotel, registrando el cambio en booking_status_history con trazabilidad.

## 2. Contexto

El cliente necesita cancelar una reserva. El sistema debe validar que la cancelación esté permitida según la política del hotel (ventana de cancelación, cargos por cancelación tardía) y registrar el cambio de estado.

## 3. Actores

- Cliente / Viajero (cancela su propia reserva)
- Gerente de hotel (cancela cualquier reserva de su propiedad)

## 4-13. Resumen

| ID | Descripción |
|----|-------------|
| RF-001 | Validar que la reserva existe y pertenece al usuario |
| RF-002 | Validar política de cancelación del hotel (fechas, cargos) |
| RF-003 | Cambiar estado a "cancelled" en booking_orders |
| RF-004 | Registrar en booking_status_history: estado anterior → cancelled |
| RF-005 | Liberar inventario si estaba confirmada |
| RF-006 | POST /api/reservations/{booking_id}/cancel |

**Escenarios**: Cliente cancela reserva con 7 días de anticipación → cancelación gratuita según política. Cliente cancela reserva 1 día antes → aplica cargo del 50%.

**Criterios**: CA-001: Reserva cambia a estado cancelled; CA-002: Historial registra la cancelación; CA-003: Inventario se libera si estaba ocupado.

**Dependencias**: booking_orders, booking_status_history, room_inventory_calendar, hotel_policies

**Fuera de alcance**: Reembolso automático (pago simulado)
