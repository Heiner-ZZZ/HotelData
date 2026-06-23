# Plan de Implementación: Inventario y Disponibilidad

**Branch**: `017-inventario-disponibilidad` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Frontend                            Backend                          MongoDB
─────────────────                   ─────────────────                ──────
                                                     ┌──────────────────────────┐
  /management/availability ─────────►               │ partner/services/        │
  (calendario mensual,               PUT/PATCH       │ inventory.py             │──► room_inventory_calendar
   drag & drop para                  /api/partner/   │ (update_inventory,       │    {hotel_id}_{room_type_id}_
   actualizar totals)                inventory/      │  get_calendar,           │    {date}
                                      {id}           │  batch_update)           │
                                                     └──────────────────────────┘
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/partner/properties/{id}/inventory | Obtener calendario mensual |
| PUT | /api/partner/inventory/{inventory_id} | Actualizar total/disponible/blocked con optimistic locking |
| POST | /api/partner/properties/{id}/inventory/batch | Actualización batch por rango de fechas |

## Optimistic Locking

- Cada documento tiene campo `version` (integer)
- Al actualizar: `filter: { _id, version: current_version }`, `update: { ..., version: current_version + 1 }`
- Si no coincide, error 409 Conflict → frontend recarga
