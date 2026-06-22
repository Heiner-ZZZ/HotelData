# Limpieza lógica MongoDB GA03 - Paso 1

## Alcance

Este paso realizó una preparación mínima y segura sobre MongoDB para ordenar el modelo GA03 sin alterar la base analítica principal.

- No se borraron colecciones.
- No se borraron documentos.
- No se modificó `fact_hotel_reservations`.
- No se tocaron ETL ni Airflow.
- No se crearon nuevas colecciones en este paso.

## Cambios aplicados

### 1. Alias display seguro en `dim_sites`

Se ejecutó [normalize_display_aliases_ga03.py](/C:/HotelData/hoteldata_project/scripts/normalize_display_aliases_ga03.py) para completar `site_name` únicamente donde faltaba.

Regla aplicada:
- usar `site_display_name` si existe
- si no, usar `site_label`
- si no, usar `Sitio {site_id}`

Resultado:
- documentos en `dim_sites`: `32`
- `site_name` antes: `0`
- `site_name` después: `32`
- documentos actualizados: `32`

### 2. Métricas del dashboard corregidas

Se ajustó [service.py](/C:/HotelData/hoteldata_project/src/app/features/dashboard/service.py) para que `GET /api/dashboard/overview` calcule directamente desde `fact_hotel_reservations`:

- `total_events = 300000`
- `total_reservations = 8338`
- `total_clicks = 13431`
- `gross_revenue = 3327127.4`
- `avg_price = 176.36`
- `promotions = 64992`
- `conversion_rate = 2.78`
- `click_rate = 4.48`
- `rejected_records = 0`

Compatibilidad preservada:
- se mantiene `bookings`
- se mantiene `booking_rate`
- se agregan `total_reservations`, `total_clicks`, `conversion_rate` y `click_rate`

### 3. Seed operativo demo mínimo

Se ejecutó [seed_operational_demo_ga03.py](/C:/HotelData/hoteldata_project/scripts/seed_operational_demo_ga03.py) con `prop_id` reales `1, 2, 3, 4, 5`.

Todos los documentos sembrados quedaron con:
- `demo_seed = true`
- `source = "ga03_operational_seed"`

Conteos antes/después:

| Colección | Antes | Después | Delta |
| --- | ---: | ---: | ---: |
| `room_types` | 0 | 10 | 10 |
| `hotel_rooms` | 0 | 10 | 10 |
| `room_inventory_calendar` | 0 | 70 | 70 |
| `rate_plans` | 0 | 10 | 10 |
| `hotel_rate_calendar` | 0 | 70 | 70 |
| `hotel_policies` | 0 | 5 | 5 |
| `hotel_content_pages` | 0 | 5 | 5 |
| `hotel_images` | 0 | 10 | 10 |
| `promotion_campaigns` | 0 | 5 | 5 |
| `coupon_codes` | 0 | 5 | 5 |

Cobertura sembrada:
- `room_types`: 2 por hotel
- `room_inventory_calendar`: 7 días por `room_type`
- `rate_plans`: 2 por hotel
- `hotel_rate_calendar`: 7 días por `rate_plan`
- `hotel_policies`: 1 por hotel
- `hotel_content_pages`: 1 por hotel
- `hotel_images`: 2 por hotel
- `promotion_campaigns`: 1 por hotel
- `coupon_codes`: 1 por promoción

## Validaciones ejecutadas

Se ejecutaron:
- `python scripts/normalize_display_aliases_ga03.py`
- `python scripts/seed_operational_demo_ga03.py`
- `python scripts/validate_ga03_mongo_step1.py`
- `python scripts/validate_frontend_backend_contract.py`

Resultados principales:
- `dim_sites.site_name`: `32/32`
- `fact_hotel_reservations`: se mantuvo en `300000`
- `dashboard overview`: devuelve `total_reservations = 8338`
- colecciones operativas demo: todas con datos `> 0`
- contrato frontend/backend: `16` endpoints revisados, `0` errores de contrato

## Legacy pendiente

No se tocó ninguna colección legacy en este paso. Quedan marcadas para revisión futura, sin borrar nada todavía:

- `dim_date`
- `dim_countries`
- `fact_hotel_events`
- `dataset_container`

## Archivos de soporte

- Auditoría base: [mongodb_model_audit.md](/C:/HotelData/hoteldata_project/docs/ga03/mongodb_model_audit.md)
- Reporte alias: [normalize_display_aliases_ga03.json](/C:/HotelData/hoteldata_project/data/reports/normalize_display_aliases_ga03.json)
- Reporte seed: [seed_operational_demo_ga03.json](/C:/HotelData/hoteldata_project/data/reports/seed_operational_demo_ga03.json)
- Validación paso 1: [validate_ga03_mongo_step1.json](/C:/HotelData/hoteldata_project/data/reports/validate_ga03_mongo_step1.json)

## Siguiente paso recomendado

Con el hecho principal intacto, las llaves cubiertas y las colecciones operativas mínimas pobladas, el siguiente paso seguro es:

- separar formalmente colecciones activas vs legacy por documentación y contrato interno
- decidir cuáles colecciones operativas demo pasan a seed funcional y cuáles quedan solo para pruebas
- después de eso, preparar limpieza lógica de compatibilidad sin borrado físico
