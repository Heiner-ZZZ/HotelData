# Plan de Implementación: Configuración de Entornos

**Branch**: `050-configuracion-entornos` | **Spec**: [spec.md](spec.md)

## Variables de configuración

| Variable | Default | Descripción |
|----------|---------|-------------|
| MONGODB_URL | mongodb://mongo:27017 | Conexión MongoDB |
| REDIS_URL | redis://redis:6379 | Conexión Redis |
| POCKETBASE_URL | http://pocketbase:8090 | Conexión PocketBase |
| SESSION_TTL_HOURS | 8 | Duración de sesión |
| CORS_ORIGINS | http://localhost:4200 | Orígenes CORS |
| CHUNK_SIZE | 50000 | Filas por chunk ETL |
| BATCH_SIZE | 5000 | Documentos por batch insert |
| DATA_DIR | data/ | Directorio de datos |

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `server/config/settings.py` | Configuración central (pydantic-settings) |
| `server/config/.env.example` | Template de variables |
| `server/config/redis_settings.py` | Configuración Redis |
| `.env` | Variables reales (gitignored) |
| `infra/docker-compose.yml` | Environment variables para servicios |

## Entregables

Este spec documenta la configuración global existente del sistema.
