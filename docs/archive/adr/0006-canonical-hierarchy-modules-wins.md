# ADR-0006: Jerarquía canónica en `src/app/`: `modules/` gana sobre `features/`

## Status
Accepted

## Date
2026-06-06

## Context
`src/app/` tiene dos jerarquías paralelas:

- `src/app/features/` — código vivo legacy, montado en
  `src/app/main.py:10-23`. Patrón "feature folder" del scaffold
  original. Contiene `audit`, `dashboard`, `quality`, `collections`,
  `records`, `problems`, `catalogs`, `company`, `etl_status`,
  `ta02_crud`.
- `src/app/modules/` — bounded contexts introducidos en
  `docs/ga03/arquitectura_modular_integraciones.md` (GA03).
  Contiene `auth`, `admin`, `audit`, `hotels`, `partner`,
  `reservations`, `revenue`, `users`, `account`.

Hoy solo `audit` tiene archivos en **ambas** jerarquías:

- `src/app/features/audit/` sirve `GET /audit` (HTML) y
  `GET /api/audit/activity` (JSON) usando `etl_executions` y
  `search_logs`.
- `src/app/modules/audit/` es un stub que sirve
  `GET /modules/audit/status` y dice en su descripción
  *"la auditoria ETL actual sigue en features/audit"*.

Los otros `features/*` no colisionan en URL con ningún `modules/*`,
pero la duplicación conceptual crece con cada PR nuevo (los devs
nuevos no saben dónde poner código nuevo).

`main.py:10-23` y `main.py:24-47` montan routers de ambas
jerarquías en el mismo proceso FastAPI, así que ambos viven
simultáneamente.

## Decision
**`modules/` es la jerarquía canónica para código nuevo de
dominio.** `features/` queda marcado como legacy. La migración
sigue **Strangler Fig**: el código vivo permanece donde está hasta
que un bounded context específico se migre de forma explícita.
**No se elimina nada** en esta fase: los archivos en `features/`
que ya no se montan quedan como orphan, no como borrados.

### Piloto de migración: `audit`

`audit` es el único bounded context con duplicación real hoy. Se
migra primero porque:

1. Es el único caso donde un mismo nombre vive en dos carpetas.
2. La lógica es pequeña (un `service.py` de 15 líneas y un
   `routes.py` de 27 líneas).
3. Sirve para validar el patrón antes de aplicarlo a bounded
   contexts más grandes.

Resultado de la migración:

- `src/app/modules/audit/service.py` ahora expone
  `recent_activity()` (antes solo `module_status()`).
- `src/app/modules/audit/routes.py` ahora sirve `/audit` y
  `/api/audit/activity` (antes solo `/modules/audit/status`).
- `src/app/main.py` deja de importar `audit_router` desde
  `features/audit/routes` y solo monta `modular_audit_router` desde
  `modules/audit/routes`.
- `src/app/features/audit/` queda como archivos orphan (no se
  borran). Si en el futuro se quiere limpiar, será en una fase
  separada con verificación previa de que nadie los importa.

### Reglas para código nuevo

- Cualquier bounded context nuevo va en `src/app/modules/<nombre>/`
  con la convención `routes.py` + `service.py` + `schemas.py` (ver
  §2 de `.opencode/skills/backend-senior/SKILL.md`).
- Si un dev duda entre `features/X` y `modules/X`, la respuesta
  siempre es `modules/X`.
- Las migraciones desde `features/` siguen Strangler Fig: el viejo
  router se desmonta **solo cuando** el nuevo lleva al menos una
  release en producción y los smoke tests pasan.

## Alternatives Considered

### 1. Eliminar `features/` de inmediato
- **Pros**: estado limpio desde el día uno, sin orphan.
- **Cons**: borra código que aún está importado por otros
  `features/*` (catalogs importa de quality, etc., ver
  `src/app/features/catalogs/service.py:1-15`); riesgo de regresión
  silenciosa. **Rechazado** por la restricción del usuario de no
  eliminar en esta fase.

### 2. Declarar `features/` canónica
- **Pros**: no requiere migrar nada, todo sigue donde está.
- **Cons**: contradice `docs/ga03/arquitectura_modular_integraciones.md`
  y la intención de la GA03. La duplicación conceptual crece.
  **Rechazado** porque es exactamente el problema que GA03 intentó
  resolver.

### 3. Strangler Fig sin ADR
- **Pros**: menos paperwork.
- **Cons**: el siguiente dev no sabría que `modules/` es
  canónico sin leer la conversación. **Rechazado**: la decisión
  tiene que quedar escrita para que sobreviva a las rotaciones
  de equipo.

## Consequences

### Positive
- Decisión explícita y documentada: nuevo código va a `modules/`.
- Una sola ruta canónica para cada URL (`/audit`,
  `/api/audit/activity`).
- `features/` queda como legacy identificable, no como confusión
  silenciosa.
- El piloto `audit` establece el patrón para migrar otros bounded
  contexts (e.g. `dashboard`, `quality`) en fases futuras.

### Negative
- `src/app/features/audit/` queda como orphan (no borrado). Si
  alguien hace `import src.app.features.audit` por copy-paste de
  código antiguo, va a funcionar pero no estará montado.
  **Mitigación**: nota visible en
  `docs/ga03/arquitectura_modular_integraciones.md` (ya añadida
  en Phase 12.3.2).
- El smoke test manual debe confirmar `/audit` y
  `/api/audit/activity` siguen devolviendo HTML y JSON
  respectivamente tras la migración. Si no, hay regresión
  silenciosa porque ningún test automatizado las cubre hoy.

### Risks
- **Riesgo**: que el piloto `audit` no se haga y se acumulen
  bounded contexts en `features/`. **Mitigación**: Phase 9 ya
  dejó cobertura de regresión para el wiring (`test_auth.py`,
  `test_middleware.py`); un health check `GET /audit` se puede
  añadir en una fase posterior.
- **Riesgo**: que una migración futura (e.g. `dashboard`) rompa
  dependencias entre `features/*`. **Mitigación**: hacer un mapa
  de imports entre features antes de cada migración; el patrón
  Strangler Fig exige tener la nueva ruta validada antes de
  desconectar la vieja.

## References
- `docs/refactor-checklist.md` Phase 2 (este ADR es la decisión
  que la checklist pedía)
- `docs/ga03/arquitectura_modular_integraciones.md` (declaración
  original de la estructura `modules/`)
- `docs/handoff-2026-06-02.md` (múltiples agentes tocando el
  repo, hace falta un ADR para que la decisión sobreviva)
- `docs/adr/0001-modular-monolith.md` (decisión de fondo: un solo
  proceso, varios bounded contexts)
- `.opencode/skills/arquitectura-software-senior/SKILL.md`
  (sección "Migration Path (Monolith → Microservices)" — Strangler
  Fig)
