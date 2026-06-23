# Plan de Implementación: Planes Tarifarios

**Branch**: `019-planes-tarifarios` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Frontend                            Backend                          MongoDB
─────────────────                   ─────────────────                ──────
                                                     ┌──────────────────────────┐
  /management/rates ──────────────────►              │ partner/services/        │
  (CRUD: list, create, edit, delete)   CRUD          │ rates.py                 │──► rate_plans
                                      /api/partner/  │ (create_rate_plan,       │──► rate_rules
                                      rate-plans/    │  update_rate_plan,       │
                                                     │  list_rate_plans,        │
                                                     │  delete_rate_plan)       │
                                                     └──────────────────────────┘
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/partner/properties/{id}/rate-plans | Listar planes tarifarios |
| POST | /api/partner/properties/{id}/rate-plans | Crear plan tarifario |
| PUT | /api/partner/rate-plans/{plan_id} | Actualizar plan |
| DELETE | /api/partner/rate-plans/{plan_id} | Eliminar (solo sin reservas activas) |

## Reglas de negocio

- Un plan tarifario se asocia a un tipo de habitación
- `base_price` define la tarifa base por noche
- Se pueden definir reglas por temporada (temporada alta/baja, eventos especiales)
- Las reglas se almacenan en `rate_rules` (solo lectura desde UI)
- No se puede eliminar un plan con reservas activas
