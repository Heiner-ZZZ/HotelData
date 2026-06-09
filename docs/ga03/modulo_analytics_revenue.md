# Modulo inicial Revenue y Analytics

## Objetivo

Se implementa una primera capa analitica real para revenue manager y analista comercial, usando agregaciones MongoDB sobre hechos y dimensiones ya cargados.

## Rutas implementadas

- `GET /analytics/reservations`
- `GET /analytics/conversion`
- `GET /analytics/revenue`
- `GET /analytics/promotions`
- `GET /analytics/visitor-markets`

## Alcance funcional

### Reservations

- total eventos
- reservas
- clicks
- ingresos brutos
- precio promedio

### Conversion

- tasa click
- tasa reserva
- abandono
- conversion posterior al click

### Revenue

- ingresos por hotel
- ingresos por destino
- precio promedio

### Promotions

- comparacion con promocion vs sin promocion

### Visitor markets

- analisis por pais visitante
- analisis por `site_id`

## Fuente de datos

- `fact_hotel_reservations`
- `fact_hotel_events` como fallback si el hecho principal estuviera vacio
- `dim_hotels`
- `dim_destinations`
- `dim_visitor_countries`
- `dim_sites`

## Restricciones mantenidas

- No reemplaza ETL.
- No modifica hechos ni dimensiones.
- No toca Airflow.
- No carga todos los registros en memoria.
- Usa solo consultas analiticas con aggregation pipeline.

## Casos de uso impactados

- CU24 Evaluar impacto de promociones: Implementado
- CU25 Consultar dashboard de reservas: Implementado
- CU26 Analizar conversión búsqueda-click-reserva: Implementado
- CU27 Analizar ingresos brutos por hotel y destino: Implementado
- CU28 Analizar comportamiento por país visitante y canal: Implementado

## Evidencias sugeridas

- Captura de `/analytics/reservations`
- Captura de `/analytics/conversion`
- Captura de `/analytics/revenue`
- Captura de `/analytics/promotions`
- Captura de `/analytics/visitor-markets`
