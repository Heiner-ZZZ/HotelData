# Integracion real de Redis en GA03

## Objetivo

Esta integracion agrega Redis como capa opcional de cache para evolucion futura del sistema, sin volverlo requisito para que la aplicacion web funcione.

## Alcance implementado

- Archivo de configuracion: `config/redis_settings.py`
- Cliente opcional: `src/cache/redis_client.py`
- Servicio de cache: `src/cache/cache_service.py`
- Ruta de diagnostico: `GET /system/redis-status`

## Comportamiento esperado

- Si `REDIS_ENABLED=false`, la aplicacion sigue funcionando con normalidad.
- Si el servicio Redis no esta activo, la aplicacion no se cae.
- La ruta `/system/redis-status` responde el estado real de configuracion y conexion.
- Redis no participa en ETL, Airflow, PocketBase ni MongoDB como almacenamiento principal.

## Variables de entorno

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_ENABLED=false
```

Opcionalmente puede usarse `REDIS_URL`, por ejemplo:

```env
REDIS_URL=redis://localhost:6379/0
```

## Funciones disponibles

- `get_redis_client()`
- `redis_available()`
- `set_cache(key, value, ttl_seconds)`
- `get_cache(key)`
- `delete_cache(key)`

## Usos previstos

- Cache futuro de dashboard
- Cache de busquedas frecuentes
- Cache de sesiones complementarias
- Estado temporal de procesos ligeros de interfaz

## Validacion funcional

1. La aplicacion debe arrancar aunque Redis este apagado.
2. `GET /system/redis-status` debe mostrar `connected=false` cuando Redis no esta activo.
3. Si Redis se activa y `REDIS_ENABLED=true`, la misma ruta debe mostrar `connected=true`.

## Resultado arquitectonico

Redis queda integrado de forma real, pero aislada. Esto permite empezar a usar cache gradualmente sin acoplar el sistema actual ni volver fragil la app si Redis no esta disponible.
