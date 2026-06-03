# Estrategia de enriquecimiento manual display

## Principio base

En HotelData el identificador técnico es la llave estable del modelo analítico.

Ejemplos:
- `fact_hotel_reservations.prop_id -> dim_hotels.prop_id`
- `fact_hotel_reservations.srch_destination_id -> dim_destinations.srch_destination_id`
- `fact_hotel_reservations.visitor_location_country_id -> dim_visitor_countries.visitor_location_country_id`
- `fact_hotel_reservations.site_id -> dim_sites.site_id`

Estos IDs no cambian por edición manual.

## Qué sí puede cambiar

Lo que sí puede enriquecerse manualmente es la capa visible:
- `display_name`
- `hotel_name`
- `display_country_label`
- descripciones visibles de perfil

Esto permite corregir nombres comerciales sin romper relaciones fact-dim ni el dashboard.

## Campos de control en `dim_hotels`

Se introducen campos para distinguir entre nombre generado y nombre ajustado manualmente:

- `original_generated_name`
- `manual_override`
- `name_source`
- `updated_by`
- `updated_at`

Convención:
- `manual_override = false`
  - el nombre visible sigue siendo generado o heredado
- `manual_override = true`
  - existe intervención manual y debe preservarse
- `name_source = "generated_from_id"`
  - nombre visible generado por lógica base
- `name_source = "manual"`
  - nombre visible editado manualmente

## Regla de preservación

El ETL y los scripts de enriquecimiento no deben sobrescribir un nombre manual.

En la práctica:
- el ID técnico sigue siendo la referencia real
- el nombre visible se trata como capa de presentación
- si `manual_override = true`, el sistema conserva `display_name` manual
- los nombres generados pasan a ser fallback, no verdad absoluta

## Historial de cambios

Cada edición manual de perfil se registra en `hotel_profile_changes` con:

- `prop_id`
- `field`
- `old_value`
- `new_value`
- `changed_by`
- `changed_at`
- `reason`
- `source = "manual_profile_edit"`

Esto deja trazabilidad sin borrar datos previos.

## Flujo recomendado

1. La carga analítica conserva IDs técnicos.
2. La capa visible genera nombres fallback cuando no existe edición manual.
3. El usuario de gestión puede editar perfil visible por API.
4. El cambio queda marcado con `manual_override = true`.
5. El historial se escribe en `hotel_profile_changes`.
6. La búsqueda, detalle, partner y gestión consumen primero el nombre manual.

## Resultado esperado

- el ID técnico no cambia
- el nombre visible sí puede cambiar
- el ETL debe preservar `manual_override`
- el historial queda en `hotel_profile_changes`
- los nombres generados son fallback, no nombres reales
