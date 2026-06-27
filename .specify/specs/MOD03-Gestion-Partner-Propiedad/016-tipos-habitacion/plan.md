# Plan de Implementación: Tipos de Habitación

**Branch**: `016-tipos-habitacion` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Frontend                            Backend                          MongoDB
─────────────────                   ─────────────────                ──────
                                                     ┌──────────────────────────┐
  /management/rooms ──────────────────►              │ modules/partner/        │
  (CRUD: list, create, edit, delete)    CRUD         │ services/rooms.py       │──► room_types
                                                     │ (create_room_type,       │──► hotel_rooms
                                                     │  update_room_type,       │
                                                     │  delete_room_type,       │
                                                     │  list_room_types)        │
                                                     └──────────────────────────┘
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/partner/properties/{id}/room-types | Listar tipos de habitación de una propiedad |
| POST | /api/partner/properties/{id}/room-types | Crear nuevo tipo de habitación |
| PUT | /api/partner/room-types/{room_type_id} | Actualizar tipo de habitación |
| DELETE | /api/partner/room-types/{room_type_id} | Eliminar tipo (solo si sin reservas activas) |

## Reglas de negocio

- Un tipo de habitación pertenece a una sola propiedad
- No se puede eliminar un tipo con reservas activas o futuras
- `max_guests` debe ser ≥ 1
- `base_rate` debe ser > 0
- El nombre del tipo debe ser único dentro de la misma propiedad
