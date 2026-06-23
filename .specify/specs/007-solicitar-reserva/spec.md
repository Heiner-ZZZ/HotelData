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

**Fuera de alcance**: 

- Pago en línea al reservar (solo facturación post-estancia)
- webhook para notificar al gerente del hotel sobre nueva reserva
- Modificación o cancelación de reservas por parte del cliente
- chat bot para asistencia en reservas
- Solicitud de reserva para múltiples tipos de habitación en una sola acción
- IA para sugerir upgrades o promociones al solicitar reserva
- Solicitud de reserva para múltiples fechas en una sola acción
- Automatización de confirmación de reservas (requiere acción del gerente)
- Webhooks o notificaciones automáticas al cliente y gerente al crear reserva
- Confirmación automática de reservas (requiere acción del gerente)
- Integración con sistemas de terceros para gestión de reservas (Channel Managers, OTAs)
- Envío de notificaciones automáticas al cliente y gerente (email, SMS) al crear reserva
- Gestión de reservas para grupos o eventos especiales
- Gestión de solicitudes especiales (cama extra, accesibilidad, etc.) durante la reserva
- Validación de datos de huéspedes contra bases de datos externas (pasaportes, visas, etc.)
- Gestión de reservas con múltiples tipos de habitación en una sola solicitud
- Gestión de reservas con diferentes políticas de cancelación en una sola solicitud
- Gestión de reservas con diferentes tarifas en una sola solicitud
- Gestión de reservas con diferentes fechas de check-in/check-out en una sola solicitud
- Gestión de reservas con diferentes opciones de pago en una sola solicitud
- Gestión de reservas con diferentes opciones de cancelación gratuita en una sola solicitud
- Gestión de reservas con diferentes opciones de reembolso en una sola solicitud
- Gestión de reservas con diferentes opciones de servicios adicionales en una sola solicitud
- Gestión de reservas con diferentes opciones de habitación para no fumadores/fumadores en una sola solicitud
- Gestión de reservas con diferentes opciones de habitación para discapacitados en una sola solicitud
- Gestión de reservas con diferentes opciones de habitación para grupos en una sola solicitud
- Gestión de reservas con diferentes opciones de habitación para familias en una sola solicitud
- Gestión de reservas con diferentes opciones de habitación para mascotas en una sola solicitud
- Gestión de reservas con diferentes opciones de habitación para parejas en una sola solicitud
- Gestión de reservas con diferentes opciones de habitación para solteros en una sola solicitud
- Gestión de reservas con diferentes opciones de habitación para viajeros de negocios en una sola solicitud
- Gestión de reservas con diferentes opciones de habitación para viajeros de ocio en una sola solicitud     
