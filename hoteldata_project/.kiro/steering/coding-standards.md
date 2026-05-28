# Estandares de codificacion

- Usar Python claro, modular y mantenible.
- Usar nombres descriptivos en ingles para archivos, funciones y variables.
- Separar extraccion, validacion, transformacion, carga, calidad y reportes.
- Usar variables de entorno desde `.env`.
- Usar logs claros.
- Usar batch insert para MongoDB.
- Usar upsert para dimensiones o colecciones maestras cuando corresponda.
- Evitar cargar todo el dataset completo en memoria cuando el volumen lo requiera.
- Usar chunks o batches para procesar datasets grandes.
- Escribir pruebas basicas para validacion, transformacion, calidad y reglas del DAG.
- No borrar `system_catalogs` durante el ETL.
- No borrar `search_logs` durante el ETL.
- Mantener historial en `etl_executions`.
- Mantener reportes en `data_quality_reports`.

## Reglas TA02

- El CRUD TA02 debe paginar resultados y no devolver mas de 25 documentos por pagina.
- Las cargas masivas de hechos deben usar batch insert o upsert controlado.
- Las dimensiones TA02 deben cargarse con upsert para evitar duplicacion innecesaria.
- Los scripts de validacion no deben borrar datos reales; si crean datos temporales, deben eliminarlos al finalizar.
- Todo movimiento de datos TA02 debe permanecer en Python.
- Airflow TA02 no debe usar `BashOperator`.
- Airflow TA02 no debe importar `src.app`.
