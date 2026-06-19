# TA 02 - Casos de uso

## CU01 - Ejecutar ETL de reservas

Actor: Operador de datos.

Condiciones de aceptacion:
- El flujo extrae desde PocketBase.
- Se genera Parquet antes de MongoDB.
- Se cargan hecho, dimensiones, rechazos, calidad y ejecucion.

## CU02 - Consultar dashboard de reservas

Actor: Analista comercial.

Condiciones de aceptacion:
- El dashboard muestra conteos, ingresos, reservas y calidad.
- Los datos provienen de MongoDB.
- La consulta no carga millones de registros en pantalla.

## CU03 - Administrar dimension de hoteles

Actor: Gobierno de datos.

Condiciones de aceptacion:
- El usuario lista hoteles con paginacion.
- Puede crear, consultar, actualizar y eliminar documentos autorizados.
- Los cambios quedan en MongoDB.

## CU04 - Auditar ejecuciones ETL

Actor: Operaciones digitales.

Condiciones de aceptacion:
- La web muestra `etl_executions`.
- Cada ejecucion incluye estado, fecha, base y reportes.
- El usuario puede revisar calidad y registros rechazados.

## CU05 - Analizar conversion por promocion

Actor: Revenue manager.

Condiciones de aceptacion:
- El usuario consulta hechos por `promotion_flag` y `reserva_bool`.
- El sistema usa indices MongoDB.
- Las respuestas estan paginadas.
