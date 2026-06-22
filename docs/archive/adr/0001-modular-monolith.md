# ADR-0001: Modular Monolith (FastAPI + Angular)

## Status
Accepted

## Date
2026-06-06

## Context
- El proyecto es un ETL estricto + web app de gestión hotelera con ~10
  bounded contexts: auth, admin, hotels, partner, reservations, revenue,
  audit, dashboard, ETL status, catalogs.
- Tamaño del equipo: < 10 desarrolladores.
- Volumen objetivo: < 1M usuarios, 300k registros de eventos en `fact_*`.
- ACID es importante (reservas, pagos, inventario) — no queremos saga
  patterns todavía.
- Tiempo a mercado: el equipo necesita entregar features en semanas, no
  en trimestres.

## Decision
Adoptamos **modular monolith** como arquitectura objetivo:

- **Backend**: un solo proceso FastAPI con `src/app/modules/<context>/` por
  bounded context. Cada módulo expone `routes.py` (HTTP) + `schemas.py`
  (Pydantic) + `services/` (lógica).
- **Frontend**: un solo bundle Angular con `core/` + `features/`. Cada
  feature es un lazy-loaded module.
- **DB**: una sola instancia MongoDB con una colección por agregado de
  dominio. PocketBase para un sub-dominio específico (ver ADR-0002).
- **Despliegue**: un contenedor Docker por proceso (app + frontend + Mongo
  + Redis + PocketBase), detrás de Nginx.
- **Comunicación entre bounded contexts**: imports directos en Python
  (estamos en el mismo proceso), no event bus. Cuando duela, añadir
  event bus interno (ver ADR-0005).

## Alternatives Considered

### Microservicios
- **Pros**: escalado independiente, equipos desacoplados, deploys
  independientes.
- **Cons**: 5–10 servicios para 10 contextos = 5–10 deploy pipelines,
  service mesh, tracing distribuido, sagas para ACID, costo de infra
  3–5x. **Mucho overhead para el tamaño actual del equipo.**
- **Why not**: el equipo no llega a 50 devs, no hay SLA distinto por
  contexto, y los datos están altamente acoplados (reservas ← hoteles
  ← inventario ← tarifas).

### Layered monolith (capas, no módulos)
- **Pros**: simplicidad inicial.
- **Cons**: igual termina en god class. Es lo que teníamos antes del
  refactor de Phase 1 (ver `docs/refactor-checklist.md`).
- **Why not**: el módulo como unidad de ownership escala mejor que la
  capa.

### Serverless por bounded context
- **Pros**: zero ops.
- **Cons**: estado de sesión, conexión persistente a Mongo, plantillas
  Jinja legadas — todas fricciones con FaaS.
- **Why not**: la migración no se justifica con el tráfico actual.

## Consequences

### Positive
- Un solo proceso, un solo deploy, un solo log stream. Debug simple.
- Tests de integración cubren flujos cross-context sin red.
- ACID gratis: transacciones Mongo multi-documento cuando se necesiten.
- Refactors cross-context son búsquedas y reemplazos, no deploys
  coordinados.

### Negative
- Acoplamiento accidental: es fácil que `partner` importe de `revenue`
  sin que se note. Mitigación: la regla §13.3 de
  `.opencode/skills/backend-senior/SKILL.md` y code review.
- Un módulo puede degradar a todo el proceso. Mitigación: timeouts en
  llamadas a Mongo, circuit breakers alrededor de PocketBase.
- Escalar es escalar el proceso entero. Aceptable hasta ~50 RPS; más
  allá, extraer el cuello de botella (ver ADR-0005).

### Risks
- **Riesgo**: que el monolito se re-infle con el tiempo.
  **Mitigación**: la skill `backend-senior` §13 prohíbe `service.py >
  400 lines` y obliga a seccionar por sub-dominio.

## References
- `.opencode/skills/arquitectura-software-senior/SKILL.md` (decision
  framework monolith vs microservices)
- `.opencode/skills/backend-senior/SKILL.md` §13 (anti god-class)
- `docs/refactor-checklist.md` Phase 1 (ya ejecutado)
- ADR-0005 (cuándo reconsiderar)
