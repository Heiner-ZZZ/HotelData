# Plan de Implementación: Frontend - Gestión Hotelera (Partner)

**Branch**: `044-frontend-partner` | **Spec**: [spec.md](spec.md)

## Componentes

| Componente | Ruta | CU asociado |
|-----------|------|-------------|
| PropertyListPage | /management/properties | CU-O12 |
| PropertyEditPage | /management/properties/:id/edit | CU-O12 |
| RoomTypesPage | /management/rooms | CU-O14 |
| InventoryCalendar | /management/availability | CU-O15, CU-O16 |
| RatePlansPage | /management/rates | CU-O17, CU-O18 |
| PoliciesPage | /management/policies | CU-O20 |
| ContentPage | /management/content | CU-O21 |
| AmenitiesPage | /management/amenities | CU-O21 |

## Módulo existente

`frontend/src/app/features/partner/` con rutas lazy-loaded:
- `partner.routes.ts` define las rutas del módulo
- Servicios: `partner.service.ts` (HTTP client)

## Entregables

Este spec documenta la UI de gestión hotelera existente y asegura cobertura de todos los CU-O12 al CU-O21.
