# Especificación: Consultar Mis Reservas

**Versión**: 1.0 | **Estado**: Draft

**Casos de uso TAF06**: CU-O06 (Consultar mis reservas), CU-O09 (Consultar solicitudes de reserva)

## 1. Objetivo

Permitir que el cliente consulte todas sus reservas con estado, fechas, hotel, monto y acciones disponibles (cancelar, ver detalle). El gerente de hotel puede consultar solicitudes de reserva de todos los clientes para su propiedad.

## 2. Contexto

El cliente necesita ver el historial de sus reservas activas y pasadas. El gerente necesita ver las solicitudes entrantes para gestionarlas. Ambos roles tienen vistas diferentes pero comparten la misma fuente de datos.

## 3. Actores

- Cliente: ve solo sus reservas
- Gerente de hotel: ve todas las reservas de su propiedad

## 4-13. Resumen

| ID | Descripción |
|----|-------------|
| RF-001 | Listar reservas del cliente autenticado |
| RF-002 | Mostrar estado (pending, confirmed, cancelled, completed) |
| RF-003 | Mostrar hotel, fechas, tipo habitación, monto |
| RF-004 | GET /api/reservations con filtro por usuario (cliente) o por hotel (gerente) |
| RF-005 | GET /api/management/check-ins y /check-outs para operación diaria |

**Escenarios**: Cliente ve 3 reservas: 1 confirmada (próxima), 1 completada (anterior), 1 cancelada.

**Criterios**: CA-001: Lista muestra solo reservas del usuario autenticado; CA-002: Estados visualmente distintos.

**Dependencias**: booking_orders, booking_guests, booking_status_history

**Fuera de alcance**: Exportar a PDF
