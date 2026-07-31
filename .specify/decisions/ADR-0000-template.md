# ADR-0000 — Template de Architecture Decision Record

> **Estado**: accepted | **Fecha**: 2026-07-28 | **Owner**: `admin_sistema`

## Contexto

HotelData Hub adoptó desde la versión constitucional v0.9 (julio 2026) un modelo de gobierno de decisiones arquitectónicas vía ADRs. Este archivo documenta la plantilla canónica que se replica cada vez que se propone una nueva decisión.

La Convención Constitucional §14.1 establece la jerarquía: Constitución > ADRs > Specs > `knowledge.md` > `AGENTS.md`. Los ADRs son el artefacto de gobierno entre la Constitución y los specs que materializan sus principios.

## Decisión

Adoptar la siguiente plantilla como formato canónico de ADR en este repositorio.

### Formato Obligatorio

Cada ADR **debe** contener las siguientes secciones en este orden:

```md
# ADR-NNNN — Título descriptivo (corto, específico, accionable)

> **Estado**: proposed | accepted | deprecated | superseded-by-ADR-NNNN
> **Fecha**: YYYY-MM-DD
> **Owner**: role system
> **Decisión bajo revisión**: ADR-NNNN (si supersede)

## Contexto
- ¿Qué problema estamos resolviendo o qué elección arquitectónica estamos tomando?
- ¿Qué fuerzas están en juego? (hoteleras: propiedad multi-grupo, ops 24/7, dual-write, normalización multi-PMS)
- ¿Qué constraints vienen de la Constitución o specs vigentes?

## Decisión
- ¿Qué decidimos hacer? (declarativo, MUST/SHALL/NEVER)
- ¿Cómo se alinea con §3 (Principios) de la Constitución?

## Consecuencias
### Positivas
- ...

### Negativas (trade-offs aceptados)
- ...

### Riesgos conocidos
- ...

## Alternativas Consideradas
- **Alternativa A**: ... por qué rechazada
- **Alternativa B**: ... por qué rechazada
- (Cero alternativas = mal ADR — siempre existe al menos una alternativa)

## Compliance
- [ ] ¿Cumple §I (Python-First)?
- [ ] ¿Cumple §II (Airflow-Web boundary)?
- [ ] ¿Cumple §VII (Operational-First + Dual-Write cuando aplique)?
- [ ] ¿Impacta algún `data_*` o `*Response` migrada? (ver knowledge.md §API convention)
- [ ] ¿Performance Budget §9 sigue cumpliéndose?

## Notas de Migración (si aplica)
- Pasos concretos para migrar consumidores downstream.
- Lista de archivos que cambian.
- Plan de rollback.

## Cross-References
- Spec afectada: `.specify/specs/.../spec.md`
- ADR relacionada: ADR-NNNN (si supersede)
- Conocimiento operativo: `knowledge.md` §<sección>
```

## Consecuencias

### Positivas

- **Trazabilidad**: cada decisión arquitectónica tiene fecha, owner, contexto y consecuencias documentadas.
- **Anti-drift**: nuevas decisiones deben justificar compatibilidad con la Constitución y principios vigentes.
- **Onboarding**: nuevos agentes (LLM o humanos) pueden leer los ADRs en orden cronológico para entender el _por qué_ de la arquitectura.
- **Reemplazo disciplinado**: una decisión deprecada nunca se borra — queda como superseded-by link al nuevo ADR.

### Negativas

- **Costo cognitivo**: cada decisión requiere estructurar contexto + alternativas + consecuencias. Es más lento que un commit ad-hoc.
- **Riesgo de rigidez**: si se abusa, se puede volver un blocker ceremonies-over-output.

### Riesgos

- **ADRs obsoletos**: si el owner deja el proyecto y nadie los mantiene, se vuelven ruido. Mitigación: owner debe declarar sucesor en el campo `Owner` y actualizar cuando cambie.

## Alternativas Consideradas

- **No documentar decisiones**: status quo pre-v0.9. **Rechazada** porque producía drift arquitectónico (ej. `docker-compose.airflow3.yml` legacy sin justificar).
- **ADRs como Markdown libre sin plantilla**: rechazada por falta de compliance con Constitución.
- **Wikis externas (Notion, Confluence)**: rechazada por fragmentar el source-of-truth; deben vivir en git junto al código.

## Compliance

- [x] §I Python-First (n/a — governance doc, no ETL code)
- [x] §II Airflow-Web boundary (n/a)
- [x] §VII Operacional-First (n/a — meta-governance)
- [x] §5 Service Catalog (n/a)
- [x] §9 Performance Budget (n/a)

## Cross-References

- `.specify/memory/constitution.md` §13 (cascada), §14.1 (jerarquía), §14.5 (ADRs pendientes).
- `knowledge.md` (referencias operativas, no decisiones arquitectónicas).
