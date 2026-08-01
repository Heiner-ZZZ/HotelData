# DAGs históricos no montados

Estos archivos se conservan como referencia histórica de TA02, TAF01 y una
versión anterior de GA03. Airflow **no** los carga porque el Compose monta
únicamente `server/dags` en `/opt/airflow/dags`.

El único DAG activo actualmente es:

```text
server/dags/hoteldata_ga03_etl.py
```

No ejecutar ni mover un DAG de esta carpeta a `server/dags` sin revisar su
contrato, imports, destino de datos y compatibilidad con el pipeline vigente.
