# Especificacion: Infraestructura Docker

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T11, CU-E04 (Monitorear servicios, disponibilidad global)

## 1. Objetivo

Desplegar y mantener el sistema con Docker Compose: 6 servicios con health checks.

## 2. Servicios

| Servicio | Imagen | Puerto | Proposito |
|----------|--------|--------|-----------|
| mongo | mongo:7.0 | 27017 | Base de datos |
| redis | redis:7.4 | 6379 | Cache |
| pocketbase | pocketbase:0.22 | 8090 | Fuente ETL |
| server | custom (python:3.12-slim) | 8000 | FastAPI |
| airflow | custom (apache/airflow:3.2.2) | 8080 | Orquestador ETL |
| frontend | custom (nginx:alpine) | 4200:80 | Angular SPA |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | docker-compose.yml con 6 servicios y health checks | Alta |
| RF-002 | Versiones pinneadas para reproducibilidad | Alta |
| RF-003 | Red compartida entre servicios | Alta |
| RF-004 | Volumenes persistentes (mongo_data, redis_data, pb_data) | Alta |

## 4. Dependencias

- infra/docker-compose.yml
- frontend/Dockerfile
- infra/Dockerfile
- infra/docker/airflow3.Dockerfile
