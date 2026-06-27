# Plan de Implementación: Sistema General

**Branch**: `main` | **Spec**: 000-sistema-general

## Stack

| Componente | Tecnología | Versión |
|-----------|-----------|---------|
| Backend | FastAPI / Python | 3.12 / 0.110+ |
| Frontend | Angular 21 standalone | 21 |
| Base de datos | MongoDB | 7.0 |
| Caché | Redis | 7.4 |
| Orquestador | Apache Airflow | 3.2.2 |
| Fuente datos | PocketBase | 0.22.0 |

## Estructura de proyectos

```
/ ─── hoteldata_project/
├── server/         → FastAPI backend
│   ├── config/     → settings.py, redis
│   ├── src/
│   │   ├── app/    → módulos (auth, admin, partner, revenue, etc.)
│   │   ├── etl/    → pipelines (TAF01, TA02, GA03)
│   │   ├── database/ → conexión, colecciones, índices
│   │   └── cache/  → redis
│   └── tests/
├── frontend/       → Angular 21 standalone
│   └── src/app/
│       ├── features/ → lazy modules
│       └── shared/   → UI, utils, api
├── infra/          → docker-compose.yml
└── .specify/specs/ → 50 specs SDD
```

## Principios arquitectónicos

1. Python-First con Separación de Capas (Constitución I)
2. Límite Airflow-Web (Constitución II)
3. Normalización Multi-Propiedad (Constitución III)
4. Calidad de Datos como Proceso (Constitución IV)
5. Desarrollo Basado en Evidencia con Matriz de Trazabilidad (Constitución V)
6. Mejora Progresiva (Constitución VI)
7. Operacional-First con Dual-Write (Constitución VII)
