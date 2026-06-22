# Plan de Implementación: Inicio de Sesión JWT

**Branch**: `main` | **Spec**: 001-inicio-sesion-jwt

## Arquitectura

```
Cliente (form/web) → POST /auth/login → session.py → users collection
                   → POST /api/auth/login → session.py → user_sessions collection
                                              → cookie hoteldata_session (httponly)
                                              → user_activity_logs
```

## Componentes existentes

| Archivo | Propósito |
|---------|-----------|
| `server/src/app/security/session.py` | Crear/invalidar sesiones, bcrypt verify |
| `server/src/app/security/dependencies.py` | require_login(), get_current_user() |
| `server/src/app/security/permissions.py` | get_user_permission_codes() |
| `server/src/app/modules/auth/routes.py` | Login web (GET/POST) + API (POST) |
| `users` collection | Almacena password_hash con bcrypt |
| `user_sessions` collection | TTL index 8h en expires_at |

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /auth/login | Mostrar formulario login (HTML) |
| POST | /auth/login | Procesar login (HTML form) |
| POST | /api/auth/login | Login API (JSON) |
| GET | /api/auth/me | Sesión actual |

## Flujo de datos

1. Usuario envía email + password
2. `session.py:verify_password()` → bcrypt check contra users.password_hash
3. Si OK: `session.py:create_session()` → token 48 bytes → hash SHA-256 → user_sessions
4. Cookie `hoteldata_session` = token plano
5. Redirección según rol (navigation.py)
