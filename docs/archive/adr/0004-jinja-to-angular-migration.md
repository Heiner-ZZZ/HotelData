# ADR-0004: Migración Jinja2 → Angular (la lógica queda en Python)

## Status
Accepted

## Date
2026-06-06

## Context
- Históricamente, el web app renderizaba HTML con **Jinja2** desde
  FastAPI. Cada `web_router` retornaba `templates.TemplateResponse(...)`.
- El frontend está migrando a **Angular** (`frontend/src/app/` con
  `core/` + `features/` + `shared/`).
- La migración está **en curso**: conviven ambos. El backend todavía
  expone los `web_router` (Jinja) por compat, y los `api_router` (JSON)
  por Angular.
- `src/app/main.py` monta **ambos** routers. Eso explica la proliferación
  de routers por módulo (un sub-dominio típico tiene 3-4 routers:
  `router`, `web_router`, `api_router`, `legacy_*`).

## Decision
**El frontend Angular consume los endpoints JSON. La lógica de negocio
permanece en Python (FastAPI + services). Jinja2 es legacy y se
mantiene solo para rutas no migradas todavía.**

Reglas:

1. **Toda lógica de negocio (validación, transformación, reglas de
   dominio, autorización fina) vive en `src/app/modules/<context>/
   services/`** (Python). Angular es presentación pura.
2. **Nuevas features = nueva API JSON en `api_router`**, no nueva
   página Jinja.
3. **Templates Jinja se eliminan cuando la última ruta que los usa se
   migra a Angular**. Tracking en `docs/frontend/frontend_migration_status.md`.
4. **No se duplica lógica en TypeScript.** Si Angular necesita una
   transformación costosa, llama al endpoint y deja que Python la haga.
5. **El router `web_router` se considera deprecado** para nuevos
   endpoints. Los existentes siguen funcionando.

## Alternatives Considered

### SSR con Angular Universal
- **Pros**: primer render rápido, mejor SEO.
- **Cons**: complejidad operacional alta; para un B2B con auth por
  sesión, el SEO no aporta. El primer render no es el cuello de
  botella.
- **Why not**: el proyecto no tiene problema que SSR resuelva.

### Migrar a BFF (Backend-for-Frontend) por contexto
- **Pros**: cada bounded context tiene su BFF que orquesta.
- **Cons**: hoy sería un solo BFF (FastAPI ya hace de BFF). Fragmentar
  sería extraer bounded contexts a microservicios, lo que ADR-0001 y
  ADR-0005 descartan por ahora.
- **Why not**: prematuro.

### Mover parte de la lógica a TypeScript (cliente rico)
- **Pros**: menos round-trips, latencia percibida mejor.
- **Cons**: dos fuentes de verdad (Python y TS) para la misma regla
  de negocio. Drift garantizado.
- **Why not**: el costo de mantener dos implementaciones de la misma
  regla es peor que un round-trip extra.

## Consequences

### Positive
- Una sola fuente de verdad para reglas de negocio: Python.
- El backend es testeable sin Angular (capa de servicios pura).
- El frontend se mantiene simple: solo presenta datos y captura input.

### Negative
- **Más round-trips**: Angular no puede hacer joins client-side de
  datos que viven en distintas colecciones. Mitigación: endpoints
  agregados (`properties_dashboard`, `partner_hotel_edit_profile`)
  que devuelven todo lo que la vista necesita en un solo request.
- **Latencia del primer paint**: hasta que Angular haga su bootstrap +
  HTTP, el usuario ve spinner. Mitigación: skeletons + lazy loading
  por feature.
- **Proliferación de routers**: 3-4 routers por módulo durante la
  transición. Es transitorio y se resuelve cuando se borren los
  `web_router` deprecados.

### Risks
- **Riesgo**: que se cuele lógica de negocio en un componente Angular
  (`*.ts` con un `if` que debería estar en el servicio Python).
  **Mitigación**: code review + buscar funciones con副作用 en
  componentes puros durante la migración.
- **Riesgo**: que convivan Jinja y Angular para la misma vista, con
  UX inconsistente.
  **Mitigación**: el router `web_router` está marcado deprecated y se
  eliminará cuando su último consumidor migre.

## References
- `frontend/src/app/` (Angular app con `core/`, `features/`, `shared/`)
- `src/app/main.py:67-103` (monta routers Jinja y JSON)
- `docs/frontend/frontend_migration_status.md` (estado por vista)
- `docs/frontend/angular_contract_validation.md` (contrato API ↔ TS)
- `docs/frontend/api_gaps_report.md` (qué endpoints faltan)
