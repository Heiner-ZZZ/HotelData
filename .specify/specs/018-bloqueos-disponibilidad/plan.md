# Plan de Implementación: Bloqueos de Disponibilidad

**Branch**: `018-bloqueos-disponibilidad` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Frontend                            Backend                          MongoDB
─────────────────                   ─────────────────                ──────
                                                     ┌──────────────────────────┐
  /management/availability ─────────►               │ partner/services/        │
  (sección "Bloqueos")               CRUD            │ blackouts.py             │──► blackout_dates
                                      /api/partner/  │ (create_blackout,        │──► room_availability_blocks
                                      blackouts/     │  list_blackouts,         │
                                                     │  delete_blackout,        │
                                                     │  list_blocks)            │
                                                     └──────────────────────────┘
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/partner/properties/{id}/blackouts | Listar bloqueos de la propiedad |
| POST | /api/partner/properties/{id}/blackouts | Crear bloqueo por rango de fechas |
| DELETE | /api/partner/blackouts/{blackout_id} | Eliminar bloqueo |
| GET | /api/partner/properties/{id}/availability-blocks | Listar bloques de disponibilidad |

## Reglas de negocio

- Un bloqueo aplica a un tipo de habitación específico o a toda la propiedad
- Los rangos de fecha no pueden solaparse para el mismo room_type
- Al crear bloqueo, se actualiza `room_inventory_calendar.blocked` para las fechas afectadas
- Se puede definir motivo del bloqueo (mantenimiento, reserva grupal, temporada cerrada)
