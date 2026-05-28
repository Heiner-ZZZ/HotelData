# TA 02 - Historias de usuario

1. Como operador de datos, quiero ejecutar un DAG de reservas para cargar PocketBase en MongoDB con trazabilidad completa.
   - Criterios: usa PythonOperator, genera Parquet, registra `execution_id`.

2. Como analista comercial, quiero ver reservas brutas en USD para evaluar desempeno de ventas.
   - Criterios: `reservas_brutas_usd` existe en el hecho y se calcula con regla documentada.

3. Como revenue manager, quiero clasificar precios para comparar segmentos tarifarios.
   - Criterios: cada hecho valido incluye `price_category_id` cuando el precio existe.

4. Como analista de demanda, quiero analizar anticipacion de reserva para planificar ocupacion.
   - Criterios: se crea `booking_window_category_id` desde `srch_booking_window`.

5. Como responsable de gobierno, quiero CRUD de dimensiones para corregir datos maestros.
   - Criterios: todas las dimensiones tienen endpoints CRUD paginados.

6. Como auditor, quiero ver ejecuciones y calidad para explicar errores de carga.
   - Criterios: existen `etl_executions`, `data_quality_reports` y `rejected_records`.

7. Como usuario de negocio, quiero consultar registros por paginas para no saturar la web.
   - Criterios: los listados limitan `page_size` a 100 como maximo.
