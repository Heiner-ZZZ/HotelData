# TA 02 - Empresa

## Empresa ficticia

HotelData Hub Analytics es una unidad empresarial dedicada a integrar, gobernar y analizar datos de busquedas y reservas hoteleras para equipos de revenue management, operaciones digitales y direccion comercial.

## Mision

Convertir datos dispersos de reservas hoteleras en informacion confiable, auditable y accionable para mejorar conversion, ingresos y eficiencia operativa.

## Vision

Ser la plataforma interna de referencia para analitica hotelera, integrando fuentes operacionales, modelos dimensionales y servicios web de consulta en una arquitectura gobernada sobre MongoDB.

## Objetivos

| Nivel | Objetivo | Indicador |
| --- | --- | --- |
| Estrategico | Incrementar la capacidad de decision basada en datos de reservas | Dashboard con KPIs de reservas, precio e ingresos |
| Estrategico | Consolidar una fuente analitica gobernada en MongoDB | Modelo dimensional cargado y auditado |
| Tactico | Automatizar extraccion PocketBase, Parquet y carga MongoDB | DAG TA 02 ejecutable de punta a punta |
| Tactico | Mejorar trazabilidad de calidad y rechazos | `rejected_records`, `etl_executions`, `data_quality_reports` |
| Operativo | Consultar hechos y dimensiones sin cargar millones de registros | CRUD paginado |
| Operativo | Asegurar busquedas rapidas por llaves de negocio | Indices MongoDB |

## Areas usuarias

- Direccion comercial: analiza reservas brutas, conversion y promociones.
- Revenue management: revisa precio, anticipacion y duracion de estancia.
- Operaciones digitales: audita ejecuciones ETL y calidad de datos.
- Gobierno de datos: controla dimensiones, rechazos e historias de carga.
