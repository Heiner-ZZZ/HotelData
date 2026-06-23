# Especificacion: Pipeline ETL

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T12 (Ejecutar y validar pipeline Airflow sobre 600000 registros), CU-E07 (Evaluar calidad de datos)

## 1. Objetivo

Ejecutar el pipeline ETL orquestado por Airflow que extrae datos desde PocketBase, transforma a dimensiones y hechos, y carga en MongoDB.

## 2. Contexto

Pipeline GA03 procesa ~600k registros. Usa Airflow con PythonOperator. 14 tareas, chunk 50k, batch 5k.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Operador de datos | Ejecuta y monitorea pipeline |
| Auditor de Datos | Revisa calidad post-ejecucion |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Airflow debe ejecutar DAG hoteldata_ga03_etl con 14 tareas | Alta |
| RF-002 | El DAG debe usar solo PythonOperator | Alta |
| RF-003 | El pipeline debe extraer datos desde PocketBase | Alta |
| RF-004 | El pipeline debe transformar a dimensiones (upsert) y hechos (batch insert) | Alta |
| RF-005 | El pipeline debe generar reporte de calidad por ejecucion | Alta |
| RF-006 | El pipeline debe registrar rechazos en rejected_records | Alta |

## 5. Reglas de negocio

- Solo PythonOperator (no BashOperator)
- Chunk size: 50,000 filas, batch insert: 5,000 documentos
- Dimensiones primero (upsert), hechos despues (batch insert)

## 6. Flujo del DAG

extract_from_pocketbase validate_schema convert_to_jsonl convert_to_parquet build_dim_* (8 tareas) build_fact load_to_mongodb generate_quality_report

## 7. Escenarios

### Escenario 1: Ejecutar pipeline exitosamente
```gherkin
Dado que Airflow inicia el DAG hoteldata_ga03_etl
Cuando se ejecutan las 14 tareas
Entonces los datos se cargan en MongoDB
Y se genera el reporte de calidad
```

## 8. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | DAG se ejecuta con 14 tareas PythonOperator |
| CA-002 | Datos se cargan en MongoDB correctamente |
| CA-003 | Reporte de calidad se genera por ejecucion |
| CA-004 | test_dag_boundaries.py pasa |


## 9. Dependencias

- DAG: server/dags/hoteldata_ga03_etl.py
- Modulos: src/etl/tasks.py, ta02_dimensions.py, ta02_fact.py, transform_clean.py, validate.py
- PocketBase (fuente), MongoDB (destino)

## 10. Fuera de alcance

- Streaming en tiempo real (solo batch)
