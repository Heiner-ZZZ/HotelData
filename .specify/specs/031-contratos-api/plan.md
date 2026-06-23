# Plan de Implementación: Contratos API

**Branch**: `031-contratos-api` | **Spec**: [spec.md](spec.md)

## Arquitectura

FastAPI genera OpenAPI automáticamente. Este spec documenta y valida los contratos.

```
OpenAPI (/docs) ← FastAPI (Pydantic models)
  → Scripts de validación frontend-backend
  → Health check endpoint
```

## Componentes

| Archivo | Propósito |
|---------|-----------|
| `server/src/app/modules/health/routes.py` | Endpoint GET /health |
| `server/scripts/validate_angular_routes_contract.py` | Validación rutas Angular vs backend |
| `server/scripts/validate_frontend_backend_contract.py` | Validación contratos API |

## Endpoints base

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /health | Health check del sistema |
| GET | /docs | Documentación OpenAPI (Swagger) |
| GET | /openapi.json | Schema OpenAPI en JSON |

## Entregables

- Documentación OpenAPI actualizada en /docs
- Scripts de validación de contrato funcionales
- Health check endpoint
