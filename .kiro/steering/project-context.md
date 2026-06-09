# Contexto del proyecto

El proyecto se llama HotelData Hub Analytics.

HotelData Hub Analytics es una plataforma empresarial de analitica de reservas hoteleras. Integra, transforma, audita y consulta eventos de busqueda, click, precio, promocion y reserva para apoyar decisiones comerciales, operativas y de gobierno de datos.

La aplicacion no es una pasarela real de pagos ni un motor transaccional para confirmar reservas reales. Es una plataforma analitica y administrativa que trabaja con eventos de busqueda/reserva ya existentes.

Materia: Construccion de Software.
Entregas implementadas: TAF01 y TA02.
Base de datos final: MongoDB.
Base MongoDB real: `hoteldata_hub`.
Orquestador: Apache Airflow.
Lenguaje obligatorio para movimiento de datos: Python.
Web: FastAPI + Jinja2.

## Estado real consolidado TAF01 + TA02

TAF01 es la base historica del proyecto. Conserva el flujo ETL desde CSV hacia MongoDB, el DAG `hoteldata_taf01_etl_pipeline`, la separacion entre Airflow, ETL, base de datos y web, y las colecciones de control `etl_executions`, `data_quality_reports` y `rejected_records`.

TA02 no crea un proyecto independiente. Extiende HotelData Hub Analytics con un flujo de reservas desde PocketBase, Parquet obligatorio como formato intermedio, modelo dimensional de reservas, DAG Airflow TA02, CRUD para hecho/dimensiones, reportes de calidad y evidencia de ejecucion.

El foco funcional evoluciona desde catalogo/calidad hotelera TAF01 hacia analitica de reservas hoteleras TA02. Esto no invalida TAF01; la deja como linea base historica y agrega una nueva capacidad analitica sobre reservas.

## Evidencia real TA02

- Fuente: PocketBase.
- Coleccion PocketBase: `hotel_reservation_events__2`.
- Flujo: `PocketBase -> JSONL -> Parquet -> Dimensiones + Hecho -> MongoDB`.
- JSONL: `data/staging/pocketbase_full_extract.jsonl`.
- Parquet: `data/processed/hotel_reservations_full.parquet`.
- Hecho procesado: `data/processed/fact_hotel_reservations_ta02.jsonl`.
- Rechazados procesados: `data/processed/rejected_records_ta02.jsonl`.
- Dimensiones procesadas: `data/processed/ta02_dimensions/*.jsonl`.
- DAG: `hoteldata_ta02_reservations_pipeline`.
- Hecho MongoDB: `fact_hotel_reservations`.
- Registros extraidos/cargados: `201000`.
- Registros rechazados: `0`.
- Web TA02: `/ta02`.
- CRUD visual: `/ta02/crud`.
- API CRUD: `/api/{collection_name}`.

## Reglas para futuras tareas

Toda nueva tarea SDD debe declarar que conserva, agrega, modifica, reemplaza o elimina. Tambien debe indicar archivos, rutas, colecciones o modulos afectados y la evidencia que demostrara cumplimiento.

```md
## Relacion con entregas anteriores

Esta tarea no crea un proyecto independiente. Extiende el proyecto HotelData Hub Analytics.

### Elementos que se conservan
- ...

### Elementos que se agregan
- ...

### Elementos que se modifican
- ...

### Elementos que se reemplazan
- ...

### Elementos que se eliminan
- ...

### Matriz de impacto

| ID | Elemento afectado | Tarea origen | Tipo de cambio | Archivo/ruta/coleccion | Estado anterior | Estado nuevo | Criterio de aceptacion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IMP-001 | ... | ... | ... | ... | ... | ... | ... |
```
