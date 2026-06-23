# Plan de Implementación: Monitoreo de Servicios

**Branch**: `032-monitoreo-servicios` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Super Admin
  → MonitoringPage
    → GET /health (estado global)
    → GET /api/admin/health/details
      → Verifica: MongoDB, Redis, PocketBase, Airflow
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /health | Health check rápido (status general) |
| GET | /api/admin/health/details | Estado detallado de cada servicio |

## Servicios monitoreados

| Servicio | Verificación |
|----------|-------------|
| MongoDB | `db.command('ping')` |
| Redis | `redis_client.ping()` |
| PocketBase | `GET /api/health` |
| Airflow | `GET /api/v1/health` (si configurado) |

## Frontend

MonitoringPage con cards por servicio: indicador verde/rojo, última comprobación, tiempo de respuesta.
