# Tasks TAF01 - HotelData Hub Analytics

## Estado actual

TAF01 esta implementada y queda como base historica del proyecto. Las tareas se documentan como estado real, no como promesa futura.

## Fase 1 - Configuracion
- [x] Crear configuracion del proyecto.
- [x] Crear `config/settings.py`.
- [x] Crear `requirements.txt`.
- [x] Probar conexion con MongoDB.

## Fase 2 - ETL local
- [x] Crear `schema.py` con columnas esperadas.
- [x] Crear modulos de extraccion, validacion, transformacion, calidad, carga y reportes en `src/etl`.
- [x] Crear scripts de carga local y validacion.
- [x] Separar registros validos y rechazados.
- [x] Registrar reportes de calidad y ejecuciones.

## Fase 3 - Airflow
- [x] Crear DAG `hoteldata_taf01_etl_pipeline`.
- [x] Validar que el DAG no importe `src.app`.
- [x] Usar `PythonOperator`.
- [x] No usar `BashOperator` para mover datos.
- [x] Ejecutar tareas ETL desde funciones Python.

## Fase 4 - Web
- [x] Crear app FastAPI.
- [x] Crear layout base.
- [x] Crear dashboard.
- [x] Crear busqueda o consulta paginada de registros.
- [x] Crear vista de calidad de datos.
- [x] Crear vista de colecciones.
- [x] Crear vista de empresa.
- [x] Crear vista de problemas.
- [x] Crear vista de auditoria.
- [x] Crear CRUD basico para `system_catalogs`.

## Fase 5 - Documentacion
- [x] Crear documentacion de empresa, objetivos, problemas, arquitectura, colecciones, roles y guion.
- [x] Mantener TAF01 como base historica.
- [x] Documentar que TA02 extiende el proyecto sin crear un proyecto independiente.

## Reglas SDD para tareas posteriores

Toda tarea posterior debe declarar:
- Que conserva.
- Que agrega.
- Que modifica.
- Que reemplaza.
- Que elimina.
- Que archivo, ruta, modulo o coleccion afecta.
- Que evidencia demostrara cumplimiento.
