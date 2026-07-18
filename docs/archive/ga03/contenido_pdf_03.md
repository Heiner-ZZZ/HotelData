# Contenido PDF GA03 - HotelData Analytics

## Portada

**Proyecto:** HotelData Analytics  
**Entrega:** GA03 - Reservas hoteleras  
**Tarea:** `TASK_NUMBER=03`  
**Volumen objetivo:** `TARGET_RECORDS=300000`  
**Fuente operacional:** PocketBase `hotel_reservation_events_03`  
**Base analítica:** MongoDB `hoteldata_hub`  
**DAG:** `hoteldata_reservas_03_pipeline`  
**Video:** [Agregar link del video en primera página]

## Introducción

GA03 consolida el avance de HotelData Analytics como plataforma web/responsiva de reservas hoteleras inspirada en Expedia/Trivago. El alcance implementado se concentra en datos, analítica, CRUD analítico, auditoría y ETL.

No se documentan como implementados login real, roles reales, pagos, PMS, reservas transaccionales completas, habitaciones, tarifas operativas ni CMS hotelero.

## Alcance GA03

- Preparación administrativa: CSV -> PocketBase.
- ETL principal: PocketBase -> JSONL -> Parquet -> MongoDB.
- Hecho principal: `fact_hotel_reservations`.
- 12 dimensiones activas.
- Reportes de ejecución, calidad y validación.
- Interfaz `/etl-status` ampliada para GA03.
- Docker y Redis como preparación futura, no como ejecución requerida.

## Diagramas

Incluir renderizados:

- `diagrams/ga03_database.puml`
- `diagrams/ga03_use_cases.puml`

## Casos de uso

La visión funcional se documenta con exactamente 32 casos de uso agrupados en 8 paquetes:

1. Experiencia del cliente y búsqueda hotelera.
2. Cuenta, sesión y perfil de usuario.
3. Core de reservas hoteleras.
4. Gestión hotelera / Partner Central.
5. Habitaciones, inventario y disponibilidad.
6. Tarifas, promociones y revenue.
7. Analytics, BI y toma de decisiones.
8. Administración, datos, ETL y gobierno.

Estados:

- Implementado: CU25, CU29, CU30, CU32.
- Parcial: CU01, CU02, CU03, CU04, CU12, CU24, CU26, CU27, CU28.
- Planificado: CU05, CU06, CU07, CU08, CU09, CU10, CU11, CU13, CU14, CU15, CU16, CU17, CU18, CU19, CU20, CU21, CU22, CU23, CU31.

La descripción completa de cada CU está en `docs/ga03/casos_uso_ga03.md`.

## Diseño de base de datos

Incluir:

- Modelo actual implementado.
- Modelo futuro planificado.
- Hechos, 12 dimensiones activas, control, documental/operativo actual y colecciones legadas.

La descripción completa está en `docs/ga03/diseno_base_datos_ga03.md`.

## Modelo futuro

Incluir como planificado:

- Seguridad, usuarios, roles y permisos.
- Perfiles de viajero.
- Partner Central.
- Habitaciones, inventario y disponibilidad.
- Tarifas, promociones y revenue.
- Reservas, pagos, reembolsos y facturas.
- PMS, webhooks, notificaciones, Redis y Docker.

La descripción completa está en `docs/ga03/modelo_futuro_ga03.md`.

## Interfaz ETL

La sección `/etl-status` fue reutilizada y ampliada:

- GA03 aparece como tarea actual.
- TAF01 y TA02 quedan como históricos colapsados.
- Se separa preparación administrativa de fuente y ETL principal.
- Se muestran validaciones, estados, reportes y mensajes controlados.
- Se evita mostrar JSON técnico gigante por defecto.

## Evidencias sugeridas

- PocketBase con `hotel_reservation_events_03`.
- `/etl-status` mostrando configuración GA03.
- Parquet `data/processed/reservas_hoteleras_03.parquet`.
- Reportes GA03 en `data/reports`.
- Diagrama de base de datos renderizado.
- Diagrama de casos de uso renderizado.
- Dashboard, CRUD, auditoría y calidad.

## Resultados obtenidos

Agregar únicamente resultados con evidencia real disponible. No inventar ejecuciones ni estados.

## Conclusiones

GA03 deja alineada la documentación SDD con una visión de 32 casos de uso, manteniendo el alcance real del núcleo implementado y separando claramente lo planificado para fases posteriores.
