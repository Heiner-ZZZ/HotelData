# Objetivos

## Objetivos estrategicos

- Centralizar informacion hotelera de alto volumen.
- Mejorar la confiabilidad del catalogo hotelero.
- Separar claramente ETL, almacenamiento y consulta web.

## Objetivos tacticos

- Construir un pipeline ETL verificable con Airflow.
- Transformar el dataset con Python antes de cargar MongoDB.
- Crear reportes de calidad por ejecucion.

## Objetivos operacionales

- Leer `data/raw/hotels.csv` por chunks.
- Validar 16 columnas obligatorias.
- Eliminar duplicados por `HotelCode`.
- Cargar colecciones derivadas con PyMongo batch insert.
- Consultar dashboard, registros, calidad, problemas y catalogos desde FastAPI.
