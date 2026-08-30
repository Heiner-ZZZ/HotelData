# Módulo Agrupado: Inteligencia de Negocios y Arquitectura ETL (Arquitectura Medallón)

**Trazabilidad Jerárquica Obligatoria:**
* **Nivel Empresarial**: Estratégico y Táctico (Objetivo OE4)
* **Departamento**: Administración de Datos y Revenue Management
* **Paquete UML**: Paquete 6 - Pipeline ETL
* **Casos de Uso Consolidados**: CU-O26 (Reportes Revenue), CU-O27 (Calidad de Datos), CU-T12 (Ejecución ETL).

## 1. Objetivo General
Consolidar el ecosistema de datos del hub hotelero mediante un pipeline de extracción, transformación y carga (ETL) que alimente modelos de estrella sin penalizar las transacciones diarias.

## 2. Especificación Técnica Consolidada (Reemplaza specs 033, 038, 039, 040, 041)
- **Modo Incremental (GA03_INCREMENTAL_MODE)**: El orquestador Airflow ejecutará extracciones parciales basadas en last_extracted_at para minimizar el impacto computacional, logrando una sincronización casi en tiempo real (consistencia eventual).
- **Ingesta**: Extracción directa desde colecciones MongoDB y PocketBase.
- **Dimensiones y Hechos**: Generación automatizada de 12 dimensiones y tablas de hechos (act_reservations), garantizando operaciones Upsert idempotentes.
- **Modelo Estrella**: La estructura final habilitará dashboards OLAP, series temporales de ocupación y proyecciones predictivas de demanda (BI/ML).
