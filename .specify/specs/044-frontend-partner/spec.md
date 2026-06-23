# Especificacion: Frontend - Gestion Hotelera (Partner)

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O12 al CU-O21 (Partner: rooms, inventory, rates, policies, content)

## 1. Objetivo

UI de gestion hotelera: propiedades, habitaciones, inventario, tarifas, politicas, contenido.

## 2. Componentes

| Componente | Ruta | CU asociado |
|------------|------|-------------|
| PropertyListPage | /management/properties | CU-O12 |
| PropertyEditPage | /management/properties/:id/edit | CU-O12 |
| RoomTypesPage | /management/rooms | CU-O14 |
| InventoryCalendar | /management/availability | CU-O15, CU-O16 |
| RatePlansPage | /management/rates | CU-O17, CU-O18 |
| PoliciesPage | /management/policies | CU-O20 |
| ContentPage | /management/content | CU-O21 |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | PropertyListPage con tabla de propiedades asignadas | Alta |
| RF-002 | PropertyEditPage con formulario de edicion de perfil | Alta |
| RF-003 | RoomTypesPage con CRUD de tipos de habitacion | Alta |
| RF-004 | InventoryCalendar con vista mensual | Alta |
| RF-005 | RatePlansPage con tabla de planes tarifarios | Alta |
| RF-006 | PoliciesPage con formulario de politicas | Alta |
| RF-007 | ContentPage con editor de descripcion y amenities | Alta |

## 4. Dependencias

- frontend/src/app/features/partner/
- partner.routes.ts
