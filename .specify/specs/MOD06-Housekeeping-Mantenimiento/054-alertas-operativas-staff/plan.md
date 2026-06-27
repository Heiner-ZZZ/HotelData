# Plan: Alertas Operativas

## Componentes
- `server/src/app/modules/notifications/alert_service.py`
- `frontend/src/app/features/notifications/` InternalAlertsPanel

## Endpoints
| GET | /api/notifications/alerts | Panel alertas |
| PUT | /api/notifications/alerts/{id}/status | Actualizar estado |