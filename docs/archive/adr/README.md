# ADR Index

Decisiones arquitectónicas del proyecto HotelData. Cada ADR es un
contrato: si la decisión cambia, este archivo o el ADR cambia primero.

| # | Título | Estado | Fecha |
|---|---|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith (FastAPI + Angular) | Accepted | 2026-06-06 |
| [0002](0002-dual-database-mongo-pocketbase.md) | Dual database: MongoDB + PocketBase | Accepted | 2026-06-06 |
| [0003](0003-cookie-session-in-mongodb.md) | Cookie session persistida en MongoDB | Accepted | 2026-06-06 |
| [0004](0004-jinja-to-angular-migration.md) | Migración Jinja2 → Angular (lógica en Python) | Accepted | 2026-06-06 |
| [0005](0005-stay-monolith-no-microservices-yet.md) | Quedarse en monolito modular (no extraer) | Accepted | 2026-06-06 |

## Cómo escribir un ADR nuevo

1. Copia `0001-modular-monolith.md` como plantilla.
2. Numera secuencialmente: `0006-<slug>.md`.
3. Status: `Proposed` → `Accepted` → `Deprecated` / `Superseded by ADR-NNNN`.
4. Mantén "Consequences" honestas: si la decisión tiene costos, dilos.
5. Si la decisión revierte, marca como `Superseded by ADR-NNNN` — no borres.
