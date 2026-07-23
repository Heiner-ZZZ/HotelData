# Docker local en Windows

Este entorno permite levantar `HotelData` desde Docker Desktop en Windows, sin depender de WSL.

## Servicios incluidos

- `app`: FastAPI + Angular
- `mongo`: MongoDB para `hoteldata`
- `redis`: cache opcional pero habilitado en Docker
- `pocketbase`: fuente operacional para pruebas y preparacion de GA03

## Compose con Mongo local (Windows)

Si usas `docker-compose.local-mongo.yml`, ese compose **no** define servicio `mongo`.
La app se conecta al MongoDB local de Windows via `host.docker.internal:27018`.

```powershell
docker compose -f hoteldata_project/docker-compose.local-mongo.yml up -d redis app
```

No usar:

```powershell
docker compose -f hoteldata_project/docker-compose.local-mongo.yml up -d mongo redis app
```

## Archivos usados

- `../docker-compose.yml`
- `../Dockerfile`
- `./.env.example`
- `../scripts/docker_healthcheck_ga03.py`

## Variables clave dentro de Docker

- `MONGO_URI=mongodb://mongo:27017`
- `MONGO_DATABASE=hoteldata_hub`
- `REDIS_HOST=redis`
- `REDIS_PORT=6379`
- `REDIS_ENABLED=true`
- `POCKETBASE_URL=http://pocketbase:8090`
- `POCKETBASE_COLLECTION_03=hotel_reservation_events_03`
- `TASK_NUMBER=03`
- `TARGET_RECORDS=300000`

## Levantar desde PowerShell

```powershell
docker compose up -d --build
```

## Ver estado

```powershell
docker compose ps
```

## Ver logs de la app

```powershell
docker compose logs -f app
```

## Apagar servicios

```powershell
docker compose down
```

## Validar salud del stack

Desde PowerShell local:

```powershell
python scripts/docker_healthcheck_ga03.py
```

Si prefieres validar con el stack ya levantado:

```powershell
docker compose exec app python scripts/docker_healthcheck_ga03.py
```

## Importante

- Docker no ejecuta ETL automaticamente.
- Docker no carga los `300000` registros por si solo.
- PocketBase, MongoDB y Redis se levantan vacios en sus volumenes Docker si es la primera vez.
- El entorno actual de Docker usa datos propios de los volumenes `mongo_data`, `redis_data` y `pocketbase_data`.
- Tus datos locales actuales fuera de Docker no se mezclan automaticamente con MongoDB dentro del contenedor.
- Si luego quieres reutilizar datos existentes, habria que importar un dump o montar una ruta explicita.

## Nota sobre PocketBase

El stack usa una imagen de PocketBase para desarrollo local. Si mas adelante decides cambiar a otra imagen o a binario local, la app seguira funcionando ajustando `POCKETBASE_URL`, sin rehacer la arquitectura.
