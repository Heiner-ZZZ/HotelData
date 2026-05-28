# Requisitos TAF01 - HotelData Hub Analytics

## Estado real consolidado TAF01 + TA02

TAF01 es la base historica implementada de HotelData Hub Analytics. Define la arquitectura inicial, el ETL desde CSV hacia MongoDB, la separacion entre Airflow, ETL, base de datos y web, y las colecciones de control operativo.

TA02 no crea un proyecto independiente. Extiende la base TAF01 con analitica de reservas desde PocketBase, Parquet obligatorio, modelo dimensional de reservas, DAG propio y CRUD de hecho/dimensiones.

El foco funcional actual del proyecto evoluciona hacia reservas hoteleras, pero TAF01 se conserva como linea base historica y tecnica.

## Requisitos funcionales TAF01 implementados

### RF01 - Validar dataset
El sistema valida que el dataset CSV tenga mas de 100000 registros y mas de 12 columnas.

### RF02 - Validar columnas esperadas
El sistema valida que el CSV contenga columnas transaccionales requeridas como `srch_id`, `date_time`, `prop_id`, `srch_destination_id`, `visitor_location_country_id` y `price_usd`.

### RF03 - Ejecutar ETL con Python
El sistema ejecuta un proceso ETL desde Python. Airflow solo orquesta funciones Python.

### RF04 - Transformar antes de cargar
El sistema limpia, valida, normaliza y prepara los datos antes de cargarlos a MongoDB.

### RF05 - Crear colecciones MongoDB
El sistema usa MongoDB como destino final en la base `hoteldata_hub`. TAF01 conserva colecciones de hecho, dimensiones, rechazos, calidad, auditoria y catalogos administrativos.

### RF06 - Registrar ejecuciones
El sistema registra ejecuciones ETL en `etl_executions`.

### RF07 - Reportar calidad de datos
El sistema genera reportes de calidad en `data_quality_reports`.

### RF08 - Sembrar colecciones maestras
El sistema permite carga inicial manual e idempotente de colecciones maestras requeridas para TAF01.

### RF09 - Validar claves maestras
El sistema rechaza hechos cuyas claves no existan en colecciones maestras cuando aplica el flujo TAF01.

### RF10 - Mostrar web empresarial
La web muestra dashboard, registros, calidad, colecciones, empresa, problemas, auditoria y catalogos administrativos.

## Requisitos no funcionales

### RNF01 - Movimiento de datos con Python
Todo movimiento de datos debe realizarse desde Python.

### RNF02 - Separacion de responsabilidades
Airflow no debe importar `src.app`, templates, static, HTML, CSS ni JS.

### RNF03 - Airflow sin BashOperator para datos
Los DAGs no deben usar `BashOperator` para mover datos.

### RNF04 - Rendimiento
El sistema debe procesar datasets grandes usando chunks o batches cuando corresponda.

### RNF05 - Configuracion
Credenciales y rutas deben manejarse mediante variables de entorno.

### RNF06 - Mantenibilidad
El proyecto debe estar separado en modulos de ETL, base de datos, app web, docs, scripts y tests.

## Relacion con TA02

TA02 conserva la arquitectura TAF01 y agrega:
- Fuente PocketBase.
- Parquet como formato intermedio obligatorio.
- Hecho `fact_hotel_reservations`.
- 12 dimensiones de reservas.
- DAG `hoteldata_ta02_reservations_pipeline`.
- CRUD TA02 en `/ta02` y `/ta02/crud`.
- Evidencia de `201000` registros cargados y `0` rechazados.
