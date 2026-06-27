# Plan de Implementación: Gestionar Disponibilidad y Estado de Habitaciones

**Branch**: `feature/051-gestionar-disponibilidad-habitaciones` | **Spec**: 051

## Arquitectura

```
Recepcionista → GET /partner/hotels/{prop_id}/rooms/status → room_status_log
              → PUT /api/housekeeping/rooms/{room_id}/status → room_status_log
              → POST /api/management/rooms/{room_id}/assign-room-type → hotel_rooms
              → GET /api/housekeeping/rooms/availability → room_inventory_calendar
```

## Componentes

| Archivo | Propósito |
|---------|-----------|
| `server/src/app/modules/housekeeping/room_status_service.py` | Servicio de estado |
| `frontend/src/app/features/housekeeping/room-status/` | RoomStatusPanel |

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /partner/hotels/{prop_id}/rooms/status | Panel de estado HTML |
| GET | /api/housekeeping/rooms/status | API de estado JSON |
| PUT | /api/housekeeping/rooms/{room_id}/status | Actualizar estado |
| POST | /api/management/rooms/{room_id}/assign-room-type | Asignar tipo habitación |

## Flujo

1. Usuario navega al panel → GET rooms/status
2. Sistema consulta hotel_rooms + room_status_log
3. Usuario cambia estado → PUT rooms/{id}/status
4. Sistema registra en room_status_log + actualiza hotel_rooms