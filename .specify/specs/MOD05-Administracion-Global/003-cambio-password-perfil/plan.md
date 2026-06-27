# Plan de Implementación: Cambio de Contraseña y Perfil

**Spec**: 003-cambio-password-perfil

## Arquitectura

```
Password: PUT /api/settings/password → verify current → hash new → update users.password_hash
                                                                   → invalidate sessions
                                                                   → activity log

Profile:  PUT /api/account/profile → update users.profile subdocument → activity log
Avatar:   POST /api/account/profile/avatar → save file → update users.profile.avatar_url
```

## Componentes

| Archivo | Propósito |
|---------|-----------|
| `server/src/app/modules/settings/routes.py` | PUT /api/settings/password |
| `server/src/app/modules/account/routes.py` | GET/PUT profile, POST avatar |
| `server/src/app/security/session.py` | invalidate_all_user_sessions() |

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/account/profile | Obtener perfil |
| PUT | /api/account/profile | Actualizar perfil |
| POST | /api/account/profile/avatar | Subir avatar |
| PUT | /api/settings/password | Cambiar contraseña |
| PUT | /api/settings | Actualizar config (timeout, dashboard) |
