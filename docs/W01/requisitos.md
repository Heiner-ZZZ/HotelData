# Requisitos

## Funcionales

- Validar dataset y columnas esperadas.
- Ejecutar ETL desde Python.
- Transformar antes de cargar MongoDB.
- Crear colecciones documentales.
- Registrar ejecuciones ETL.
- Reportar calidad de datos.
- Mostrar dashboard y busqueda de hoteles.
- Mostrar documentacion empresarial.
- Permitir CRUD de `system_catalogs` para admin.
- Mostrar auditoria de ejecuciones y busquedas.

## No funcionales

- Mantener separacion entre Airflow, ETL, base de datos y web.
- Procesar datos grandes con chunks o batches.
- Usar variables de entorno.
- Evitar que Airflow importe `src/app`.
- No borrar `system_catalogs` ni `search_logs` durante el ETL.
