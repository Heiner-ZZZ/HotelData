# Plan de Implementación: Políticas Hoteleras

**Branch**: `022-politicas-hoteleras` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Frontend                            Backend                          MongoDB
─────────────────                   ─────────────────                ──────
                                                     ┌──────────────────────────┐
  /management/policies ─────────────►               │ partner/services/        │
  (check-in/out, cancelación,        CRUD            │ content/save.py          │──► hotel_policies
   mascotas, niños)                  /api/partner/   │ (update_policies,        │
                                      policies/      │  get_policies)           │
                                                     └──────────────────────────┘
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/partner/properties/{id}/policies | Obtener políticas del hotel |
| PUT | /api/partner/properties/{id}/policies | Actualizar políticas (check-in, check-out, cancelación, mascotas, niños) |

## Colecciones

| Colección | Campos |
|-----------|--------|
| `hotel_policies` | `check_in_time`, `check_out_time`, `cancellation_hours`, `pets_allowed`, `pet_fee`, `children_allowed`, `extra_bed_fee`, `min_stay`, `max_stay` |

## Reglas de negocio

- `check_out_time` debe ser después de `check_in_time`
- `cancellation_hours` define horas antes del check-in para cancelación gratuita
- `min_stay` y `max_stay` en noches mínimas/máximas
- Los cambios se registran en `hotel_content_changes`
