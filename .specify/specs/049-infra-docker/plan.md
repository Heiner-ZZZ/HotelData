# Plan de Implementación: Infraestructura Docker

**Branch**: `049-infra-docker` | **Spec**: [spec.md](spec.md)

## Servicios

| Servicio | Imagen | Puerto | Volumen |
|----------|--------|--------|---------|
| mongo | mongo:7.0 | 27017 | mongo_data |
| redis | redis:7.4 | 6379 | redis_data |
| pocketbase | pocketbase:0.22 | 8090 | pb_data |
| server | custom (python:3.12-slim) | 8000 | — |
| airflow | custom (apache/airflow:3.2.2) | 8080 | — |
| frontend | custom (nginx:alpine) | 4200:80 | — |

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `infra/docker-compose.yml` | Orquestación principal |
| `infra/docker-compose.airflow.yml` | Perfil Airflow |
| `infra/docker-compose.local-mongo.yml` | Perfil Mongo local |
| `infra/Dockerfile` | Build de servidor |
| `frontend/Dockerfile` | Build multi-stage Angular |
| `infra/docker/airflow3.Dockerfile` | Build Airflow |

## Entregables

Este spec documenta la infraestructura Docker existente con 6 servicios, health checks, versiones pinneadas y configuración reproducible.
