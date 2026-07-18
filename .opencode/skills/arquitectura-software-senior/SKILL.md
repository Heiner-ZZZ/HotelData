---
name: arquitectura-software-senior
description: Use when designing system architecture, choosing patterns (monolith vs microservices), reviewing coupling/cohesion, defining bounded contexts, creating ADRs, or migrating from monolith to microservices. Covers Clean Architecture, Hexagonal, DDD, C4 model, and event-driven patterns.
---

# Senior Software Architect

## 2026 Landscape
- **Modular Monolith** is the recommended default — microservices are an extraction strategy, not a starting point
- **ADR (Architecture Decision Records)** are standard practice — every significant decision gets documented
- **C4 Model** (Context → Container → Component → Code) for architecture diagrams
- **DDD + Bounded Contexts** for domain modeling
- **Event-Driven Architecture** for async workflows and cross-context communication
- **Strangler Fig pattern** for incremental migration from monolith to microservices

## Decision Framework: Monolith vs Microservices

| Factor | Monolith | Microservices |
|---|---|---|
| Team size | < 20 developers | > 50 developers |
| Scale | < 1M users | > 10M with uneven load |
| Time to market | Faster initially | Slower initially, faster at scale |
| Domain complexity | Single bounded context | Multiple clear bounded contexts |
| Deployment freq | Weekly/monthly | Multiple daily |
| ACID requirements | Simple | Saga pattern needed |
| Cost (infra) | Lower | Higher (service mesh, gateways) |

**Rule of thumb**: Start modular monolith. Extract services when you hit specific pain points, not before.

## This Project Architecture

### Current: Modular Monolith (FastAPI + Angular 22)
```
┌─────────────────────────────────────────────────────┐
│                    Nginx (Port 80/4200)              │
│  /api/* → backend:8000  /static → Angular 22 SPA    │
├────────────────────┬───────────────────┬────────────┤
│  modules/          │  features/        │  angular/   │
│  ─────────         │  ─────────        │  ─────────  │
│  auth              │  audit            │  core/      │
│  admin             │  catalogs         │  features/  │
│  hotels            │  dashboard        │  shared/    │
│  partner           │  quality          │             │
│  reservations      │  records          │             │
│  revenue           │  etl_status       │             │
│  users             │  ta02_crud        │             │
├────────────────────┴───────────────────┴────────────┤
│                    MongoDB                           │
│  Users, Roles, Hotels, Reservations, Catalogs...     │
├─────────────────────────────────────────────────────┤
│              Redis / PocketBase / ETL                │
└─────────────────────────────────────────────────────┘
```

### ADR Template (for all future decisions)
```markdown
# ADR-XXX: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Date
YYYY-MM-DD

## Context
What is the situation? What problem are we solving?
What constraints exist?

## Decision
What was decided, precisely.

## Alternatives Considered
1. **Alternative A**: Pros / Cons / Why not
2. **Alternative B**: Pros / Cons / Why not

## Consequences
### Positive
- benefit 1
- benefit 2
### Negative
- drawback 1
- drawback 2
### Risks
- risk + mitigation

## References
```

## Architectural Patterns Reference

### 1. Clean Architecture (for new modules)
```
┌──────────────────────────────────────┐
│  Frameworks & Drivers                │
│  FastAPI, MongoDB, Redis, Docker     │
├──────────────────────────────────────┤
│  Interface Adapters                  │
│  Routes, Schemas (Pydantic), Views   │
├──────────────────────────────────────┤
│  Application / Use Cases             │
│  Services, DTOs, Port interfaces     │
├──────────────────────────────────────┤
│  Domain / Entities                   │
│  Pure Python objects, business rules │
└──────────────────────────────────────┘
```
**Dependency Rule**: Outer → Inner. Domain imports NOTHING from frameworks.

### 2. Hexagonal / Ports & Adapters
```
  [Web] ──→  [Inbound Port] ──→ [Application] ──→ [Outbound Port] ──→ [DB]
  [CLI] ──→  (interface)       │   Core Logic    │  (interface)      [API]
                                └─────────────────┘
```
Use when business logic is complex and must be testable without infrastructure.

### 3. CQRS
Separate read and write models. Use when:
- Read and write shapes differ significantly
- High read volume with low write volume
- Need different optimization for each path

### 4. Event-Driven
```python
# Publish domain event
bus.publish("reservation.created", {
    "reservation_id": ...,
    "hotel_id": ...,
    "timestamp": now,
})

# Subscribe (separate module)
@bus.subscribe("reservation.created")
def on_reservation_created(event):
    update_revenue_metrics(event)
    notify_hotel_partner(event)
```

## Quality Gates
- **Cohesion**: Each module has one reason to change
- **Coupling**: Module A knows Module B's interface but not its internals
- **Testability**: Domain logic testable without DB/HTTP
- **Extensibility**: New features = new files, not modifying existing ones (Open/Closed)

## Migration Path (Monolith → Microservices)
1. **Phase 1**: Modular monolith with clear bounded contexts ✅ (CURRENT)
2. **Phase 2**: Extract one context as independent service (e.g., auth)
3. **Phase 3**: Add event bus between contexts
4. **Phase 4**: Deploy services independently with CI/CD per service

Use **Strangler Fig pattern**: route traffic gradually to new services while old routes remain.

## C4 Model Diagramming
- **Level 1 (Context)**: System boundary, users, external systems (PocketBase)
- **Level 2 (Container)**: Angular SPA, FastAPI backend, MongoDB, Redis, Nginx
- **Level 3 (Component)**: Modules inside the backend (auth, hotels, revenue...)
- **Level 4 (Code)**: Classes/files inside a module

## Security Architecture Considerations
- Auth boundary: session service owns all auth logic
- Data boundary: each module owns its MongoDB collections
- Network boundary: Docker compose network, only expose nginx:80
- API boundary: all external access through nginx proxy
