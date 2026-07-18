# Diseño de base de datos GA03

## Contexto técnico

GA03 extiende HotelData Analytics como avance funcional aproximado del 25% del sistema completo. No crea una aplicación separada ni reemplaza TAF01/TA02. La base analítica compartida sigue siendo `hoteldata_hub`.

Configuración real de GA03:

- `TASK_NUMBER=03`
- `TARGET_RECORDS=300000`
- PocketBase collection: `hotel_reservation_events_03`
- MongoDB database: `hoteldata_hub`
- Fact principal: `fact_hotel_reservations`
- DAG Airflow: `hoteldata_reservas_03_pipeline`
- JSONL: `data/staging/reservas_hoteleras_03_extract.jsonl`
- Parquet: `data/processed/reservas_hoteleras_03.parquet`
- Reportes:
  - `data/reports/reporte_ejecucion_reservas_03.json`
  - `data/reports/reporte_calidad_reservas_03.json`
  - `data/reports/validacion_dataset_reservas_03.json`

El flujo CSV -> PocketBase es preparación administrativa de la fuente operacional. El ETL principal inicia desde PocketBase y sigue el flujo PocketBase -> JSONL -> Parquet -> MongoDB.

## Modelo actual de base de datos

### Hechos

| Colección | Tipo | Propósito |
| --- | --- | --- |
| `fact_hotel_reservations` | Hecho principal | Eventos de búsqueda, click, precio y reserva usados para analítica de reservas hoteleras. |
| `fact_hotel_events` | Hecho histórico | Hechos de eventos hoteleros de entregas previas, conservado como parte de la base actual. |

### Dimensiones activas

| Colección | Propósito |
| --- | --- |
| `dim_hotels` | Describe hoteles por `prop_id`. |
| `dim_destinations` | Describe destinos por `srch_destination_id`. |
| `dim_visitor_countries` | Segmenta por país de origen del visitante. |
| `dim_sites` | Segmenta por sitio o canal de origen. |
| `dim_dates` | Permite análisis temporal por `date_key`. |
| `dim_promotions` | Clasifica eventos con o sin promoción. |
| `dim_click_status` | Clasifica eventos con o sin click. |
| `dim_reservation_status` | Clasifica eventos con o sin reserva. |
| `dim_occupancy_profile` | Define perfiles por adultos, niños y habitaciones. |
| `dim_stay_length_category` | Segmenta duración de estancia. |
| `dim_booking_window_category` | Segmenta anticipación de reserva. |
| `dim_price_category` | Segmenta rangos de precio. |

### Colecciones de control

| Colección | Propósito |
| --- | --- |
| `etl_executions` | Bitácora de ejecuciones ETL. |
| `data_quality_reports` | Reportes de calidad por ejecución. |
| `rejected_records` | Registros rechazados y motivo de rechazo. |

### Colecciones documentales y operativas

| Colección | Propósito |
| --- | --- |
| `hotels` | Maestra operativa de hoteles. |
| `locations` | Ubicación y datos geográficos por hotel. |
| `contacts` | Teléfonos y datos de contacto. |
| `websites` | URLs asociadas a hoteles. |
| `facilities` | Instalaciones o servicios. |
| `attractions` | Atracciones cercanas. |
| `hotel_quality` | Calidad de datos de hotel. |
| `dataset_container` | Metadatos del dataset procesado. |
| `system_catalogs` | Catálogos de apoyo del sistema. |
| `search_logs` | Bitácora de búsquedas. |

### Colecciones legadas

| Colección | Estado |
| --- | --- |
| `dim_countries` | Legada, sin uso principal en GA03. |
| `dim_date` | Legada, reemplazada por `dim_dates`. |

## Relaciones lógicas

`fact_hotel_reservations` se relaciona lógicamente con las dimensiones mediante llaves como `prop_id`, `srch_destination_id`, `visitor_location_country_id`, `site_id`, `date_key`, `occupancy_profile_id`, `stay_length_category_id`, `booking_window_category_id` y `price_category_id`.

Las colecciones de control se relacionan por `execution_id`, permitiendo trazabilidad entre ejecución, calidad y registros rechazados.

## Modelo futuro de seguridad y administración de usuarios

GA03 no implementa login real, roles reales ni autorización por permisos. Para fases posteriores se proyecta un modelo de seguridad y administración de usuarios con las siguientes colecciones planificadas:

| Colección planificada | Propósito futuro | Estado |
| --- | --- | --- |
| `users` | Usuarios con credenciales y perfil. | Planificado, no implementado en GA03. |
| `roles` | Roles como Administrador, Usuario operativo o Auditor. | Planificado, no implementado en GA03. |
| `permissions` | Permisos por módulo y acción. | Planificado, no implementado en GA03. |
| `user_sessions` | Sesiones activas e históricas. | Planificado, no implementado en GA03. |
| `user_activity_logs` | Auditoría de acciones de usuarios. | Planificado, no implementado en GA03. |
| `uploaded_files` | Trazabilidad de archivos cargados. | Planificado, no implementado en GA03. |
| `task_configurations` | Configuración por tarea o fase. | Planificado, no implementado en GA03. |
| `notification_events` | Notificaciones de procesos completados, fallidos o pendientes. | Planificado, no implementado en GA03. |

Estas colecciones permitirán login, control de roles, auditoría de acciones, trazabilidad de cargas y notificaciones. No forman parte del alcance implementado de GA03 y no deben interpretarse como tablas reales existentes.

## Flujo técnico de datos

```text
CSV limpio
-> PocketBase hotel_reservation_events_03
-> data/staging/reservas_hoteleras_03_extract.jsonl
-> data/processed/reservas_hoteleras_03.parquet
-> dimensiones + fact_hotel_reservations
-> MongoDB hoteldata_hub
-> reportes de ejecución, calidad y validación
```

## Interfaz /etl-status

La interfaz `/etl-status` se documenta como centro operativo de GA03:

- GA03 aparece primero.
- TA02 queda como evidencia histórica.
- TAF01 queda como flujo histórico.
- Se separó preparación administrativa de fuente y ETL principal.
- Se agregaron validaciones de PocketBase, MongoDB, colección, conteo objetivo y reportes.
- Se evita mostrar JSON gigante por defecto.
- Se puede preparar fuente, validar dataset y ejecutar pipeline desde la sección ETL.

## Mejoras implementadas en la interfaz ETL

La sección ETL ya existía en la aplicación como ruta `GET /etl-status`. Para la tarea vigente se reutilizó y amplió esa sección; no se creó una aplicación ni un panel ETL separado.

Rutas conservadas y ampliadas:

- `GET /etl-status`
- `POST /etl-status/upload`
- `POST /etl-status/seed`
- `POST /etl-status/run`
- `POST /etl-status/ga03/validate`
- `POST /etl-status/ga03/seed`
- `POST /etl-status/ga03/run`

Archivos relacionados:

- `src/app/routes/etl_status.py`
- `src/app/services/etl_status_service.py`
- `src/app/templates/etl_status.html`
- `src/app/templates/base.html`
- `src/app/static/css/styles.css`

La interfaz fue reorganizada para presentar la tarea actual como primer bloque visible, dejando TAF01 como flujo histórico colapsado y TA02 como evidencia histórica colapsada. Los detalles técnicos, trazas y JSON completos se muestran bajo demanda mediante desplegables o ayudas visuales, evitando saturar la pantalla principal.

## Separación funcional del flujo

La interfaz diferencia dos responsabilidades:

1. Preparación administrativa de fuente:
   - Flujo: CSV -> PocketBase.
   - Objetivo: preparar la colección operacional de la tarea vigente.
   - En GA03 la colección es `hotel_reservation_events_03`.
   - No carga directo a MongoDB.

2. ETL principal:
   - Flujo: PocketBase -> JSONL -> Parquet -> MongoDB.
   - Objetivo: transformar la fuente operacional en modelo analítico.
   - No debe ejecutarse si PocketBase no contiene `TARGET_RECORDS`.

Esta separación evita confundir la carga semilla administrativa con el pipeline analítico principal.

## Lógica funcional agregada al panel ETL

La interfaz permite visualizar y operar:

- `TASK_NUMBER`.
- `TARGET_RECORDS`.
- Colección PocketBase de la tarea vigente.
- Estado de PocketBase.
- Estado de MongoDB.
- Conteo actual de la colección operacional.
- Conteo de `fact_hotel_reservations`.
- Estado de reportes de la tarea.
- Preparación de fuente desde CSV.
- Validación de dataset.
- Ejecución del pipeline.
- Mensajes de éxito/error.
- Detalle técnico bajo demanda.

Aunque la documentación usa GA03 como configuración actual, el enfoque queda preparado para tareas futuras con otra colección y otra cantidad objetivo.

## Validaciones y bloqueos agregados

La sección ETL documentada controla los siguientes casos:

- Si PocketBase no está disponible, muestra "No disponible".
- Si MongoDB no está disponible, muestra "No disponible".
- Si la colección de la tarea no existe, muestra un mensaje limpio sin traza gigante.
- Si la colección tiene 0 registros, bloquea validación y pipeline.
- Si la colección tiene menos que `TARGET_RECORDS`, indica fuente incompleta.
- Si la colección tiene exactamente `TARGET_RECORDS`, marca la fuente como lista.
- Si la colección tiene más que `TARGET_RECORDS`, bloquea por seguridad.
- Si el CSV fuente no existe, muestra advertencia.
- Si un script falla, muestra resumen de `stdout`/`stderr` y permite ver detalle técnico desplegable.
- Se evita que el usuario confunda preparación de fuente con ETL principal.

## Mejoras de usabilidad

Las mejoras visuales implementadas incluyen:

- Tarjetas de estado.
- Checklist por paso.
- Secciones colapsables.
- Mensajes claros para errores 404 de PocketBase.
- Advertencias antes de acciones sensibles.
- Orden lógico de operación:
  1. Preparar fuente.
  2. Validar dataset.
  3. Ejecutar pipeline.
- Integración con evidencias para presentación y PDF.

## Evidencia sugerida para el PDF

- `/etl-status` mostrando la tarea vigente como bloque principal.
- `/etl-status` mostrando PocketBase disponible.
- `/etl-status` mostrando MongoDB disponible.
- `/etl-status` mostrando `TARGET_RECORDS=300000`.
- `/etl-status` mostrando `hotel_reservation_events_03`.
- `/etl-status` mostrando validación OK.
- `/etl-status` mostrando reportes.
- TAF01 y TA02 colapsados como históricos.
- Mensaje de error controlado cuando la fuente no está lista.
- Resultado del pipeline o auditoría.

## Diagrama lógico

El código PlantUML completo se mantiene en `docs/ga03/plantuml_03.md`.
