# Especificación: Check-out

**Versión**: 1.0 | **Estado**: Draft

**Casos de uso TAF06**: CU-O11 (Completar check-out)

## 1. Objetivo

Permitir que el gerente de hotel registre la salida del huésped, cambiando el estado de "checked_in" a "checked_out" y liberando la habitación para nuevo inventario.

## 2. Contexto

Al finalizar la estancia, el gerente realiza el check-out. Esto libera la habitación, actualiza el inventario y cierra el ciclo operativo de la reserva.

## 3. Actores

- Gerente de hotel

## 4-13. Resumen

| ID | Descripción |
|----|-------------|
| RF-001 | Listar reservas checked_in para hoy (GET /api/management/check-outs) |
| RF-002 | Completar check-out (POST /api/management/check-outs/{id}/complete) |
| RF-003 | Cambiar estado a "checked_out" |
| RF-004 | Liberar inventario en room_inventory_calendar |

**Escenarios**: Gerente da check-out a huésped → estado checked_out, habitación liberada para limpieza y nueva reserva.

**Criterios**: CA-001: Reserva cambia a checked_out; CA-002: Inventario se libera correctamente.

**Dependencias**: booking_orders, booking_status_history, room_inventory_calendar

**Fuera de alcance**: Generación automática de factura al check-out
