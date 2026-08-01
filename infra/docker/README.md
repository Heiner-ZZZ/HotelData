# Docker local en Windows

Este entorno permite levantar `HotelData` desde Docker Desktop en Windows, sin depender de WSL.

## Servicios incluidos

- `server`: FastAPI
- `frontend`: Angular servido por Nginx
- `mongo`: MongoDB para `hoteldata`
- `redis`: caché de la aplicación y broker de Celery para Airflow
- `pocketbase`: fuente operacional para pruebas y preparación de GA03
- `airflow-postgres`: base de metadatos exclusiva de Airflow
- `airflow-init`, `airflow-api-server`, `airflow-scheduler`, `airflow-dag-processor`, `airflow-triggerer`, `airflow-worker`: un único despliegue lógico de Airflow 3 descompuesto por servicio

## Archivos usados

- `infra/docker-compose.yml`
- `infra/Dockerfile`
- `infra/docker/.env.example`
- `server/scripts/docker_healthcheck_ga03.py`

## Variables clave dentro de Docker

- `MONGO_URI=mongodb://mongo:27018`
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
docker compose --env-file .env -f infra/docker-compose.yml up -d --build
```

## Ver estado

```powershell
docker compose --env-file .env -f infra/docker-compose.yml ps
```

## Ver logs de la app

```powershell
docker compose --env-file .env -f infra/docker-compose.yml logs -f server
```

## Apagar servicios

```powershell
docker compose --env-file .env -f infra/docker-compose.yml stop
```

## Validar salud del stack

Desde PowerShell local:

```powershell
python server/scripts/docker_healthcheck_ga03.py
```

Si prefieres validar con el stack ya levantado:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml exec server python server/scripts/docker_healthcheck_ga03.py
```

## Airflow descompuesto

Airflow no se separa por PMS, CRS, Booking Engine ni por tenant. HotelData usa un solo despliegue lógico con componentes independientes:

```text
airflow-postgres       metadata de Airflow
airflow-init            migraciones iniciales
airflow-api-server      UI/API en :8080
airflow-scheduler       planificación
airflow-dag-processor   lectura/procesamiento de DAGs
airflow-triggerer       tareas diferibles
airflow-worker          ejecución Celery
```

El DAG activo `hoteldata_ga03_etl` conserva el flujo completo implementado: preparación CSV → PocketBase, validación y ETL PocketBase → MongoDB. La separación de componentes permite escalar y aislar la infraestructura de Airflow, pero no introduce aún ningún ETL hacia ClickHouse.

Arranque y validación:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml config --quiet
docker compose --env-file .env -f infra/docker-compose.yml up -d --build airflow-postgres airflow-init airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer airflow-worker
```

La URL de la UI/API de Airflow es `http://localhost:8080`. La base `airflow-postgres` es únicamente la metadata database de Airflow; no sustituye MongoDB ni almacena datos operativos del hotel.

## Importante

- Docker no ejecuta ETL automaticamente.
- Docker no carga los `300000` registros por si solo.
- PocketBase, MongoDB y Redis se levantan vacios en sus volumenes Docker si es la primera vez.
- El entorno actual de Docker usa datos propios de los volumenes `mongo_data`, `redis_data` y `pocketbase_data`.
- Tus datos locales actuales fuera de Docker no se mezclan automaticamente con MongoDB dentro del contenedor.
- Si luego quieres reutilizar datos existentes, habria que importar un dump o montar una ruta explicita.

## Nota sobre PocketBase

El stack usa una imagen de PocketBase para desarrollo local. Si mas adelante decides cambiar a otra imagen o a binario local, la app seguira funcionando ajustando `POCKETBASE_URL`, sin rehacer la arquitectura.
