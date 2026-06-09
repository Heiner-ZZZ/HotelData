# Management Operational Data Step 2

## Alcance

Este paso conectó datos operativos reales/demo de MongoDB GA03 con FastAPI y Angular para el módulo de Management.

No se tocó:

- `fact_hotel_reservations`
- ETL
- Airflow
- la matriz de roles
- nombres manuales protegidos con `manual_override=true`

## Colecciones conectadas

- `room_types`
- `hotel_rooms`
- `room_inventory_calendar`
- `room_availability_blocks`
- `blackout_dates`
- `rate_plans`
- `hotel_rate_calendar`
- `rate_rules`
- `hotel_policies`
- `hotel_content_pages`
- `hotel_images`
- `promotion_campaigns`
- `coupon_codes`

## Pantallas que las consumen

- `/management`
  - usa `/api/dashboard/overview`
  - ahora muestra métricas operativas además de KPIs analíticos
- `/management/properties`
  - usa `/api/management/properties`
  - muestra `display_name`, badge manual/generado, checks operativos y score operativo
- `/management/properties/:propertyId`
  - usa `/api/management/properties/{prop_id}`
  - muestra badge de nombre manual, score operativo y checks por área
- `/management/rooms`
  - usa `/api/management/rooms`
  - conecta `room_types` y `hotel_rooms`
- `/management/availability`
  - usa `/api/management/availability`
  - conecta `room_inventory_calendar`, `room_availability_blocks` y `blackout_dates`
- `/management/rates`
  - usa `/api/management/rates`
  - conecta `rate_plans`, `hotel_rate_calendar`, `rate_rules`, promociones y cupones demo
- `/management/policies`
  - usa `/api/management/policies`
  - conecta `hotel_policies`
- `/management/amenities`
  - usa `/api/management/amenities`
  - conecta `hotel_content_pages` e `hotel_images`
- `/management/reports`
  - usa `/api/management/reports`
  - muestra total eventos, reservas detectadas, revenue, top hoteles, top destinos, top países y conteos operativos

## Datos demo_seed

Los datos sembrados en el paso previo siguen marcados con:

- `demo_seed=true`
- `source="ga03_operational_seed"`

Eso aplica especialmente a:

- `room_types`
- `hotel_rooms`
- `room_inventory_calendar`
- `rate_plans`
- `hotel_rate_calendar`
- `hotel_policies`
- `hotel_content_pages`
- `hotel_images`
- `promotion_campaigns`
- `coupon_codes`

## Preservación de nombres manuales

Las pantallas de Management y los endpoints de propiedades respetan:

- `display_name` manual si existe
- `manual_override=true`
- badge `Nombre editado manualmente`

El enriquecimiento automático no debe sobrescribir esos nombres; la protección quedó validada antes de este paso.

## Pendientes reales

- poblar `rate_rules`, `room_availability_blocks` y `blackout_dates` con más casos operativos reales, no solo demo/manuales
- ampliar `/management/reports` con filtros por propiedad, fecha y destino
- si el negocio lo requiere, conectar `facilities` cuando exista una colección estable para esa capa
- limpiar warnings de Angular no bloqueantes en componentes existentes

## Confirmación de integridad

- no se modificó el hecho principal `fact_hotel_reservations`
- no se cambiaron IDs técnicos (`prop_id`, `site_id`, etc.)
- no se sobrescribieron nombres manuales
