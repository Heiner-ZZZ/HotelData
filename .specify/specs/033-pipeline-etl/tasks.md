# Tareas: Pipeline ETL

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: DAG

- [ ] T001 Verificar DAG `hoteldata_ga03_etl` con 14 tareas en Airflow
- [ ] T002 Verificar que todas las tareas usan PythonOperator
- [ ] T003 Verificar chunk size 50k filas y batch insert 5k documentos

## Fase 2: Calidad

- [ ] T004 Verificar que cada ejecución genera reporte en `data/reports/` + MongoDB
- [ ] T005 Verificar que registros rechazados van a `rejected_records` con razón

## Fase 3: Validación

- [ ] T006 Ejecutar DAG de prueba y verificar reporte de calidad
- [ ] T007 Verificar `test_dag_boundaries.py` (sin imports de src.app)
