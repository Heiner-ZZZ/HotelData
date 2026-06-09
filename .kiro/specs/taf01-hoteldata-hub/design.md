# Diseno TAF01 - HotelData Hub Analytics

## Estado implementado TAF01

TAF01 implementa la primera version de HotelData Hub Analytics. Su objetivo es cargar, validar, transformar y consultar informacion hotelera desde CSV hacia MongoDB usando Python, Airflow y FastAPI.

TAF01 queda como base historica del proyecto. TA02 extiende esta arquitectura para reservas hoteleras, pero no invalida el diseno TAF01.

## Capas del sistema TAF01

1. Capa de orquestacion:
   - Apache Airflow.
   - DAG `hoteldata_taf01_etl_pipeline`.
   - Usa `PythonOperator`.
   - No importa `src.app`.

2. Capa ETL:
   - Modulos Python en `src/etl`.
   - Extrae, valida, transforma y prepara datos.

3. Capa de datos:
   - MongoDB.
   - Base real: `hoteldata_hub`.
   - Colecciones documentales, auditoria y calidad.

4. Capa web:
   - FastAPI + Jinja2.
   - Consulta MongoDB y muestra dashboard, registros, calidad, colecciones, catalogos, empresa, problemas y auditoria.

## Flujo ETL TAF01

```text
CSV -> Transformacion Python -> MongoDB
```

Extract:
- Leer `data/raw/hotels.csv`.

Transform:
- Validar columnas necesarias.
- Validar minimo de registros.
- Normalizar tipos de datos.
- Crear campos derivados cuando corresponda.
- Validar claves maestras.
- Separar registros validos e invalidos.

Load:
- Insertar documentos validos en MongoDB.
- Insertar documentos invalidos en `rejected_records`.
- Crear indices.
- Guardar `data_quality_reports`.
- Guardar `etl_executions`.

## Matriz de impacto entre tareas

| ID | Elemento afectado | Tarea origen | Tipo de cambio | Estado anterior | Estado actual | Ruta/coleccion real | Accion SDD | Evidencia |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IMP-TAF01-001 | Nombre del proyecto | TAF01 | Modificar | HotelData Hub | HotelData Hub Analytics | `.kiro/steering/project-context.md` | Alinear nombre academico completo | Steering actualizado |
| IMP-TAF01-002 | Base MongoDB | TAF01 | Conservar | `hoteldata_hub` | `hoteldata_hub` | MongoDB | Mantener como base final | `config/settings.py` |
| IMP-TAF01-003 | Flujo CSV | TAF01 | Conservar | CSV hacia MongoDB | Base historica vigente | `data/raw/hotels.csv` | Documentar como TAF01 | DAG TAF01 |
| IMP-TAF01-004 | DAG TAF01 | TAF01 | Conservar | `hoteldata_taf01_etl_pipeline` | Implementado | `dags/hoteldata_taf01_etl_dag.py` | Mantener | DAG existente |
| IMP-TAF01-005 | Foco funcional | TA02 | Ampliar | Catalogo/calidad hotelera | Analitica de reservas sobre base TAF01 | Specs TAF01/TA02 | Explicar evolucion | Specs actualizados |

## Relacion con TA02

TA02 agrega un flujo nuevo:

```text
PocketBase -> JSONL -> Parquet -> Dimensiones + Hecho -> MongoDB
```

El hecho principal TA02 es `fact_hotel_reservations`. TA02 usa el DAG `hoteldata_ta02_reservations_pipeline`, la ruta web `/ta02`, el CRUD visual `/ta02/crud` y la API `/api/{collection_name}`.
