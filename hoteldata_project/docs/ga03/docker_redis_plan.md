# Plan Docker y Redis GA03

## Propósito

Este plan deja el proyecto preparado documentalmente para fases posteriores de despliegue. No obliga a ejecutar el sistema con Docker y no modifica el ETL validado.

## Servicios propuestos

| Servicio | Uso previsto | Estado |
| --- | --- | --- |
| `mongo` | Base `hoteldata_hub` para hechos, dimensiones y control. | Preparado |
| `redis` | Cache y estado temporal futuro. | Preparado |
| `pocketbase` | Fuente operacional `hotel_reservation_events_03`. | Preparado |
| `app` | Aplicación FastAPI/Jinja actual. | Preparado |

## Redis planificado

Redis se propone para:

- Cache de dashboard.
- Cache de búsquedas frecuentes.
- Sesiones futuras.
- Estado temporal de jobs.
- Rate limiting futuro.

No se conecta Redis al ETL actual para evitar afectar el flujo validado PocketBase -> JSONL -> Parquet -> MongoDB.

## Variables sugeridas

```env
REDIS_URL=redis://localhost:6379/0
REDIS_ENABLED=false
REDIS_DEFAULT_TTL_SECONDS=300
```

## Uso esperado posterior

1. Levantar servicios con Docker Compose.
2. Validar que MongoDB, PocketBase y Redis respondan.
3. Ejecutar la app con las mismas rutas actuales.
4. Mantener Airflow como compose separado o despliegue independiente.
5. Conectar Redis solo cuando se agregue una historia técnica específica.

## Compose principal

El archivo `docker-compose.yml` define `mongo`, `redis`, `pocketbase` y `app`.

## Compose Airflow opcional

El archivo `docker-compose.airflow.yml` queda como scaffolding opcional. No reemplaza el DAG existente ni fuerza ejecución Docker.
