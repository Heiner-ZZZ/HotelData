# Especificación: Check-in

**Versión**: 1.0 | **Estado**: Draft

**Casos de uso TAF06**: CU-O10 (Completar check-in)

## 1. Objetivo

Permitir que el gerente de hotel registre la llegada del huésped, cambiando el estado de la reserva de "confirmed" a "checked_in" y actualizando el inventario de habitaciones.

## 2. Contexto

Cuando el huésped llega al hotel, el gerente realiza el check-in en el sistema. Esto marca la habitación como ocupada, inicia la estancia y registra el evento con trazabilidad.

## 3. Actores

- Gerente de hotel

## 4-13. Resumen

| ID | Descripción |
|----|-------------|
| RF-001 | Listar reservas confirmed para hoy (GET /api/management/check-ins) |
| RF-002 | Completar check-in de una reserva (POST /api/management/check-ins/{id}/complete) |
| RF-003 | Cambiar estado booking_order a "checked_in" |
| RF-004 | Registrar en booking_status_history |
| RF-005 | Actualizar inventario (room_inventory_calendar) |

**Escenarios**: Gerente ve lista de check-ins del día, selecciona huésped, confirma llegada → estado pasa a checked_in.

**Criterios**: CA-001: Reserva cambia a checked_in; CA-002: Inventario se actualiza; CA-003: Historial registra el cambio.

**Dependencias**: booking_orders, booking_status_history, room_inventory_calendar

**Fuera de alcance**: 
- Asignación automática de habitación específica
- Gestión de check-out
- Notificaciones al huésped
- check-in calendario de disponibilidad
- calendario de ocupación
- logística de limpieza y mantenimiento
- pagos y facturación
- excel para reportes de check-in
- diseño de interfaz de usuario para check-in
- Integración con sistemas de control de acceso (tarjetas, cerraduras inteligentes)
- Gestión de check-in para grupos o eventos especiales
- Validaciones de documentos de identidad o métodos de pago durante el check-in
- Funcionalidades de self check-in o kioscos de check-in
