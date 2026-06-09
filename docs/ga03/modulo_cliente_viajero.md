# Modulo inicial Cliente/Viajero

## Objetivo

Se implementa una primera capa web orientada al cliente/viajero para que HotelData Hub Analytics se vea como una plataforma de busqueda hotelera inspirada en Expedia/Trivago, sin crear reservas reales ni pagos.

## Rutas implementadas

- `GET /hotels/search`
- `GET /hotels/{prop_id}`
- `GET /hotels/compare`

## Fuente de datos

Las pantallas usan datos existentes de MongoDB:

- `dim_hotels`
- `dim_destinations`
- `fact_hotel_reservations`
- `fact_hotel_events` como fallback si `fact_hotel_reservations` esta vacia

No se toca ETL, Airflow, PocketBase ni la logica de carga.

## Funcionalidad implementada

### Busqueda de hoteles

Ruta: `GET /hotels/search`

Permite filtrar por:

- destino o `srch_destination_id`
- precio minimo
- precio maximo
- estrellas minimas
- promocion
- adultos
- ninos
- habitaciones

La paginacion muestra 20 hoteles por pagina y usa agregaciones de MongoDB para evitar cargar todos los datos en memoria.

### Detalle de hotel

Ruta: `GET /hotels/{prop_id}`

Muestra:

- `prop_id`
- estrellas
- review score
- pais
- precio promedio
- reservas
- clicks
- conversion
- destinos asociados

### Comparacion de hoteles

Ruta: `GET /hotels/compare`

Permite comparar hasta 3 hoteles usando query params:

```text
/hotels/compare?prop_id=123&prop_id=456&prop_id=789
```

Compara:

- precio promedio
- reservas
- clicks
- review score
- estrellas
- conversion
- revenue bruto

## Limites actuales

- No crea reservas transaccionales.
- No procesa pagos.
- No calcula disponibilidad real por habitacion.
- No administra inventario hotelero.
- No reemplaza `/ta02`, `/ta02/crud` ni `/etl-status`.

## Casos de uso impactados

- CU01 Buscar hoteles por destino, fecha y ocupacion: Parcial
- CU02 Filtrar hoteles por precio, estrellas, promocion y servicios: Parcial
- CU03 Consultar detalle de hotel: Parcial
- CU04 Comparar hoteles disponibles: Parcial

Estos casos pasan a tener interfaz real inicial, pero permanecen parciales porque el alcance GA03 no incluye reservas reales, disponibilidad transaccional, pagos ni inventario.

## Evidencias sugeridas

- Captura de `/hotels/search` con filtros aplicados.
- Captura de resultados paginados de busqueda.
- Captura de `/hotels/{prop_id}` con metricas analiticas.
- Captura de `/hotels/compare` con hasta 3 hoteles.
