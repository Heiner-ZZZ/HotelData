# Especificacion: Monitoreo de Servicios

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T11 (Monitorear servicios), CU-E04 (Monitorear disponibilidad global)

## 1. Objetivo

Monitorear el estado de los servicios del sistema: backend FastAPI, Redis, MongoDB, Airflow, frontend Angular.

## 2. Contexto

Docker Compose con 6 servicios. Cada servicio tiene health checks. El backend expone endpoints de health check.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Super Admin | Monitorea estado global |
| Admin Sistema | Diagnostica problemas de servicios |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe exponer endpoint GET /health | Alta |
| RF-002 | El sistema debe verificar conexion a MongoDB | Alta |
| RF-003 | El sistema debe verificar estado de Redis | Alta |
| RF-004 | El sistema debe exponer un panel de monitoreo basico | Media |

## 5. Reglas de negocio

- Cada servicio se verifica individualmente
- MongoDB: db.command('ping')
- Redis: redis_client.ping()

## 6. Salidas

```json
{
  "status": "ok",
  "services": {
    "mongodb": { "status": "ok", "response_time_ms": 5 },
    "redis": { "status": "ok", "response_time_ms": 2 }
  }
}
```

## 7. Escenarios

### Escenario 1: Consultar health check
```gherkin
Dado que el admin consulta GET /health
Cuando todos los servicios funcionan
Entonces el sistema responde con status ok
```

## 8. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | /health responde con estado de todos los servicios |
| CA-002 | MongoDB ping funciona |
| CA-003 | Redis ping funciona |

## 9. Dependencias

- Modulo: src/app/modules/health/routes.py
- MongoDB, Redis, PocketBase

## 10. Fuera de alcance

- Alertas automaticas (email, Slack)
- Historial de uptime
