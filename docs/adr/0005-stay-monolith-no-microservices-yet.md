# ADR-0005: Quedarse en Monolito Modular (no extraer a microservicios)

## Status
Accepted

## Date
2026-06-06

## Revisar
Q-1 de 2027 (o antes si aparece uno de los disparadores abajo)

## Context
- El proyecto es un monolito modular FastAPI + Angular + MongoDB
  (ver ADR-0001).
- La pregunta recurrente cuando se añade un bounded context: ¿lo
  extraemos como servicio independiente?
- Hoy: 1 equipo, < 10 devs, deploys coordinados, ACID multi-doc
  necesario para reservas.

## Decision
**No extraer.** Mantener el monolito modular mientras se cumplan
todas estas condiciones:

1. **Un solo equipo** mantiene el backend.
2. **ACID multi-doc** sigue siendo requisito (reservas, inventario,
   pagos).
3. **El proceso aguanta el RPS** (regla práctica: < 500 RPS sostenidos).
4. **El deploy del monolito se puede hacer en < 1 release cycle**
   (regla práctica: < 30 min de CI/CD + smoke tests).
5. **Ningún bounded context** tiene un SLA materialmente distinto del
   resto (ej. "este debe responder en 50ms p99", "este tiene picos
   100x sobre la media").

Si alguna de estas cambia, **se re-evalúa** este ADR y se considera
extracción vía **Strangler Fig pattern**.

## Disparadores de re-evaluación

Si pasa CUALQUIERA de estos, abrir un nuevo ADR proponiendo
extracción:

- [ ] El equipo de backend se divide en ≥ 2 squads con prioridades
      independientes.
- [ ] Un bounded context (probablemente `partner` o `revenue`) tiene
      un SLA p99 < 100ms mientras el resto está en p99 < 500ms.
- [ ] El RPS sostenido del proceso supera 500 en horas pico.
- [ ] Un bounded context necesita escalar a 10x del resto
      (probablemente `hotels` search).
- [ ] El CI/CD del monolito supera 30 min y se vuelve cuello de
      botella.

## Alternatives Considered

### Extraer `partner` ya
- **Pros**: `partner` es el más grande (1600+ líneas pre-refactor) y
  tiene su propio ciclo de release.
- **Cons**: extraído se vuelve 1 repo + 1 deploy pipeline + 1 tracing
  distribuido, para servir a 1 consumidor interno (Angular). No
  compensa hoy.
- **Why not**: dispara la regla 1 (mismo equipo) y la regla 5 (sin SLA
  distinto).

### Extraer `revenue` (analytics)
- **Pros**: `revenue` es read-heavy, candidato natural a escalar
  aparte.
- **Cons**: necesita `fact_hotel_reservations` y `dim_hotels` que
  están en el mismo Mongo del monolito. O se replica el dato (eventual
  consistency) o se comparte la BD (que frustra el punto).
- **Why not**: no resuelve el problema y añade complejidad.

## Consequences

### Positive
- Cero overhead operacional de servicios.
- ACID gratis, debugging simple, deploy simple.
- Refactors cross-context siguen siendo búsquedas y reemplazos.

### Negative
- **Acoplamiento accidental**: es fácil que un bounded context importe
  de otro sin que se note. La regla §13.3 de
  `.opencode/skills/backend-senior/SKILL.md` y el code review lo mitigan.
- **Una caída del proceso = caída de todo**. Mitigación: health checks,
  restart policies, `readinessProbe`/Kubernetes si se migrara.
- **Escalar = escalar el proceso entero**. Aceptable hasta el umbral
  del disparador 3.

### Risks
- **Riesgo**: que se re-infle el monolito y la decisión de "no
  extraer" se use como excusa para no seccionar.
  **Mitigación**: el refactor-checklist (Phase 1 ya hecho, Phase 2
  pendiente) y la skill `backend-senior` §13 imponen la disciplina
  de sub-dominios.
- **Riesgo**: que un bounded context empiece a doler y no se re-evalúe
  este ADR a tiempo.
  **Mitigación**: los disparadores están escritos. Cualquier dev puede
  abrirlos y proponer extracción.

## Cómo se ejecutaría la extracción si se aprueba

Strangler Fig pattern (ver
`.opencode/skills/arquitectura-software-senior/SKILL.md`):

1. **Phase 1**: el bounded context vive en el monolito con interfaz
   limpia (ya está, gracias al refactor de Phase 1).
2. **Phase 2**: extraer como servicio independiente. Nginx / API
   Gateway redirige tráfico al nuevo servicio.
3. **Phase 3**: añadir event bus entre el servicio extraído y el
   monolito restante para los eventos cross-context.
4. **Phase 4**: deploys independientes, CI/CD por servicio, tracing
   distribuido.

## References
- ADR-0001 (modular monolith — la base de esta decisión)
- `.opencode/skills/arquitectura-software-senior/SKILL.md` (decision
  framework monolith vs microservices + Strangler Fig)
- `docs/refactor-checklist.md` (Phase 1 done; las siguientes fases
  mejoran la "interfaz limpia" que necesitaríamos para extraer)
