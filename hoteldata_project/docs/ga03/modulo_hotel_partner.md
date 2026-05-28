# Modulo inicial Hotel Partner / Dueño de hotel

## Objetivo

Se implementa una primera capa de Partner Central para que un hotelero pueda consultar y administrar informacion basica de sus propiedades usando datos reales del proyecto, sin autenticacion estricta todavia.

## Rutas implementadas

- `GET /partner/hotels`
- `GET /partner/hotels/{prop_id}`
- `GET /partner/hotels/{prop_id}/performance`
- `GET /partner/hotels/{prop_id}/content`

## Fuente de datos

El modulo usa:

- `dim_hotels` como catalogo principal de propiedades
- `hotels` como maestra documental si existe informacion base
- `fact_hotel_reservations` como fuente preferida de rendimiento
- `fact_hotel_events` como fallback si el hecho principal estuviera vacio

Todas las consultas usan MongoDB con agregaciones o paginacion controlada. No se carga toda la coleccion en memoria.

## Funcionalidad implementada

### Listado de hoteles

Ruta: `GET /partner/hotels`

- lista propiedades desde `dim_hotels`
- permite buscar por nombre o `prop_id`
- muestra indicadores resumidos por hotel:
  - busquedas
  - clicks
  - reservas
  - ingresos brutos

### Detalle de hotel

Ruta: `GET /partner/hotels/{prop_id}`

- muestra perfil basico de la propiedad
- expone estrellas, review score, pais y location score
- muestra datos maestros disponibles si existen en la coleccion `hotels`

### Rendimiento

Ruta: `GET /partner/hotels/{prop_id}/performance`

Muestra:

- busquedas
- clicks
- reservas
- conversion
- click rate
- ingresos brutos
- precio promedio
- destinos con mayor actividad

### Contenido

Ruta: `GET /partner/hotels/{prop_id}/content`

- muestra datos actuales disponibles
- marca como planificado:
  - imagenes
  - politicas
  - CMS / contenido enriquecido

## Limites actuales

- No existe autenticacion estricta de partner.
- No existe PMS.
- No hay pagos ni reservas transaccionales.
- No se edita contenido real persistente todavia.
- No se toca ETL ni Airflow.

## Casos de uso actualizados

- CU13 Administrar perfil del hotel: Parcial
- CU14 Administrar imagenes y contenido del hotel: Parcial
- CU16 Consultar rendimiento de propiedades: Parcial

Permanecen parciales porque ya hay interfaz funcional de consulta, pero todavia no hay flujo completo de partner central con edicion persistente, aprobaciones, PMS, inventario ni contratos.

## Evidencias sugeridas

- Captura de `/partner/hotels`
- Captura de `/partner/hotels/{prop_id}`
- Captura de `/partner/hotels/{prop_id}/performance`
- Captura de `/partner/hotels/{prop_id}/content`
