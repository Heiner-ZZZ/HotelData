# Plan de Implementación: Tarifas Calendario

**Branch**: `020-tarifas-calendario` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Frontend                            Backend                          MongoDB
─────────────────                   ─────────────────                ──────
                                                     ┌──────────────────────────┐
  /management/rates/calendar ───────►               │ partner/services/        │
  (calendario de precios             PUT/PATCH       │ rates.py                 │──► hotel_rate_calendar
   por fecha y plan)                 /api/partner/   │ (update_rate_calendar,   │    {hotel_id}_{rate_plan_id}_
                                      rate-calendar/ │  get_rate_calendar,      │    {date}
                                      {id}           │  batch_update_rates)     │
                                                     └──────────────────────────┘
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/partner/properties/{id}/rate-calendar | Obtener calendario de precios mensual |
| PUT | /api/partner/rate-calendar/{entry_id} | Actualizar precio para una fecha específica |
| POST | /api/partner/properties/{id}/rate-calendar/batch | Actualización batch por rango de fechas y plan |

## Reglas de negocio

- El precio por fecha puede diferir del `base_price` del plan tarifario
- Se pueden definir precios especiales por temporada desde el calendario
- El precio debe ser > 0
- `_id` semántico: `{hotel_id}_{rate_plan_id}_{YYYY-MM-DD}`
