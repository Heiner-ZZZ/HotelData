# Especificacion: Contratos API

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T02 (Gestionar contratos API, endpoints y documentacion OpenAPI)

## 1. Objetivo

Gestionar contratos API, endpoints JSON documentados con OpenAPI y validacion frontend-backend.

## 2. Contexto

FastAPI genera documentacion OpenAPI automaticamente en /docs. Los contratos se validan con scripts.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Admin sistema | Gestiona documentacion y contratos |
| Desarrollador | Consulta documentacion OpenAPI |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe exponer OpenAPI en /docs con todos los endpoints | Alta |
| RF-002 | El sistema debe tener scripts de validacion de contrato frontend-backend | Alta |
| RF-003 | El sistema debe exponer endpoint de health check | Alta |
| RF-004 | El sistema debe usar Pydantic models para validacion | Alta |

## 5. Escenarios

### Escenario 1: Validar contratos frontend-backend
```gherkin
Dado que se ejecuta el script de validacion de contratos
Cuando encuentra discrepancias
Entonces reporta las rutas faltantes o incorrectas
```

## 6. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | OpenAPI en /docs muestra todos los endpoints |
| CA-002 | Health check responde correctamente |
| CA-003 | Scripts de validacion no reportan errores |

## 7. Dependencias

- FastAPI (OpenAPI automatico)
- Scripts: validate_frontend_backend_contract.py, validate_angular_routes_contract.py

## 8. Fuera de alcance

- API keys para partners externos
- Rate limiting
