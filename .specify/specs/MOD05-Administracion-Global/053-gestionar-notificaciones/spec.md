# Especificación: Gestionar Notificaciones Transaccionales al Huésped

**Versión**: 1.0 | **Estado**: Draft | **Última actualización**: 2026-06-21

**Casos de uso TA07**: CU-O32 (Gestionar notificaciones transaccionales al huésped)

## 1. Objetivo

Enviar notificaciones automáticas al huésped durante el ciclo de vida de la reserva: confirmación, recordatorio check-in, factura post-estancia, cambios de estado, ofertas personalizadas vía email, SMS y push.

## 2. Contexto

Nuevo caso de uso que cubre la comunicación transaccional con el huésped. Antes no existía un CU dedicado a notificaciones.

## 3. Actores

| Actor | Descripción |
|-------|-------------|
| Sistema | Genera notificaciones automáticas basadas en eventos |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe enviar confirmación de reserva al crear booking_order | Alta |
| RF-002 | El sistema debe enviar recordatorio de check-in 24h antes | Alta |
| RF-003 | El sistema debe enviar factura post-checkout | Alta |
| RF-004 | El sistema debe soportar canales: email, SMS, push | Alta |
| RF-005 | El sistema debe registrar envíos en notification_logs | Alta |
| RF-006 | El sistema debe reintentar envíos fallidos (3 intentos con backoff) | Media |

## 5-13. (Structure follows same pattern as 051)