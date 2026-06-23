# Plan de Implementación: Frontend - Reseñas

**Branch**: `048-frontend-resenas` | **Spec**: [spec.md](spec.md)

## Componentes

| Componente | Ruta | CU asociado |
|-----------|------|-------------|
| ReviewForm | /reviews/new | CU-O22 |
| ReviewListPage | /reviews | CU-O22 |
| ModeratePage | /reviews/moderate | CU-O23 |
| ReviewDetailPage | /reviews/:id | CU-O23 |

## Módulo existente

`frontend/src/app/features/reviews/` con rutas lazy-loaded. Backend reviews ya implementado en `server/src/app/modules/reviews/routes.py`.

## Entregables

Este spec documenta la UI de reseñas: formulario de registro (post-estancia), listado en detalle de hotel, panel de moderación y respuesta del hotel.
