# Plan de Implementación: Gestión de Sesiones

**Spec**: 002-gestion-sesiones

## Arquitectura

```
Logout: GET /auth/logout → session.invalidate_session() → delete user_sessions
                                                           → clear cookie
                                                           → redirect /login

Sesión: GET /api/auth/me → session.get_current_user() → user_sessions lookup
                                                          → return user data or 401
```

## Componentes

| Archivo | Propósito |
|---------|-----------|
| `server/src/app/security/session.py` | invalidate_session(), get_session() |
| `server/src/app/modules/auth/routes.py` | GET /auth/logout, GET /auth/me, GET /api/auth/me |
| `user_sessions` collection | TTL index en expires_at |

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /auth/logout | Logout web (HTML redirect) |
| GET | /auth/me | Homepage según rol |
| GET | /api/auth/me | Estado de sesión (JSON) |
