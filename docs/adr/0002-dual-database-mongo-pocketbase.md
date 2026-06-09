# ADR-0002: Dual Database — MongoDB + PocketBase

## Status
Accepted

## Date
2026-06-06

## Context
- El backend principal usa **MongoDB 7+** como store de documentos para
  ETL (`fact_hotel_reservations`, `dim_*`), gestión (`users`, `roles`),
  y datos de partner (`hotel_content_pages`, `rate_plans`, etc.).
- El proyecto también corre **PocketBase** (`ghcr.io/muchobien/pocketbase`)
  en `docker-compose.yml` como servicio adicional.
- PocketBase se usa para una colección específica: `hotel_reservation_events_03`
  (ver `POCKETBASE_COLLECTION_03` en `docker-compose.yml:66`).
- Hay escritura dual: el mismo evento se persiste en Mongo (`fact_hotel_*`)
  y en PocketBase (`hotel_reservation_events_03`).

## Decision
Mantenemos **dos bases de datos** con responsabilidades distintas y
escritura dual controlada por un único DAG de Airflow:

| Database | Responsabilidad | Por qué |
|---|---|---|
| **MongoDB** | Source of truth para todos los dominios. ETL, consultas analíticas, gestión, partner. | Modelo de documentos flexible, agregaciones (`$group`, `$facet`) que necesitamos para revenue/dashboard, transaccionalidad multi-doc cuando se requiera. |
| **PocketBase** | Subset de eventos de reserva (ga03), expuesto como API REST con auth built-in para un consumidor externo específico. | Su API REST con JWT y reglas por-collection es lo que necesita ese consumidor, sin tener que mantener endpoints custom en FastAPI. |

El DAG `dags/hoteldata_reservas_03_pipeline.py` es el único punto que
escribe en PocketBase. FastAPI (`src/app/`) **no** escribe en PocketBase.

## Alternatives Considered

### Solo MongoDB
- **Pros**: una sola BD, una sola fuente de verdad, sin drift.
- **Cons**: el consumidor externo tendría que autenticarse contra nuestro
  FastAPI, mantener credenciales de sesión, y rate-limiting. PocketBase
  da eso gratis.
- **Why not**: reescribir el consumidor no estaba en el scope y PocketBase
  ya estaba operativo.

### Solo PocketBase
- **Pros**: una sola BD.
- **Cons**: PocketBase no tiene las agregaciones que necesitamos
  (`$group` con `$cond`, `$facet`, etc.). Rendimiento pobre con 300k
  eventos.
- **Why not**: el ETL y los aggregations de revenue/dashboard necesitan
  Mongo.

### Postgres para datos relacionales + Mongo para documentos
- **Pros**: SQL para joins complejos.
- **Cons**: dos motores relacionales + uno documental = 3 BD. Overhead
  operacional enorme para el caso.
- **Why not**: no hay joins complejos que justifiquen Postgres. Mongo
  con `lookup` cubre lo poco que hay.

## Consequences

### Positive
- Cada BD se optimiza para su caso de uso (Mongo para agregaciones,
  PocketBase para API REST con auth).
- El consumidor externo no toca nuestro FastAPI: independencia de
  despliegue.

### Negative
- **Escritura dual**: si el DAG falla a mitad, Mongo y PocketBase pueden
  divergir. No hay reconciliación automática.
- **Costo operacional**: 2 motores que mantener, 2 backups, 2
  monitorings.
- **Costo de dev**: el DAG tiene que conocer dos APIs distintas.

### Risks
- **Riesgo**: drift entre Mongo y PocketBase.
  **Mitigación**: el DAG valida el `count_documents` al final
  (ver `dags/hoteldata_ta02_reservations_dag.py`). Si difiere, el DAG
  falla loudly.
- **Riesgo**: PocketBase se vuelve un SPOF para el consumidor externo.
  **Mitigación**: en el futuro, considerar reemplazar PocketBase por
  un endpoint de FastAPI con su propia auth.

## References
- `docker-compose.yml:32-45` (servicio pocketbase)
- `docker-compose.yml:65-66` (env vars `POCKETBASE_*`)
- `dags/hoteldata_reservas_03_pipeline.py` (único escritor a PocketBase)
- `docs/ga03/diseno_base_datos_03.md` (esquema de la colección 03)
