# Docker Compose base para entorno local

## Objetivo

Se prepara una alternativa Docker Compose para ejecutar servicios locales del proyecto sin reemplazar el entorno actual validado en Windows/WSL.

## Servicios incluidos

- `mongo`: base de datos MongoDB para `hoteldata_hub`
- `redis`: cache opcional para integraciones futuras
- `pocketbase`: fuente operacional para pruebas locales
- `app`: aplicacion FastAPI/Jinja2

## Archivos creados o ajustados

- `docker-compose.yml`
- `docker/.env.example`
- `docker/README.md`
- `Dockerfile`

## Como levantar

```powershell
docker compose up -d
```

## Como apagar

```powershell
docker compose down
```

## Variables de entorno base

El contenedor `app` consume:

- `MONGO_DATABASE=hoteldata_hub`
- `POCKETBASE_COLLECTION_03=hotel_reservation_events_03`
- `TASK_NUMBER=03`
- `TARGET_RECORDS=300000`
- `GA03_EXPECTED_RECORDS=300000`
- `REDIS_ENABLED=false`

## Advertencia de alcance

- El entorno validado actual sigue siendo manual/WSL.
- Docker queda preparado como alternativa para fases siguientes.
- No se modifica ETL, Airflow, PocketBase real ni MongoDB real por este cambio.

## PocketBase en Docker o binario local

El compose incluye una imagen de PocketBase para desarrollo local. Si mas adelante se decide usar el binario oficial local, la app puede seguir funcionando ajustando `POCKETBASE_URL` sin rehacer la arquitectura.

## Validacion esperada

Si Docker esta disponible, puede validarse con:

```powershell
docker compose config
```

Si Docker no esta disponible, el cambio se considera preparado por validacion estatica del archivo YAML y la documentacion asociada.
