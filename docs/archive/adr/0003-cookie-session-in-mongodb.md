# ADR-0003: Cookie Session Persistida en MongoDB

## Status
Accepted

## Date
2026-06-06

## Context
- Auth del web app usa sesiones server-side, no JWT.
- Cookie: `hoteldata_session` (httpOnly, secure en prod), TTL 8h.
- Las sesiones se persisten en una colección MongoDB (`user_sessions`).
- Cada request pasa por `src/app/security/middleware.py:36-37` que hace
  `get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))` —
  un lookup a Mongo por request autenticado.

## Decision
**Sesiones server-side con token opaco + hash en MongoDB.**

- Token: `secrets.token_urlsafe(48)` (64 chars, ~384 bits entropía).
- Cookie: solo el token en plano. En Mongo se guarda
  `hashlib.sha256(token).hexdigest()`.
- TTL: 8h, enforced por `expires_at` y un job de limpieza
  (recomendado: cron en el DAG o `TTL index` en Mongo).
- Logout = `delete_one` por `session_token_hash`.
- Passwords: `passlib[bcrypt]`, cost factor 12.

## Alternatives Considered

### JWT stateless
- **Pros**: cero lookup por request, escala horizontal trivial.
- **Cons**: revocación inmediata imposible (lista de bloqueos = misma
  BD que queríamos evitar). Refresh tokens añaden complejidad.
- **Why not**: la invalidación inmediata de sesión es requisito del
  dominio (cambio de rol, baja de usuario). La "performance win" de
  JWT no compensa.

### Sesiones en Redis
- **Pros**: lookup O(1) en memoria.
- **Cons**: estado en un sistema extra; si Redis cae, todos deslogueados.
- **Why not**: Mongo ya está; añadir Redis para esto es un hop más sin
  ganancia material al volumen actual. (Redis ya existe en el proyecto
  para caching, ver `src/cache/`, pero para algo distinto.)

### Sesiones firmadas (cookie = payload firmado)
- **Pros**: cero storage.
- **Cons**: revocación inmediata imposible (mismo problema que JWT).
  Tamaño de cookie crece con claims.
- **Why not**: misma razón que JWT.

## Consequences

### Positive
- Revocación inmediata: `delete_one` y el usuario está fuera.
- Cookie no filtra información: solo un token opaco.
- Auditoría: la colección `user_sessions` guarda `ip_address`,
  `user_agent`, `created_at`, `expires_at` — útil para
  `docs/ga03/control_acceso_progresivo.md`.

### Negative
- **1 lookup a Mongo por request autenticado** (ver
  `src/app/security/middleware.py:36-37`). Con 50 RPS y Mongo con índice
  en `session_token_hash`, son ~50 lookups/s — irrelevante. **Pero** es
  un patrón que escala mal cuando se vuelve 5000 RPS.
- Sesión atada al proceso: si Mongo se cae, nadie se loguea.

### Risks
- **Riesgo**: el `user_sessions` collection crece sin TTL.
  **Mitigación**: crear un `TTL index` en `expires_at` y/o un job de
  limpieza.
- **Riesgo**: el lookup por request es un cuello de botella futuro.
  **Mitigación**: tier 4 del roadmap (`docs/refactor-checklist.md` Phase
  10) plantea cachear el lookup en Redis con TTL corto. No urgente.

## References
- `src/app/security/session.py` (todo el flujo de auth)
- `src/app/security/middleware.py:36-37` (lookup por request)
- `src/app/security/dependencies.py`
- `requirements.txt:11-13` (passlib, bcrypt, python-jose)
- `.opencode/skills/backend-senior/SKILL.md` §9
