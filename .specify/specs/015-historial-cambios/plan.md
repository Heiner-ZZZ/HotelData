# Plan de Implementación: Historial de Cambios

**Branch**: `015-historial-cambios` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Frontend                            Backend                          MongoDB
─────────────────                   ─────────────────                ──────
                                                     ┌──────────────────────────┐
  /management/properties/:id/        GET              │ partner/services/       │
  history ───────────────────────────► /api/partner/  │ history.py               │──► hotel_profile_changes
                                      properties/     │ (list_changes,           │    (audit log)
                                      {id}/history    │  get_change_detail)     │
                                                     └──────────────────────────┘
```

## Componentes

| Archivo | Propósito |
|---------|-----------|
| `server/src/app/modules/partner/services/history.py` | `list_hotel_changes()`, `get_change_detail()` |
| `server/src/app/modules/partner/routes.py` | Endpoint `GET /api/partner/properties/{id}/history` |
| `frontend/src/app/features/partner/pages/history-page/*` | Tabla de auditoría con filtros |

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/partner/properties/{id}/history | Listar cambios con paginación y filtros (fecha, campo, usuario) |
| GET | /api/partner/properties/{id}/history/{change_id} | Detalle de un cambio específico |

## Colecciones

| Colección | Índices |
|-----------|---------|
| `hotel_profile_changes` | `{ hotel_id: 1, changed_at: -1 }`, `{ hotel_id: 1, field: 1 }` |
| `hotel_content_changes` | `{ hotel_id: 1, changed_at: -1 }` |
