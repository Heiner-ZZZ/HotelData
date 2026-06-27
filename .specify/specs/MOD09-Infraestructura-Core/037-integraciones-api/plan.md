# Plan de Implementación: Integraciones API

**Branch**: `037-integraciones-api` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Admin
  → IntegracionesPage
    → GET /api/admin/integrations
      → Lista de endpoints con estado de validación
      → Documentación OpenAPI
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/admin/integrations | Listar integraciones/endpoints |
| GET | /api/admin/integrations/{id}/logs | Consumo de API por endpoint |

## Entregables

- Documentación OpenAPI actualizada (todos los endpoints)
- Health checks por módulo
- Registro de consumo de API (en logs)
- Preparación para API keys de partners externos
