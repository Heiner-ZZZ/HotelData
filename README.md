# HotelData TAF 01

Proyecto ETL estricto para cargar datos hoteleros desde CSV hacia MongoDB y consultar resultados desde una web FastAPI.

## Restriccion principal

El DAG de Airflow no importa `src/app`, templates, static, HTML, CSS ni JS. Solo orquesta funciones de `src/etl`, `src/database` y `config`, usando `PythonOperator`.

## Ejecutar localmente

```powershell
pip install -r requirements.txt
python -m pytest -q
```

Coloca el dataset real en `data/raw/hotels.csv` con las columnas definidas en `src/etl/schema.py`.

## Airflow

El DAG esta en `dags/hoteldata_taf01_etl_dag.py` y ejecuta:

1. `validate_environment`
2. `extract_csv`
3. `validate_schema`
4. `transform_clean_dataset`
5. `transform_dataset_container`
6. `transform_business_collections`
7. `generate_quality_report`
8. `load_to_mongodb`
9. `create_indexes`
10. `save_execution_report`

## Web

```powershell
uvicorn src.app.main:app --reload
```

La web solo consulta MongoDB y gestiona CRUD de catalogos maestros.
