# Especificación: Reserva Manual

**Versión**: 1.0 | **Estado**: Draft

**Casos de uso TAF06**: CU-O08 (Registrar reserva manual)

## 1. Objetivo

Permitir que el gerente de hotel cree una reserva manualmente desde el panel de gestión, para casos de reservas telefónicas, walk-in o cortesía.

## 2. Contexto

No todas las reservas llegan por el canal digital. El gerente necesita poder registrar reservas directamente en el sistema, asignando habitación, fechas, huésped y tarifa. La reserva manual sigue el mismo flujo de estados que una reserva digital.

## 3. Actores

- Gerente de hotel

## 4-13. Resumen

| ID | Descripción |
|----|-------------|
| RF-001 | Formulario con selección de hotel, tipo habitación, fechas, huéspedes, tarifa |
| RF-002 | Crear booking_order con estado "confirmed" directamente |
| RF-003 | Asociar huéspedes en booking_guests |
| RF-004 | GET/POST /partner/manual-reservations/new |

**Escenarios**: Gerente registra walk-in de 2 noches, habitación estándar, pago en efectivo → reserva creada como confirmed.

**Criterios**: CA-001: Reserva manual visible en booking_orders; CA-002: Estado inicial es confirmed (no pending).

**Dependencias**: booking_orders, booking_guests, booking_status_history, manual_reservations

**Fuera de alcance**: Pago integrado al crear reserva manual
