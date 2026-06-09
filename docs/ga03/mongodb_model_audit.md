# Auditoría del modelo MongoDB GA03

- Generado: `2026-06-03T20:29:59.298859+00:00`
- Base auditada: `hoteldata_hub`
- URI objetivo: `mongodb://172.22.192.1:27017`
- Modo: `solo lectura`

## Resumen ejecutivo

- Colecciones auditadas: **53**
- Filas en `fact_hotel_reservations`: **300,000**
- Relaciones con cobertura completa: **9**
- Relaciones con faltantes: **0**

## Relaciones fact-dim

| Relación | Cobertura filas | Cobertura llaves | Filas faltantes | Llaves faltantes | Estado |
| --- | ---: | ---: | ---: | ---: | --- |
| `prop_id` -> `dim_hotels.prop_id` | 100.00% | 100.00% | 0 | 0 | Completa |
| `srch_destination_id` -> `dim_destinations.srch_destination_id` | 100.00% | 100.00% | 0 | 0 | Completa |
| `visitor_location_country_id` -> `dim_visitor_countries.visitor_location_country_id` | 100.00% | 100.00% | 0 | 0 | Completa |
| `site_id` -> `dim_sites.site_id` | 100.00% | 100.00% | 0 | 0 | Completa |
| `date_key` -> `dim_dates.date_key` | 100.00% | 100.00% | 0 | 0 | Completa |
| `occupancy_profile_id` -> `dim_occupancy_profile.occupancy_profile_id` | 100.00% | 100.00% | 0 | 0 | Completa |
| `stay_length_category_id` -> `dim_stay_length_category.stay_length_category_id` | 100.00% | 100.00% | 0 | 0 | Completa |
| `booking_window_category_id` -> `dim_booking_window_category.booking_window_category_id` | 100.00% | 100.00% | 0 | 0 | Completa |
| `price_category_id` -> `dim_price_category.price_category_id` | 100.00% | 100.00% | 0 | 0 | Completa |

## Campos display

| Colección | Filas | Display disponible | Display faltante |
| --- | ---: | --- | --- |
| `dim_hotels` | 119,831 | `display_name`, `hotel_name`, `hotel_label` | Ninguno |
| `dim_destinations` | 13,808 | `destination_display_name`, `destination_name`, `destination_label` | Ninguno |
| `dim_visitor_countries` | 199 | `country_display_name`, `country_name`, `visitor_country_label` | Ninguno |
| `dim_sites` | 32 | `site_display_name`, `site_label` | `site_name` |

## Métricas de negocio en fact

- `click_bool = true`: **13,431**
- `reserva_bool = true`: **8,338**
- `reservas_brutas_usd > 0`: **8,338**
- `promotion_flag = true`: **64,992**

## Clasificación de colecciones

| Colección | Conteo | Clasificación | Referencias código |
| --- | ---: | --- | ---: |
| `attractions` | 2 | Operativa parcial | 7 |
| `blackout_dates` | 0 | Preparada sin datos | 10 |
| `booking_guests` | 2 | Operativa parcial | 6 |
| `booking_orders` | 2 | Operativa parcial | 7 |
| `booking_status_history` | 2 | Operativa parcial | 6 |
| `contacts` | 1 | Operativa parcial | 7 |
| `coupon_codes` | 0 | Preparada sin datos | 8 |
| `data_quality_reports` | 16 | Gobierno de datos | 18 |
| `dataset_container` | 0 | Legacy sin uso | 9 |
| `dim_booking_window_category` | 4 | Activa | 14 |
| `dim_click_status` | 2 | Activa | 9 |
| `dim_countries` | 0 | Legacy/compatibilidad | 6 |
| `dim_date` | 0 | Legacy/compatibilidad | 15 |
| `dim_dates` | 6,018 | Activa | 15 |
| `dim_destinations` | 13,808 | Activa | 25 |
| `dim_hotels` | 119,831 | Activa | 30 |
| `dim_occupancy_profile` | 204 | Activa | 13 |
| `dim_price_category` | 4 | Activa | 15 |
| `dim_promotions` | 4 | Activa | 15 |
| `dim_reservation_status` | 4 | Activa | 15 |
| `dim_sites` | 32 | Activa | 15 |
| `dim_stay_length_category` | 3 | Activa | 15 |
| `dim_visitor_countries` | 199 | Activa | 24 |
| `etl_executions` | 15 | Gobierno de datos | 24 |
| `facilities` | 3 | Operativa parcial | 7 |
| `fact_hotel_events` | 100,000 | Legacy/compatibilidad | 20 |
| `fact_hotel_reservations` | 300,000 | Activa | 45 |
| `hotel_content_changes` | 15 | Operativa parcial | 11 |
| `hotel_content_pages` | 0 | Preparada sin datos | 8 |
| `hotel_images` | 0 | Preparada sin datos | 9 |
| `hotel_policies` | 0 | Preparada sin datos | 14 |
| `hotel_quality` | 1 | Operativa parcial | 7 |
| `hotel_rate_calendar` | 0 | Preparada sin datos | 10 |
| `hotel_rooms` | 0 | Preparada sin datos | 9 |
| `hotels` | 1 | Operativa parcial | 83 |
| `locations` | 1 | Operativa parcial | 7 |
| `manual_reservations` | 0 | Preparada sin datos | 6 |
| `permissions` | 11 | Seguridad activa | 34 |
| `promotion_campaigns` | 0 | Preparada sin datos | 8 |
| `rate_plans` | 0 | Preparada sin datos | 12 |
| `rate_rules` | 0 | Preparada sin datos | 8 |
| `rejected_records` | 0 | Gobierno de datos | 30 |
| `role_permissions` | 43 | Seguridad activa | 11 |
| `roles` | 9 | Seguridad activa | 41 |
| `room_availability_blocks` | 0 | Preparada sin datos | 9 |
| `room_inventory_calendar` | 0 | Preparada sin datos | 9 |
| `room_types` | 0 | Preparada sin datos | 19 |
| `search_logs` | 4 | Operativa parcial | 13 |
| `system_catalogs` | 8 | Gobierno de datos | 10 |
| `user_activity_logs` | 286 | Seguridad activa | 15 |
| `user_sessions` | 129 | Seguridad activa | 14 |
| `users` | 8 | Seguridad activa | 51 |
| `websites` | 1 | Operativa parcial | 7 |

## Candidatas

### Relaciones con cobertura completa

- prop_id -> dim_hotels.prop_id
- srch_destination_id -> dim_destinations.srch_destination_id
- visitor_location_country_id -> dim_visitor_countries.visitor_location_country_id
- site_id -> dim_sites.site_id
- date_key -> dim_dates.date_key
- occupancy_profile_id -> dim_occupancy_profile.occupancy_profile_id
- stay_length_category_id -> dim_stay_length_category.stay_length_category_id
- booking_window_category_id -> dim_booking_window_category.booking_window_category_id
- price_category_id -> dim_price_category.price_category_id

### Relaciones con faltantes

- Ninguna.

### Campos display faltantes

- `dim_sites`: `site_name`

### Colecciones candidatas a poblar

- `blackout_dates`
- `coupon_codes`
- `hotel_content_pages`
- `hotel_images`
- `hotel_policies`
- `hotel_rate_calendar`
- `hotel_rooms`
- `manual_reservations`
- `promotion_campaigns`
- `rate_plans`
- `rate_rules`
- `room_availability_blocks`
- `room_inventory_calendar`
- `room_types`

### Colecciones candidatas a marcar como legacy

- `dataset_container`
- `dim_countries`
- `dim_date`
- `fact_hotel_events`

## Recomendación de siguiente paso

- La integridad de llaves está estable; el siguiente paso recomendable es completar campos display en dimensiones visibles para endurecer el consumo frontend/reportes.
