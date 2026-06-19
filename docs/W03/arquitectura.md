# Arquitectura

Airflow orquesta funciones Python del paquete `src.etl`. El ETL escribe staging, processed y reports en disco, valida claves maestras y carga hechos ya transformados en MongoDB mediante `src.database`.

La aplicacion FastAPI en `src.app` consulta MongoDB y gestiona `system_catalogs`, pero no participa en el DAG ni en las transformaciones.
