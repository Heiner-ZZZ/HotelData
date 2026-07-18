# HotelData - Refactor Checklist

Lista viva de tareas de refactor arquitectónico, organizadas por fase.
Las casillas se marcan con `[x]` cuando la tarea está completada y verificada.

Convenciones:
- Cada fase es independiente. Si hay que pausar, se pausa entre fases.
- Toda tarea completada debe incluir verificación (test, import, hit a un endpoint).
- Las dependencias entre tareas se indican en la línea "Bloquea" / "Bloqueada por".

---

## Phase 1 - Sectioning del god class `partner/service.py`

> **Contexto**: `src/app/modules/partner/service.py` tiene 1834 líneas y 5
> sub-dominios mezclados. Esta fase lo parte en una carpeta `services/` con
> un archivo por sub-dominio, y arregla los imports de los 6 callers externos.

- [x] Crear `services/_common.py` con utilidades compartidas (formato, parseo,
      fact collection, register change). Sin dependencias de otros sub-módulos
      del paquete.
- [x] Crear `services/bootstrap.py` con `module_status` y los 4 `ensure_*_collections`.
- [x] Crear `services/properties.py` con `list_partner_hotels`,
      `partner_hotel_detail`, `partner_hotel_performance`,
      `save_partner_hotel_profile` y helpers de formato de perfil.
- [x] Crear `services/content.py` con páginas de contenido, amenidades,
      políticas, imágenes, y los agregados `partner_hotel_content`,
      `partner_hotel_policies`, `partner_hotel_images`,
      `partner_hotel_profile`, `partner_hotel_edit_profile`.
- [x] Crear `services/rooms.py` con rooms, inventory, blackout.
- [x] Crear `services/rates.py` con rate plans, calendar, promotions.
- [x] Crear `services/dashboard.py` con flags operacionales, reports y
      `properties_dashboard`.
- [x] Crear `services/__init__.py` que expone la API pública del paquete.
- [x] Borrar `src/app/modules/partner/service.py`.
- [x] Actualizar imports en `src/app/modules/partner/routes.py` para usar los
      sub-módulos de `services/`.
- [x] Actualizar imports en `src/app/modules/reservations/service.py`
      (`partner_hotel_detail`, `partner_hotel_policies`).
- [x] Actualizar import lazy en `src/app/modules/revenue/routes.py`
      (`list_partner_hotels`).
- [x] Actualizar imports en `scripts/init_inventory_ga03.py`.
- [x] Actualizar imports en `scripts/init_hotel_content_ga03.py`.
- [x] Actualizar imports en `scripts/validate_ga03_inventory.py`.
- [x] Actualizar imports en `scripts/validate_ga03_hotel_content.py`.
- [x] Verificar: `python -c "import src.app.main"` no lanza excepciones.
- [x] Verificar: `python -m pytest -q` corre los tests existentes sin romper.
- [x] Verificar: importar `from src.app.modules.partner.services.properties
      import list_partner_hotels` resuelve.

**Estado Phase 1: COMPLETADA**

---

## Tier 1 - Calentar motores (Phase 7 + 8 + 11)

> **Contexto**: tres cambios pequeños y aislados que no tocan lógica,
> solo deprecations y documentación. Riesgo ≈ 0. Preparan el terreno
> para los refactors del Tier 2/3.

- [x] **Phase 7** — Reemplazar `@app.on_event("startup")` por
      `lifespan` async context manager en `src/app/main.py`.
      Verificado: `python -m pytest -q` 11/11 verde.
- [x] **Phase 8** — Crear `docs/adr/README.md` (índice).
- [x] **Phase 8** — `docs/adr/0001-modular-monolith.md`.
- [x] **Phase 8** — `docs/adr/0002-dual-database-mongo-pocketbase.md`.
- [x] **Phase 8** — `docs/adr/0003-cookie-session-in-mongodb.md`.
- [x] **Phase 8** — `docs/adr/0004-jinja-to-angular-migration.md`.
- [x] **Phase 11** — `docs/adr/0005-stay-monolith-no-microservices-yet.md`
      (decisión Strangler Fig: no extraer todavía; disparadores
      documentados).

**Estado Tier 1: COMPLETADO**

---## Phase 2 - Decidir jerarquía: `modules/` vs `features/` ✅

> **Contexto**: existen dos jerarquías paralelas en `src/app/`. `audit`
> existe en ambas. `main.py` monta routers de las dos. Bloquea cualquier
> refactor posterior de sub-módulos.

- [x] Decidir canónica: **`modules/`** gana. Ver
      `docs/adr/0006-canonical-hierarchy-modules-wins.md`.
- [x] Auditar funciones duplicadas: solo `audit` tiene archivos en
      ambas jerarquías hoy. Los demás `features/*` no colisionan
      en URL con ningún `modules/*`, pero la duplicación conceptual
      queda como legacy identificable.
- [x] Migrar `audit` como piloto: `features/audit/service.py` y
      `routes.py` se移植aron a `modules/audit/`. `main.py` ahora
      solo importa `audit_router` desde `modules/audit/routes`.
      `features/audit/` queda como archivos orphan (no eliminados
      per restricción del usuario).
- [x] Verificar: `python -c "import src.app.main"` + `pytest -q`
      → 39/39 verde.
- [x] Añadir `tests/test_audit_migration.py` con 4 smoke tests
      que blindan la migración: `/audit` se sirve, no hay
      duplicación de rutas, las 3 rutas (`/audit`,
      `/api/audit/activity`, `/modules/audit/status`) vienen
      exclusivamente de `src.app.modules.audit.routes`.

**Bloquea:** Phase 3, Phase 4, Phase 6 (afectan a `modules/*`).

---

## Phase 3 - ACL declarativo por `Depends()` en lugar de string-prefix central

> **Veredicto (2026-06-06)**: **NO PROCEDE**. Ver análisis abajo.
> Re-evaluar si aparece un ACL bug real en el futuro.

### Por qué no se aplica

1. **`require_permission` ya existe** y se usa en
   `src/app/modules/admin/routes.py` (10 ocurrencias). El Enum
   propuesto es cosmético: 11 permission codes en strings es
   perfectamente manejable y buscable.
2. **El middleware es red de seguridad**, no fragilidad. El
   `get_access_rule` por defecto cierra el acceso a cualquier ruta
   no listada explícitamente (`AccessRule(path, roles=("super_admin",
   "admin_sistema"))`). Quitar `ROUTE_RULES` elimina ese default-deny.
3. **El "doble check" middleware + dependency es defensa en
   profundidad**, no bug. El middleware filtra por prefijo/método y
   la dependency valida el permiso fino. Las dos capas se
   complementan.
4. **No hay ACL bug real reportado** en `docs/handoff-2026-06-02.md`
   ni en los docs de GA03. La "fragilidad" del checklist original
   era genérica, no basada en código de este repo.
5. El handoff (líneas 287-302) confirma que añadir una regla a
   `ROUTE_RULES` es el patrón establecido cuando se monta un nuevo
   endpoint admin.

### Deuda real encontrada y arreglada (subset de Phase 3)

- [x] Formatting typo en `route_permissions.py:27` — dos
      `AccessRule` en la misma línea. Reemplazado por una entrada
      por línea. No cambia comportamiento.

---

## Phase 4 - Repository pattern en `src/database/`

> **Contexto**: ~130 llamadas a `get_database()` esparcidas por los services.
> El acoplamiento a `pymongo` impide testear sin Mongo y migrar a otro motor.

- [ ] Auditar las ~15 colecciones que usan los services
      (`users`, `hotels`, `dim_hotels`, `dim_destinations`, `dim_visitor_countries`,
      `fact_hotel_reservations`, `fact_hotel_events`, `room_types`,
      `hotel_rooms`, `room_inventory_calendar`, `room_availability_blocks`,
      `blackout_dates`, `rate_plans`, `hotel_rate_calendar`, `rate_rules`,
      `promotion_campaigns`, `coupon_codes`, `hotel_content_pages`,
      `hotel_images`, `hotel_policies`, `hotel_content_changes`,
      `hotel_profile_changes`, `booking_orders`, `data_quality_reports`,
      `system_catalogs`).
- [ ] Definir interfaces en `src/database/repositories.py` (un Protocol por
      colección con los métodos que usan los services).
- [ ] Implementar `MongoXxxRepository` para cada Protocol.
- [ ] Inyectar repos via `Depends()` en los services (no más
      `get_database()` directo).
- [ ] Tests: repositorios con `mongomock` o testcontainers.

**Bloqueada por:** Phase 1, Phase 2.

---

## Phase 5 - Versionado de API `/api/v1/`

> **Contexto**: no hay versionado. Cualquier cambio breaking rompe al
> frontend Angular y a futuros clientes.

- [ ] Mover todos los routers de `api_router` a prefix `/api/v1`.
- [ ] Mantener `/api/*` re-exportando a `/api/v1/*` durante 1 release
      (deprecation header).
- [ ] Actualizar `frontend/proxy.conf.json` y el `api.config.ts`.
- [ ] Documentar en `docs/api_changelog.md` qué cambió.

**Bloqueada por:** Phase 2.

---

## Phase 6 - CORS estricto desde env ✅

> **Contexto**: `main.py:53-64` tenía orígenes y métodos/headers
> hardcodeados con `*`. Migrado a `config/settings.py` con
> allowlist explícita.

- [x] Mover orígenes, métodos y headers a `config/settings.py` desde
      env (`CORS_ALLOWED_ORIGINS`, `CORS_ALLOWED_METHODS`,
      `CORS_ALLOWED_HEADERS`).
- [x] Reemplazar `allow_methods=["*"]` por allowlist explícita
      (`GET, POST, PUT, PATCH, DELETE, OPTIONS`).
- [x] Reemplazar `allow_headers=["*"]` por allowlist explícita
      (`Authorization, Content-Type, X-Requested-With, Cookie`).
- [x] `tests/test_cors.py`: 5 tests (preflight de origen permitido
      vs rechazado, GET simple no leak CORS a origen prohibido,
      `allow-credentials`, allowlist sin wildcard).
- [x] `python -m pytest -q` → **35/35 verde**, sin regresiones.

**Estado Phase 6: COMPLETADA**

---

## Phase 7 - Lifespan en lugar de `@app.on_event` ✅

> **Contexto**: `main.py:104-107` usa `on_event("startup")`,
> deprecado desde FastAPI 0.99.

- [x] Crear `lifespan(app)` async context manager que llama a
      `ensure_default_catalogs()` y `ensure_user_status_field()`.
- [x] Sustituir `@app.on_event("startup")` por `lifespan=...` en `FastAPI(...)`.
- [x] Verificar: uvicorn arranca, los seeds corren, endpoints responden.

---

## Phase 8 - ADRs (Architecture Decision Records) ✅

> **Contexto**: `docs/arquitectura.md` tiene 5 líneas. Decisiones críticas
> (dual DB, cookie session, monolith) no están documentadas.

- [x] Crear `docs/adr/README.md` (índice).
- [x] Crear `docs/adr/0001-modular-monolith.md`.
- [x] Crear `docs/adr/0002-dual-database-mongo-pocketbase.md`.
- [x] Crear `docs/adr/0003-cookie-session-in-mongodb.md`.
- [x] Crear `docs/adr/0004-jinja-to-angular-migration.md` (la lógica de
      negocio queda en Python; Angular sólo presenta).
- [ ] Crear `docs/adr/0006-permission-string-to-enum.md` (cuando se ejecute
      Phase 3, ADR pendiente).

---

## Phase 9 - Tests del web app ✅ (arranque)

> **Contexto**: `tests/` solo cubre ETL. Cualquier refactor de `src/app/`
> es a ciegas.

- [x] Setup `pytest-asyncio` + `httpx.AsyncClient` (Mongo real en
      `hoteldata_hub_test`, no mongomock — el código usa
      `$cond`/`$facet` que mongomock no soporta).
- [x] `tests/conftest.py` con fixtures: `app`, `client`, `db`,
      `_clean_collections` (autouse), `cliente_user`, `admin_user`,
      helper `login()`.
- [x] `tests/test_auth.py`: login OK / wrong password / unknown user /
      missing fields / me sin y con cookie / logout invalida sesión /
      user inactivo rechazado. **10 tests**.
- [x] `tests/test_middleware.py`: rutas públicas / 401 JSON / redirect a
      login / role 403 / role permitido / root redirige a role-home.
      **9 tests**.
- [x] `requirements.txt` actualizado con `pytest-asyncio` y `httpx`.
- [ ] Tests para `permissions` (rol sin permiso, permiso inexistente).
- [ ] Tests para 1 endpoint de cada sub-dominio (hotels, reservations,
      revenue, partner).
- [ ] Cobertura mínima del 60% en `src/app/`.

**Estado Phase 9 (arranque): 19/19 nuevos tests verde, 30/30 totales.**

**Bloqueada por:** Phase 3, Phase 4.

---

## Phase 10 - Performance / higiene operativa

- [ ] Cachear lookup de sesión en `security/middleware.py` (Redis o
      `functools.lru_cache` con TTL corto).
- [ ] Pool de conexiones Mongo (verificar `maxPoolSize` en `connection.py`).
- [ ] Reducir queries en `list_partner_hotels` (hoy hace 2 queries por hotel:
      `dim_hotels` + `_performance_for_prop` aggregate).
- [ ] Verificar: `EXPLAIN` de las 5 queries más frecuentes con dataset de 300k.

---

## Phase 11 - Romper `modules/partner/` cuando duela ✅

> **Contexto**: hoy `partner` sigue dentro del monolito. Si el equipo
> `partner` crece y necesita deployar aparte, extraer.

- [x] Decidir: **quedarse en monolito modular** (no extraer). Ver
      `docs/adr/0005-stay-monolith-no-microservices-yet.md`.
- [ ] Re-evaluar en Q-1 2027 (o antes si se dispara uno de los 5
      disparadores del ADR-0005).

---

## Apéndice - Hallazgos de la auditoría original

| # | Severidad | Falla | Evidencia |
|---|---|---|---|
| 1 | Alta | Duplicación `modules/` y `features/` | `src/app/main.py:24-25` + `modules/audit` y `features/audit` |
| 2 | Media | Proliferación de routers por módulo | `src/app/main.py:67-103` (37 mounts) |
| 3 | Alta | ACL central frágil | `src/app/security/route_permissions.py:19-83` |
| 4 | Alta | Permisos como strings sueltos | `route_permissions.py:19-61` |
| 5 | Alta | Sin repositorios | ~130 `get_database()` en services |
| 6 | Media | CORS permisivo hardcodeado | `main.py:53-64` |
| 7 | Media | Sin versionado de API | `main.py` (toda la sección `include_router`) |
| 8 | Alta | Sin tests del web | `tests/` solo cubre ETL |
| 9 | Media | Sin ADRs | `docs/arquitectura.md` (5 líneas) |
| 10 | Baja | `@app.on_event("startup")` deprecado | `main.py:104-107` |
| 11 | Media | Dual DB Mongo + PocketBase sin justificación | `docker-compose.yml:32-45` |
| 12 | Media | Auth DB lookup en cada request | `security/middleware.py:36-37` |
| 13 | Alta | God class `partner/service.py` (1834 líneas) | `src/app/modules/partner/service.py` |

---

## Cómo usar este documento

1. Antes de empezar una fase, marca el primer item como `- [~]` (en curso).
2. Cuando termines, márcalo `- [x]` solo si la verificación pasó.
3. Si una fase se bloquea, anota la razón al final de la fase.
4. Si descubres una nueva deuda, agrégala como `Phase N+1` con `- [ ]`.

**Última actualización:** Phase 1, 2, 6, 7, 8, 9, 11, 12 (12.1-12.4)
cerrados. Phase 3 marcada como NO PROCEDE. Pendientes: Phase 4, 5, 10.

---

## Phase 12 - Old-state fixes descubiertos al releer docs/

> **Contexto**: tras las fases 1-11 el proyecto quedó con varios bugs
> pre-existentes y omisiones en el trabajo propio de Phase 9 que no se
> habían detectado al no haber leído la documentación del proyecto
> (`docs/ga03/*`, `docs/frontend/*`, `docs/handoff-2026-06-02.md`).
> Riesgo bajo en su mayoría; algunos corrigen deudas reales de
> aislamiento de tests.

### 12.1 Bugs en MI trabajo (Phase 9) — prioridad alta ✅

- [x] Ampliar `TEST_COLLECTIONS` en `tests/conftest.py:33-60` de 26 a
      ~50 colecciones. (Ahora 49 colecciones agrupadas por dominio.)
- [x] Apretar `test_admin_can_access_admin_api` en
      `tests/test_middleware.py:73` de `assert response.status_code in
      (200, 404)` a `assert response.status_code == 200`.

### 12.2 Bugs pre-existentes descubiertos — prioridad media ✅

- [x] **Bug latente en `_auth_payload`**: ahora
      `src/app/modules/auth/routes.py:44` lee
      `session.get("session_token_hash", "")`. El frontend
      (`auth.service.ts:92`) consume `session_token` y ahora recibe
      un valor no vacío.
- [x] **`create_user_session` crea índice en cada login**:
      `db.user_sessions.create_index(...)` movido a nueva función
      `ensure_user_sessions_indexes()` y ejecutado una sola vez desde
      `lifespan` en `src/app/main.py`.
- [x] **`get_user_permission_codes` cae a set vacío**: añadido
      `logger.debug` con `user` y `primary_role` cuando el rol no
      resuelve en la colección `roles`. Visible en dev/test sin
      romper el request.

### 12.3 Discrepancias doc vs código — prioridad baja ✅

- [x] Actualizar `docs/ga03/control_acceso_progresivo.md`: el doc
      ahora apunta a `ROUTE_RULES` como fuente de verdad y describe
      el mecanismo de aplicación (prefijo + método + roles/permisos).
- [x] Actualizar `docs/ga03/arquitectura_modular_integraciones.md`:
      añadida nota de estado 2026-06-06 que marca `partner` y
      `auth` como activos, y referencia el seccionado de Phase 1.
- [x] Ampliar `docs/modelo_colecciones.md`: ahora lista las 12
      dimensiones activas + 2 legadas, y cita
      `diseno_base_datos_ga03.md` como fuente de verdad.
- [x] Aclarar en `tests/conftest.py` docstring que las contraseñas
      `Secret123!` / `AdminPass123!` NO son las demo reales.

### 12.4 `requirements.txt` stale — prioridad baja ✅

- [x] Subir `pytest>=8.0,<9.0` a `pytest>=8.0,<10.0`
      (`requirements.txt:10`).
- [x] Documentar el warning de bcrypt en `requirements.txt` con
      comentario que apunta a Phase 12.4 del checklist.

### 12.5 Operacional (del handoff) — no es código

Estos items son **recordatorios al usuario**, no cambios de código.
Se mantienen como checklist para no olvidarlos entre sesiones.

- [ ] **Reiniciar el backend vivo en `127.0.0.1:8000`** para que
      tome `src/app/modules/admin/routes.py`,
      `src/app/security/route_permissions.py` y los nuevos
      `Ensure*` ejecutados en `lifespan`. Sin reinicio, el proceso
      vivo sigue con código viejo
      (`docs/handoff-2026-06-02.md` líneas 236-241).
- [ ] **Validar en navegador `/system/users` y
      `/system/permissions`** después del reinicio. El shell de
      Angular está listo pero falla en runtime porque el backend
      no sirve las rutas nuevas
      (`docs/frontend/frontend_migration_status.md` líneas 84-88).

**Estado Phase 12:**
- 12.1 ✅ hechos
- 12.2 ✅ hechos
- 12.3 ✅ hechos
- 12.4 ✅ hechos
- 12.5 ⏳ recordatorios sin acción de código (usuario debe hacerlos)

---

## Phase 13 - Centralizar `ensure_*_collections` en `lifespan` (módulo partner) ✅

> **Contexto**: los 4 `ensure_*_collections` de
> `src/app/modules/partner/services/bootstrap.py` se llamaban desde cada
> write path del servicio (5 sitios en `content.py`, 5 en `rooms.py`,
> 2 en `properties.py`, 3 en `rates.py`, 2 en `routes.py` `/status`).
> Cada llamada hacía ~30 `create_index` round-trips a Mongo en cada
> write. Mismo anti-pattern arreglado en Phase 12.2.2 para
> `create_user_session`.

- [x] **Mover las 4 llamadas al `lifespan`** en `src/app/main.py`:
      `ensure_hotel_content_collections()`,
      `ensure_hotel_profile_collections()`,
      `ensure_inventory_collections()`,
      `ensure_rate_collections()`. Quedan justo después de
      `ensure_user_sessions_indexes(get_database())`.
- [x] **Borrar las 16 invocaciones en services/routes** del partner.
      Reemplazos exactos (mismo anti-pattern → mismo fix):
      - `services/content.py`: 4 llamadas + 1 import.
      - `services/rooms.py`: 5 llamadas + 1 import.
      - `services/properties.py`: 2 llamadas + 2 imports.
      - `services/rates.py`: 3 llamadas + 1 import.
      - `routes.py`: 2 llamadas en `/modules/partner/status` + 2 imports.
- [x] **Mantener las 4 funciones públicas** en `bootstrap.py` y sus
      re-exports en `services/__init__.py`. Siguen siendo la API
      pública para los scripts standalone
      (`scripts/init_hotel_content_ga03.py`,
      `scripts/init_inventory_ga03.py`) que las invocan fuera de un
      proceso de app.
- [x] **Documentar el cambio** en el docstring de `bootstrap.py`:
      "called once at lifespan startup; service paths no longer invoke
      them".
- [x] **Re-crear los índices del partner en `tests/conftest.py`** en
      el fixture `_clean_collections`, después del drop. Sin esto, los
      tests que escriban a colecciones del partner (futuros) no verían
      las unique constraints de `hotel_images.image_url_1`,
      `hotel_policies.prop_id_1`, `hotel_content_pages.prop_id_1`,
      `room_types.room_type_id_1`, etc. — comportamiento divergente
      silencioso. Costo: ~30 `create_index` por test (39 tests ≈
      +52s sobre el baseline de 9.6s). Aceptable para mantener
      paridad con producción.
- [x] **Verificación**:
      - `python -c "import src.app.main"` → 164 routes registradas, OK.
      - `GET /modules/partner/status` (sin auth) → 303 a
        `/login?next=/modules/partner/status` (middleware actúa, ruta
        está montada).
      - `python -m pytest -q` → 39 passed in 62.13s.

**Nota sobre revenue y reservations**: existen 2 `ensure_*_collections`
más con el mismo anti-pattern:
- `src/app/modules/revenue/service.py:22-62` `ensure_revenue_collections`
  (6 llamadas desde `revenue/service.py` + 1 desde `routes.py`).
- `src/app/modules/reservations/service.py:60-81`
  `ensure_reservation_collections` (1 llamada desde
  `reservations/service.py:192`).

Quedan fuera de Phase 13 por scope (esta fase solo cubre el módulo
partner, del que tenemos ownership desde Phase 1). Si querés, se
pueden meter en Phase 13.2 / 13.3 siguiendo el mismo patrón.

---

## Phase 13.2 - Mismo patrón para revenue ✅

> **Contexto**: `ensure_revenue_collections` se llamaba desde 6 write
> paths en `revenue/service.py` + 1 en `routes.py` `/status`. Mismo
> anti-pattern que 13.1.

- [x] **Mover la llamada al `lifespan`** en `src/app/main.py`. Queda
      justo después de las 4 del partner, en orden de dependencia
      (revenue depende de las mismas colecciones que partner).
- [x] **Borrar las 7 invocaciones** en service + routes:
      - `service.py:329, 349, 396, 427, 454, 483` (6 calls).
      - `routes.py:36` (1 call en `/modules/revenue/status`).
      - 1 import borrado en `routes.py:14`.
- [x] **Mantener la función pública** en `revenue/service.py:22` y
      re-exportada para que `scripts/init_revenue_ga03.py` y
      `scripts/validate_ga03_revenue.py` sigan funcionando.
- [x] **Documentar el overlap** con `partner.services.bootstrap.ensure_rate_collections`
      en el docstring de `ensure_revenue_collections`. Las 5
      colecciones (`rate_plans`, `hotel_rate_calendar`, `rate_rules`,
      `promotion_campaigns`, `coupon_codes`) son también tocadas por
      el bootstrap del partner. La mayoría de los índices son
      idempotentes (mismo nombre + mismo spec) y solo se materializan
      una vez. El único índice genuinamente nuevo que aporta revenue
      es `rate_rules.rule_id_1` (unique). Existe una
      casi-duplicación: partner crea `hotel_rate_calendar.prop_rate_date`
      y revenue crea `hotel_rate_calendar.prop_plan_date` (ambos sobre
      `(prop_id, rate_plan_id, date)` unique, distinto nombre). Mongo
      crea ambos, lo cual es desperdicio. No se corrige en esta fase
      por scope; queda como **deuda conocida** para una fase futura
      de unificación de ownership de colecciones tarifarias.
- [x] **Re-crear el índice en `tests/conftest.py`** agregando
      `ensure_revenue_collections()` al fixture `_clean_collections`
      después de los 4 del partner. Sin esto, los tests con writes a
      `rate_rules` no verían la unique constraint de `rule_id_1`.
- [x] **Verificación**:
      - `python -c "import src.app.main"` → 164 routes registradas, OK.
      - `GET /modules/revenue/status` (sin auth) → 303 a
        `/login?next=/modules/revenue/status` (middleware actúa, ruta
        está montada).
      - `python -m pytest -q` → 39 passed in 32.35s.

**Deuda conocida** (registrada, NO aplicada en esta fase):
- **Ownership compartido de colecciones tarifarias**: tanto
  `partner` como `revenue` declaran bootstrap sobre `rate_plans`,
  `hotel_rate_calendar`, `rate_rules`, `promotion_campaigns`,
  `coupon_codes`. Hay un índice casi-duplicado
  (`prop_rate_date` vs `prop_plan_date`) y 9 índices que viven dos
  veces en el código. La solución natural es elegir un solo owner
  (probablemente `partner`, que ya los declara) y hacer que
  `revenue` re-use ese bootstrap. Es trabajo de ~30 min cuando
  alguien decida que el desorden de ownership duele.
- **Phase 13.3 (reservations)**: 1 call site en
  `reservations/service.py:192`. Sigue siendo marginal; no
  aplicado por ahora.
