# Especificación: Gestión de Reservas

**Versión**: 1.0 | **Estado**: Implementado

**Casos de uso TAF06**: CU-O06 (Consultar mis reservas), CU-O09 (Consultar solicitudes de reserva), CU-O10 (Check-in), CU-O11 (Check-out)

## 1. Objetivo

Gestionar el ciclo de vida completo de las reservas: clientes consultan sus reservas, staff gestiona solicitudes, confirmaciones, cancelaciones, check-in y check-out. Unifica la vista de cliente (solo sus reservas) y la vista de gestión (staff puede ver y operar sobre todas las reservas de su propiedad).

## 2. Contexto

Una vez que el cliente solicita una reserva (spec 007), necesita consultar su estado y acciones disponibles. El staff del hotel debe poder gestionar las solicitudes entrantes: confirmar disponibilidad, rechazar si no es posible, y realizar check-in/check-out durante la estancia. Ambos roles comparten la misma fuente de datos (`booking_orders`) pero con diferentes vistas y permisos.

## 3. Actores

| Actor | Descripción |
|-------|-------------|
| Cliente / Viajero | Consulta sus propias reservas, ve detalle y estado |
| Staff / Partner hotelero | Gestiona todas las reservas de su propiedad |
| Gerente de hotel | Supervisa check-ins, check-outs y operación diaria |
| Super admin | Acceso global a todas las reservas del sistema |

## 4. Requisitos funcionales

### Cliente

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Listar reservas del cliente autenticado | Alta |
| RF-002 | Mostrar estado (pending, confirmed, cancelled, completed, rejected) | Alta |
| RF-003 | Mostrar hotel, fechas, tipo habitación, monto | Alta |
| RF-004 | GET /api/reservations con filtro por usuario autenticado | Alta |
| RF-005 | Ver detalle de reserva con historial de estados | Alta |

### Staff / Gestión

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-101 | Listar reservas con filtros (estado, hotel, huésped, fechas) | Alta |
| RF-102 | Ver detalle de reserva con historial de estados | Alta |
| RF-103 | Confirmar reserva (pending → confirmed) | Alta |
| RF-104 | Rechazar reserva (pending → rejected) | Alta |
| RF-105 | Cancelar reserva (pending/confirmed → cancelled) con liberación de inventario | Alta |
| RF-106 | Realizar check-in (confirmed → checked_in) | Alta |
| RF-107 | Realizar check-out (checked_in → checked_out) | Alta |
| RF-108 | Ver dashboard de check-ins/outs por fecha | Alta |
| RF-109 | Ver estadísticas de reservas por estado | Media |
| RF-110 | GET /api/management/check-ins y /check-outs para operación diaria | Alta |

## 5. Flujo de estados (lifecycle)

```text
                    ┌──────────┐
                    │ Pending  │
                    └────┬─────┘
                    │     │     │
             ┌──────┘     │     └──────┐
             ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │Confirmed │ │Rejected  │ │Cancelled │
        └────┬─────┘ └──────────┘ └──────────┘
             │
             ▼
        ┌──────────┐
        │Checked in│
        └────┬─────┘
             │
             ▼
        ┌──────────┐
        │Checked   │
        │out       │
        └──────────┘
```

## 6. Endpoints API

### Reservas

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/reservations` | Listar reservas (filtros: status, prop_id, guest, fechas) |
| GET | `/api/reservations/stats` | Estadísticas por estado |
| GET | `/api/reservations/{id}` | Detalle de reserva con historial |
| POST | `/api/reservations` | Crear reserva (spec 007) |
| POST | `/api/reservations/{id}/confirm` | Confirmar reserva |
| POST | `/api/reservations/{id}/reject` | Rechazar reserva |
| POST | `/api/reservations/{id}/cancel` | Cancelar reserva (libera inventario si confirmed) |

### Check-in / Check-out

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/management/check-ins?date=` | Check-ins del día |
| POST | `/api/management/check-ins/{id}/complete` | Completar check-in |
| GET | `/api/management/check-outs?date=` | Check-outs del día |
| POST | `/api/management/check-outs/{id}/complete` | Completar check-out |

## 7. Formato de salida

### GET /api/reservations/stats
```json
{
  "pending": 5,
  "confirmed": 3,
  "cancelled": 1,
  "rejected": 0,
  "checked_in": 2,
  "checked_out": 1,
  "total": 12
}
```

### GET /api/reservations?status=pending&prop_id=123
```json
{
  "items": [...],
  "page": 1,
  "page_size": 20,
  "total": 5,
  "total_pages": 1,
  "has_prev": false,
  "has_next": false
}
```

## 8. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-001 | Un cliente solo ve sus propias reservas (filtro por user_id) |
| RN-002 | El staff ve todas las reservas de su propiedad asignada |
| RN-003 | El flujo de estados es unidireccional: no se puede revertir un estado |
| RN-004 | Una reserva cancelada libera inventario si estaba en estado confirmed |
| RN-005 | No se puede hacer check-in sin reserva en estado confirmed |
| RN-006 | No se puede hacer check-out sin reserva en estado checked_in |
| RN-007 | Cada transición de estado se registra en booking_status_history |

## 9. Dependencias

- `booking_orders` — Órdenes de reserva
- `booking_guests` — Datos de huéspedes
- `booking_status_history` — Historial de cambios de estado
- `manual_reservations` — Reservas manuales (partner)
- `room_inventory_calendar` — Liberación de inventario al cancelar
- `server/src/app/modules/reservations/service/` — Lógica de ciclo de vida

## 10. Fuera de alcance

### Cubiertos por otros specs
- Pagos integrados al flujo de reserva → spec 009 (Facturación y Cancelaciones)
- Generación automática de factura al check-out 
- Notificaciones automáticas al staff por email/SMS 
- chat bot para asistencia en gestión de reservas →
- Notificaciones automáticas al cliente por email/SMS 
- Integración con Channel Managers, OTAs 
- Validación de datos de huéspedes (pasaportes, visas, etc.) 

### Pendientes de evaluar (posibles specs dedicados)
- Exportar reservas a PDF / CSV
- Gestión de reservas para grupos o eventos especiales (multi-room, multi-guest)
- Quejas y reclamos de clientes sobre reservas
- Uso de códigos promocionales o descuentos aplicados a reservas
- Gestión de solicitudes especiales (cama extra, accesibilidad, mascotas, etc.)
- calendario de disponibilidad visual para staff al gestionar reservas
- Gestión de reservas con múltiples tipos de habitación en una sola solicitud (split booking)
- Integración con calendarios externos (Google Calendar, Outlook, iCal)
- Reembolso automático dentro del flujo de cancelación
