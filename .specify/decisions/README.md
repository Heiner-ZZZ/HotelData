# Architecture Decision Records (ADRs)

> **Requisito constitucional**: §13 (cascada spec-kit) y §14.5 (ADRs pendientes) de `.specify/memory/constitution.md` v0.9+ referencian esta carpeta.

Cada decisión arquitectónica significativa que tome este proyecto se registra aquí como un ADR individual, versionado, inmutable (no se editan — se reemplazan con un nuevo ADR que sobrescribe el anterior).

## Convención

- **Nombre de archivo**: `ADR-NNNN-titulo-corto-en-kebab.md` con NNNN secuencial de 4 dígitos (ej. `ADR-0001-por-que-dual-write.md`).
- **Estado**: `proposed`, `accepted`, `deprecated`, `superseded-by-ADR-NNNN`.
- **Inmutable una vez `accepted`**: si una decisión cambia, crear un nuevo ADR que la reemplaza (`superseded-by` link al original).
- **Owner**: cada ADR declara un dueño concreto (rol + persona cuando aplique).

## Índice de Decisiones

| ADR | Título | Estado | Fecha | Owner |
|-----|--------|--------|-------|-------|
| ADR-0000 | Template de ADR | accepted | 2026-07-28 | `admin_sistema` |
| ADR-0001 | Migración MongoDB 7.0 → 8.0 en `infra/docker-compose.yml` | proposed | 2026-07-28 | `admin_sistema` + `auditor_datos` |
| ADR-0002 | Poach selectivo de `fastapi-patterns` desde ECC (con adaptación HotelData) | proposed | 2026-07-28 | `admin_sistema` + `auditor_datos` (post-MVP) |
| *(pendientes — ver §14.5 del constitution)* | | | | |

## Cómo Proponer un ADR

1. Copiar `ADR-0000-template.md`.
2. Nombrar `ADR-NNNN-titulo-corto.md`.
3. Llenar las secciones requeridas: Contexto, Decisión, Consecuencias, Alternativas Consideradas.
4. Marcar como `proposed`.
5. Abrir PR con al menos 1 reviewer aprobador de `.specify/memory/constitution.md` §14.1.
6. Una vez aprobado, mergear → estado `accepted`. Inmutable de ahí en adelante.

## Cross-References

- `.specify/memory/constitution.md` §13 (cascada), §14.1 (jerarquía), §14.5 (ADRs planificados).
- `.specify/specs/` — cada spec MAY referenciar uno o más ADRs.
- `knowledge.md` — referencias operativas; no trata decisiones arquitectónicas, solo convenciones derivadas.
