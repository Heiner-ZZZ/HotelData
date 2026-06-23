# Especificacion: Configuracion de Entornos

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: Todos (configuracion global del sistema)

## 1. Objetivo

Configuracion global del sistema: settings.py, .env, CORS, chunk/batch sizes, paths.

## 2. Variables de configuracion

| Variable | Default | Descripcion |
|----------|---------|-------------|
| MONGODB_URL | mongodb://mongo:27017 | Conexion MongoDB |
| REDIS_URL | redis://redis:6379 | Conexion Redis |
| POCKETBASE_URL | http://pocketbase:8090 | Conexion PocketBase |
| SESSION_TTL_HOURS | 8 | Duracion de sesion |
| CORS_ORIGINS | http://localhost:4200 | Origenes CORS |
| CHUNK_SIZE | 50000 | Filas por chunk ETL |
| BATCH_SIZE | 5000 | Documentos por batch insert |
| DATA_DIR | data/ | Directorio de datos |

## 3. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | settings.py carga correctamente las variables de .env |
| CA-002 | CORS configurado para el origen del frontend |
| CA-003 | Chunk y batch sizes configurados correctamente |

## 4. Dependencias

- server/config/settings.py
- server/config/.env.example
- server/config/redis_settings.py
