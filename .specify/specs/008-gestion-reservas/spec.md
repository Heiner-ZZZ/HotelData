# Especificación: Gestión de Reservas

**Versión**: 1.0 | **Estado**: Implementado

**Casos de uso TAF06**: CU-O06 (Gestionar reservas), CU-O07 (Check-in/out)

## 1. Objetivo

Permitir que el personal del hotel (staff/partner) gestione el ciclo de vida completo de las reservas: confirmar, rechazar, cancelar, listar con filtros, y realizar check-in/check-out.

## 2. Contexto

Una vez que el cliente solicita una reserva (spec 007), el staff del hotel debe poder gestionarla: confirmar la disponibilidad, rechazar si no es posible, y realizar el check-in/check-out durante la estancia del huésped.

## 3. Actores

- Staff / Partner hotelero
- Super admin

## 4. Funcionalidades

| ID | Descripción | Estado |
|----|-------------|--------|
| RF-001 | Listar reservas con filtros (estado, hotel, huésped, fechas) | ✅ |
| RF-002 | Ver detalle de reserva con historial de estados | ✅ |
| RF-003 | Confirmar reserva (pending → confirmed) | ✅ |
| RF-004 | Rechazar reserva (pending → rejected) | ✅ |
| RF-005 | Cancelar reserva (pending → cancelled) | ✅ |
| RF-006 | Realizar check-in (confirmed/pending → checked_in) | ✅ |
| RF-007 | Realizar check-out (checked_in → checked_out) | ✅ |
| RF-008 | Ver dashboard de check-ins/outs por fecha | ✅ |
| RF-009 | Ver estadísticas de reservas | ✅ |
| RF-010 | Reserva manual por partner | ✅ |

## 5. Flujo de estados (lifecycle)

```
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

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/reservations` | Listar reservas (con filtros opcionales) |
| GET | `/api/reservations/stats` | Estadísticas por estado |
| GET | `/api/reservations/{id}` | Detalle de reserva |
| POST | `/api/reservations` | Crear reserva |
| POST | `/api/reservations/{id}/confirm` | Confirmar reserva |
| POST | `/api/reservations/{id}/reject` | Rechazar reserva |
| POST | `/api/reservations/{id}/cancel` | Cancelar reserva |
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
  "total": 12,
  "active": 10,
  "completed": 1,
  "lost": 1
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

## 8. Dependencias

- booking_orders, booking_guests, booking_status_history, manual_reservations
