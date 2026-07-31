# ADR-0002 — Poach selectivo de `fastapi-patterns` desde ECC (con adaptación HotelData)

> **Estado**: proposed
> **Fecha**: 2026-07-28
> **Owner**: `admin_sistema` (con revisión de `auditor_datos` post-MVP)
> **Resuelve**: la ausencia de un skill institucional que encode las reglas Pydantic v2 / MongoDB wire-shape / dual-write / Airflow-boundary del proyecto,فرشاد которых previene recurrencia de bugs documentados en `knowledge.md`.

## Contexto

### El problema

HotelData Hub tiene reglas arquitectónicas altamente específicas que previenen cinco clases de bugs ya documentados en `knowledge.md`:

1. **PydanticUserError / `TypeAdapter not fully defined`** — cuando `from __future__ import annotations` + `response_model=` + `ObjectIdStr` (un `Annotated[str, BeforeValidator(...)]` forward-ref) coinciden sin la combinación de `model_rebuild()` + banner-separation + `populate_by_name=True`.
2. **`PydanticUndefinedAnnotation`** cuando el banner `# ─── Section ───` se colapsa con `class X(BaseModel):` en el mismo renglón (todo después de `#` es comentario, la clase queda fuera del módulo, el rebuild explícito encuentra `name 'X' is not defined`).
3. **`str(x['_id'])` callsites** dispersos (~50 restantes en `instay/`, `reservations/`, `billing/`, `expenses/`, `hr/`, `auth/`, `admin/`) que pertenecen al patrón pre-`Pydantic v2 *Response`. Migrarlos a un helper genérico (e.g. `to_id_str()`) fue explícitamente revertido por el usuario en 2026-Q2; el camino correcto es llevar cada módulo al patrón canónico de `partner/routes/` (hotel_products + hotels). Un skill institucional acelera esa migración.
4. **Stale `__pycache__`** después de borrar / mutar `*Response` Pydantic classes. El importador de Python carga `.pyc` desde el boot anterior; sin el `find ... -exec rm ... + && docker compose restart server` ritual, ImportError fantasma en runtime.
5. **DAG boundary creep** — un DAG que importe `src.app`, FastAPI, HTML, CSS, JS rompe `§II` sin warning visible (cuesta detectarlo hasta que el ETL crashea en staging).

Estas reglas viven hoy dispersas en `knowledge.md`, `constitution.md`, el cache-clear ritual documentado en `knowledge.md` §API convention, y el commit-message lore del repo. NO existe un artefacto ejecutable que un LLM / humano pueda **invocar** para validar automáticamente que un nuevo route cumple las 5 reglas simultáneamente. Friction al onboard + riesgo de regresión silenciosa.

### El repo encontrado

El usuario descubrió `https://github.com/affaan-m/ECC` (MIT-licensed, single-maintainer, weekly ship). Investigación reveló:
- **281 skills** en formato Markdown + 9 `%  .py` Python helpers con `requires-python = ">=3.11"` — **compatible con nuestro Python 3.12.5**.
- `fastapi-patterns` (15.5 KB, frontend-aligned con nuestro stack: Pydantic v2 + pytest-asyncio + httpx ASGITransport + async service layer + dependency injection). **Top match** para el problema arriba.
- **Freebuff NO está en la lista de adapters first-class** de ECC (que cubren Claude Code, Codex, Cursor, OpenCode, Gemini, Zed, Copilot, Antigravity, Qwen, Hermes, OpenClaw, Kimi, CodeBuddy, JoyCode). El repo de Freebuff cae en la categoría *"manual adaptation guide"* — implica que la integración pierde hooks runtime, slash commands nativas, y plugin marketplace. Friction Alta.

### Por qué ahora

Porque la próxima vez que aparezca un PydanticUserError post-deploy (probabilidad ≥ 1 por mes, según historial), queremos que el skill esté disponible como defensa — no como reacción post-mortem. Instalar ECC completo es reject-able por: (a) Freebuff sin adapter nativo, (b) vendor lock-in a un single maintainer, (c) name-clash con `.specify/`, (d) abandono-riesgo si el maintainer deja el proyecto. **Poach selectivo** evita los cuatro riesgos y obtiene ~70% del valor del skill con 0% del lock-in.

### Constraints heredados

- **§14.1 jerarquía**: Constitución > ADRs > Specs > knowledge.md > AGENTS.md. Este ADR no modifica la Constitución ni la contradice; la respeta y la codifica en formato ejecutable.
- **§III Normalización Multi-Propiedad** + **§VII Operacional-First**: el skill cubre la wire shape del dual-write operational↔analytical — el heart del dominio hotelero. Si ECC no tuviera un skill específico para FastAPI, hubiéramos construído uno desde cero con la misma profundidad.
- **§II Airflow↔Web**: la sección F+G del skill codifica la regla de no-import-`src.app` en DAGs. Sin skill, depende de que cada developer sepa leer `test_dag_boundaries.py` antes de mergear un DAG.
- **§IX Airflow-Web boundary**: secciones F+G+H refuerzan.
- **§Docker Safety Rules (knowledge.md)**: la sección Best Practices cita la regla; el skill la convierte en defense-in-depth para code reviewers automatizados.

## Decisión

**Poachar selectivamente el skill `fastapi-patterns` de ECC (MIT-licensed de affaan-m) bajo el path `.agents/skills/fastapi-patterns/skill.md` con adaptación HotelData-specific que reemplaza las secciones genéricas por las 5 reglas duras del proyecto, registrar la entrada en `.agents/skills.json`, y NO instalar ECC como sistema.**

Declarativo:
- **MUST** mantener atribución a ECC en el frontmatter `metadata.origin: ecc` + link al origin repo + nota de license MIT.
- **MUST** adaptar (no copiar literal) cada sección genérica de ECC para inyectar las reglas HotelData-specific. El skill resultante es **un artefacto HotelData, no un port verbatim de ECC**.
- **MUST** actualizar `.agents/skills.json` para que Freebuff descubra el directorio `./skills` (relative a `.agents/skills.json`).
- **MUST** NO instalar el resto de ECC (los otros 280 skills, los 67 agents, los 94 commands, la hook runtime, el marketplace plugin). Solo este skill.
- **SHOULD** mantener una "Future ADR-000X consideration" que documente cuándo conviene reconsiderar la integración full-stack de ECC (e.g. si Freebuff gana adapter nativo en upstream).
- **SHOULD** propagar el patrón de poach a los otros 9 skills top-tier identificados en el triage previo (`angular-developer`, `architecture-decision-records`, `recursive-decision-ledger`, `python-testing`, `knowledge-ops`, `backend-patterns`, `frontend-patterns`, `database-migrations`, `contract-first`) — uno por uno, con su propio ADR.

Alineación con §3 (Principios):
- §I Python-First: el skill codifica reglas FastAPI/MongoDB Python puro.
- §II Airflow↔Web: sección F+G enforza la separación.
- §V Evidencia: este ADR documenta el cambio propuesto.
- §VII Operacional-First: sección E (dual-write inventory) cubre el caso.
- §14.4 Cadencia Trimestral: el siguiente auto-audit (trimestre siguiente) verificará que el skill esté actualizado a Constitución vigente.

## Consecuencias

### Positivas

- **Trazabilidad del origen**: el frontmatter metadata linkea el skill a ECC + al ADR. Cualquier developer que toque el skill sabe exactamente de dónde viene y por qué existe.
- **Defensa automatizada**: cuando un LLM (Freebuff u otro) analice un nuevo PR que toca `routes/`, debe invocar este skill para validar que cumple §A (wire shape), §B (banner separation), §C (ObjectIdStr), §D (cache-clear).
- **Reducción de bugs recurrentes**: los 5 bugs del problema de arriba pasan de "discovery en producción" a "prevención en pre-commit". Estimación conservadora: 1 incidente prevenido por mes vale más que el costo de authoring (~3 horas).
- **Idempotente**: si el maintainer de ECC desaparece, el skill sigue funcionando porque es texto auto-contenido en HotelData.
- **Onboarding acelerado**: nuevos developers descubren el skill leyendo `.agents/skills/fastapi-patterns/skill.md` cuando les toca su primer endpoint.
- **Frontera clara con `.specify`**: el skill es ejecución, no governance. La Constitución sigue siendo ruler of rulers. No hay conflicto.

### Negativas (trade-offs aceptados)

- **Drift risk vs upstream**: si ECC actualiza `fastapi-patterns` upstream con patrones nuevos (e.g. Pydantic v3 cuando salga), nuestro fork queda desincronizado. Mitigación: el campo `metadata.adapted: 2026-07-28` en frontmatter + cláusula SHOULD de refresh trimestral.
- **Skill sprawl**: poachar 10 skills produce 10 archivos Markdown que mantener. No es trivial. Pero cada uno resuelve un problema distinto; trade-off aceptado.
- **Authoring tax**: este ADR + el skill combinado son ~700 líneas de Markdown. Tiempo invertido: ~3 horas. Recuperación esperada: ~1 mes por incidente prevenido.
- **Naming `ecc-` no aplicado**: si más adelante decidimos evolucionar a un namespace propio (e.g. `hoteldatas-` o `.agents/skills/<domain>/<skill>.md`), el path actual necesitaría refactor. Mantenerlo bajo `.agents/skills/<skill>/skill.md` minimiza el costo del refactor.

### Riesgos conocidos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| **Frontmatter metadata incompleto** (e.g. olvidar `origin` link) | Media | Code review del ADR verifica frontmatter + smoke test del path |
| **Attribution loss al copiar el skill** | Baja | El skill lleva frontmatter `metadata.origin: ecc` + nota en línea 1 + sección "Origen" prominente |
| **Adaptación diluida** (i.e. copy-verbatim ECC con renames en lugar de reescritura genuina) | Media | El ADR §Decisión MUST "adaptar (no copiar literal)". Code reviewer verifica |
| **Freebuff no carga el skill** porque path está mal en `.agents/skills.json` | Baja | Smoke test post-merge: invocar el skill en una conversación real |
| **Conflicto con `.specify/` governance** (i.e. alguien asume que el skill reemplaza la Constitución) | Baja | El §14.1 ya establece la jerarquía; este ADR repite que es ejecución, no governance |
| **ECC uptake rota el skill** (hyper-rare: ECC hace breaking change a fastapi-patterns upstream) | Muy baja | El skill es copy local; ignorar upstream hasta re-evaluación |

## Alternativas Consideradas

### Alternativa A — Instalar ECC como sistema completo ❌

Easy install per el README: `/plugin marketplace add` + `/plugin install ecc@ecc`. Profit inmediato: 67 agents + 281 skills + 94 commands + AgentShield + continuous learning + hook runtime + memory subsystem.

**Rechazada** porque:
1. **Freebuff no es adapter target first-class.** Caemos en *"manual adaptation guide"* sin hooks, sin marketplace, sin slash commands nativas, sin skill discovery nativa. Friction Alta, valor 60% menos del claim.
2. **Vendor lock-in a un solo maintainer** ("a single maintainer ships weekly across 7 harnesses"). Si affaan-m deja el proyecto, todo el tooling queda sin owner. Alto para un proyecto cuyo negocio es hotelero (24/7 ops).
3. **Conflicto de governance con `.specify/`.** ECC trae `rules/common`, `rules/typescript` que pretenderían autoridad sobre AGENTS.md y Constitution v0.9. La jerarquía del proyecto (§14.1) rechaza implícitamente esta colisión. Installer detecta y aborta, o silenciosamente dobla — ambos outcomes malos.
4. **Name pollution.** ECC prepende `ecc-` a todo, lo que entraría en conflicto con el naming taxonomy del dominio HotelData (`hotels`, `reservations`, `billing`, `housekeeping`, etc.).

### Alternativa B — Cherry-pick sin documentar (i.e. pegar el skill inline en un comentario de un routes file) ❌

Costo: ~5 minutos. Sin ADR, sin trace.

**Rechazada** porque:
1. Invisible al próximo developer. Si el skill cambia, nadie encuentra el origen.
2. No cumple §V (Evidencia + matriz de trazabilidad).
3. Imposible de actualizar canónicamente.
4. No es actionable para otro LLM que no sea el que lo pegó inline.

### Alternativa C — Status quo: no poachear, dejar que el conocimiento se mantenga en knowledge.md ⚠️

Costo: 0. Profit: el skill nunca existe; los 5 bugs siguen apareciendo en producción.

**Rechazada** porque el costo acumulativo de un PydanticUserError post-deploy (debugging + rollback + post-mortem + commit fix + customer trust erosion) excede por mucho el costo de authoring del skill. La fricción pre-commit es estrictamente menor que el costo post-incident.

## Compliance

- [x] **§I Python-First**: el skill codifica reglas Python (Pydantic v2 + FastAPI + MongoDB). Sin `BashOperator` introducido.
- [x] **§II Airflow↔Web**: secciones F+G+H enforza la separación. Ningún import `src.app` recomendado en DAGs. Test boundary (`test_dag_boundaries.py`) sigue siendo la enforcement layer; el skill es documentation complementaria.
- [x] **§V Evidencia + trazabilidad**: este ADR documenta el cambio; el `.kiro/steering` o equivalente debe mapear spec→ADR y ADR→skill. Frontmatter metadata del skill linka al ADR.
- [x] **§VII Operacional-First**: sección E cubre dual-write inventory con pipelined `update_one`. Warum not skipped.
- [x] **§5 Service Catalog**: el skill es un artefacto de policy, no de servicio. n/a.
- [x] **§9 Performance Budget**: el skill no introduce dependencias nuevas (FastAPI + Pydantic v2 ya están en el stack). Cero impacto en bundle.
- [x] **§14.4 Cadencia Trimestral**: el siguiente auto-audit verificará que el skill esté sincronizado con Constitución + ADRs vigentes.
- [x] **§14.5 ADRs planificados**: este ADR llena un slot del backlog (ADR-0002 era pendiente). Reduce el # de ADRs pendientes por 1.

## Notas de Migración

### Pre-Migración (qué hacer DESPUÉS de mergear este ADR)

1. **Smoke test post-merge**:
   ```bash
   cd /c/HotelData/hoteldata_project
   # Verify skill file is at the expected path
   ls -la .agents/skills/fastapi-patterns/skill.md
   # Verify skills.json has the new entry
   cat .agents/skills.json
   # Verify ECC attribution preserved in metadata frontmatter
   head -10 .agents/skills/fastapi-patterns/skill.md
   # Smoke-test that pyenv can parse (no syntax error)
   python -c "import sys; sys.path.insert(0, '.'); from pathlib import Path; print(Path('.agents/skills/fastapi-patterns/skill.md').read_text()[:200])"
   ```

2. **Verify pytest-of-the-target-endpoint passes** con el skill aplicado mentalmente:
   ```bash
   docker compose -f infra/docker-compose.yml exec -T server \
     python -m pytest -q server/tests/test_reservations.py -k "test_get or test_list"
   ```
   Si pasa, el skill refleja correctamente el comportamiento esperado del código. Si falla, el skill está desactualizado.

3. **Update ADR README index** ya está hecho en este mismo PR (ver `.specify/decisions/README.md`).

### Post-Migración (qué hacer en los próximos sprints)

- **Cuando aterrice un nuevo ADR que toque `*Response`** (e.g. ADR-0003, ADR-0004): verificar que `.agents/skills/fastapi-patterns/skill.md` §A/B/C refleje la nueva regla. Si difiere, sincronizar en el mismo PR.
- **Cuando aparezca un nuevo PydanticUserError en producción**: el incidente root-cause debería matchear una sección de este skill. Si NO matchea, agregar la lección al skill + ADR.
- **Trimestral (auto-audit §14.4)**: comparar upstream ECC `fastapi-patterns` contra nuestra versión. Si upstream tiene avances materiales (e.g. Pydantic v3 support), proponer PR de refresh.
- **Propagar pattern a los otros 9 skills poach-worthy** (`angular-developer`, `recursive-decision-ledger`, `python-testing`, etc.) con su propio ADR-000X. NO bundlear todos en un solo mega-ADR (cada uno tiene contexto distinto).

### Rollback (cómo deshacer si fuera necesario)

1. `git revert <merge-commit>` del PR de este ADR.
2. Borrar `.agents/skills/fastapi-patterns/skill.md`.
3. Revertir `.agents/skills.json` a su estado pre-ADR (solo `{ "path": "../.opencode/skills" }`).
4. Revertir `.specify/decisions/README.md` (remove ADR-0002 row).
5. NO requiere cleanup de Docker / MongoDB — el skill es Markdown, no runtime.
6. Smoke test post-rollback: pytest contra `/api/reservations/` debe pasar idéntico al pre-ADR-0002 baseline.

## Cross-References

- **Plantilla**: `.specify/decisions/ADR-0000-template.md` (este ADR es fiel al template).
- **Predecesor reciente**: `.specify/decisions/ADR-0001-mongo-7-to-8-migration.md` (el primer ADR real; este ADR-0002 es el segundo).
- **Constitutional**: `.specify/memory/constitution.md` §3.V (Evidencia), §5.1 (decimal catalog), §I/§II/§V/§VII/§14.4/§14.5.
- **Operativo**: `knowledge.md` §API convention + §Docker Safety Rules + §Cache-clear ritual.
- **Skill artefact**: `.agents/skills/fastapi-patterns/skill.md` (artefacto principal del ADR; version 1.0, dated 2026-07-28).
- **Origen upstream**: `https://github.com/affaan-m/ECC/tree/main/skills/fastapi-patterns` (MIT-licensed, adaptation 2026-07-28).
- **Skills registry**: `.agents/skills.json` (entrada `{ "path": "./skills" }` añadida por este ADR).
- **Future ADRs**: ADR-0003 (candidatos: poach `angular-developer` / `recursive-decision-ledger` / otros top-9 del triage).

---

**Versión**: 1.0 | **Ratificada**: 2026-07-28 (proposed hasta review) | **Próximo review gate**: cuando se proponga poach de cualquier otro skill ECC (cada uno con su propio ADR-NNNN)
