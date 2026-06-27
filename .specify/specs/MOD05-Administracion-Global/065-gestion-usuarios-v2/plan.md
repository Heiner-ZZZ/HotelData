# Plan de Implementación: Gestión de Usuarios v2

**Branch**: `065-gestion-usuarios-v2` | **Spec**: [065-gestion-usuarios-v2](spec.md)

## Arquitectura General

```
Frontend (Angular)                    Backend (FastAPI)                    MongoDB
─────────────────                    ─────────────────                    ──────
                                                     ┌──────────────┐
  /account/profile  ───► PUT /api/account/profile ──►│ profile.py   │──► users
  /account/profile  ───► PUT /api/account/password ──► (self-serv.)  │
                                                     │              │
  /system/users/    ───► GET /api/admin/users/{id} ──►              │
  {id}/edit              PUT /api/admin/users/{id}   │ admin.py     │──► users
                                                     │ (admin)      │
  /system/users/    ───► POST /api/admin/invite ─────►              │──► users
  invite                                              │ invite.py    │──► email
                                                                         │
  /system/audit     ───► GET /api/admin/audit ───────► audit.py     │──► user_audit_log
                                                                         │
  /system/password- ───► GET /api/admin/password-     │ policies.py │──► password_policies
  policies                policies                     │             │
                      ───► PUT /api/admin/password-
                           policies
```

## Componentes del Sistema

### Backend (archivos nuevos)

| Archivo | Propósito |
|---------|-----------|
| `server/src/app/security/password_policies.py` | Validación de contraseña contra políticas, singleton, helper de expiración |
| `server/src/app/modules/admin/service/profile.py` | Edición admin de perfil de cualquier usuario |
| `server/src/app/modules/admin/service/invite.py` | Flujo de invitación por email |
| `server/src/app/modules/admin/service/audit.py` | Consultas de auditoría de cambios en usuarios |
| `server/src/app/modules/account/service/profile.py` | Edición de perfil propio (auto-servicio) |
| `server/src/app/modules/account/routes.py` | Endpoints de perfil de cuenta propia |

### Backend (archivos modificar)

| Archivo | Cambio |
|---------|--------|
| `server/src/app/modules/admin/routes.py` | Nuevos endpoints: PUT /users/{id}, POST /invite, GET /audit, GET/PUT /password-policies |
| `server/src/app/modules/admin/service/users.py` | Agregar `update_user_profile()`, `reset_password()`, `self_deactivate()` |
| `server/src/app/security/session.py` | Exportar `invalidate_user_sessions()` (ya existe) |
| `server/src/app/security/route_permissions.py` | Nuevas reglas para /api/admin/audit, /api/admin/password-policies |
| `server/src/app/modules/auth/routes.py` | En `login`, verificar `must_change_password` y redirigir a cambio |

### Frontend (archivos nuevos)

| Archivo | Propósito |
|---------|-----------|
| `frontend/src/app/features/system-admin/pages/user-edit-page/*` | Formulario de edición de usuario (admin) |
| `frontend/src/app/features/system-admin/pages/user-invite-page/*` | Formulario de invitación |
| `frontend/src/app/features/system-admin/pages/user-audit-page/*` | Panel de auditoría |
| `frontend/src/app/features/system-admin/pages/password-policies-page/*` | Configuración de políticas |
| `frontend/src/app/features/account/pages/account-profile-page/*` | Perfil propio del usuario |
| `frontend/src/app/features/account/pages/account-password-page/*` | Cambiar propia contraseña |
| `frontend/src/app/features/auth/pages/set-password-page/*` | Página post-invitación (primer login) |

### Frontend (archivos modificar)

| Archivo | Cambio |
|---------|--------|
| `frontend/src/app/features/system-admin/system-admin.routes.ts` | Nuevas rutas: edit, invite, audit, password-policies |
| `frontend/src/app/shared/ui/sidebar-nav/sidebar-nav.ts` | Nueva entrada "Auditoría" en sección Sistema |
| `frontend/src/app/features/account/account.routes.ts` | Nuevas rutas: profile, password |
| `frontend/src/app/app.routes.ts` | Ruta /set-password |

### Colecciones MongoDB

| Colección | Tipo | Propósito |
|-----------|------|-----------|
| `password_policies` | Singleton | Configuración global de políticas de contraseña |
| `user_audit_log` | Logs | Registro de cambios en usuarios (TTL index opcional) |

### Campos nuevos en `users`

| Campo | Tipo | Propósito |
|-------|------|-----------|
| `password_changed_at` | datetime | Último cambio de contraseña (para expiración) |
| `password_history` | array[string] | Últimas N contraseñas hasheadas |
| `invitation_token_hash` | string | Hash del token de invitación activo |
| `invitation_expires_at` | datetime | Expiración del token de invitación |
| `must_change_password` | boolean | Forzar cambio en próximo login |

## Endpoints

| Método | Ruta | Módulo | Propósito |
|--------|------|--------|-----------|
| GET | /api/admin/users/{user_id} | Admin | Obtener datos editables de un usuario |
| PUT | /api/admin/users/{user_id} | Admin | Actualizar nombre, email, rol de un usuario |
| POST | /api/admin/users/{user_id}/reset-password | Admin | Resetear contraseña de un usuario |
| POST | /api/admin/users/{user_id}/deactivate | Admin | Desactivar usuario (con confirmación) |
| POST | /api/admin/invite | Admin | Invitar nuevo usuario por email |
| POST | /api/admin/invite/{token}/resend | Admin | Reenviar invitación expirada |
| GET | /api/admin/users/audit | Admin | Listar registros de auditoría (con filtros) |
| GET | /api/admin/users/audit/export | Admin | Exportar auditoría a CSV/JSON |
| GET | /api/admin/password-policies | Admin | Obtener configuración actual |
| PUT | /api/admin/password-policies | Admin | Actualizar políticas |
| GET | /api/account/profile | Account | Obtener perfil propio |
| PUT | /api/account/profile | Account | Actualizar nombre y email propio |
| PUT | /api/account/password | Account | Cambiar propia contraseña |
| GET | /set-password?token= | Auth | Formulario post-invitación |
| POST | /api/auth/set-password | Auth | Procesar cambio de contraseña post-invitación |

## Dependencias entre módulos

```
Foundational (compartido)
├── Colección password_policies + seed data
├── Colección user_audit_log + TTL index
├── password_policies.py (validación)
├── Campos nuevos en users (seed/migration)
└── session.py (invalidate_user_sessions export)
│
├── Módulo 1: Edición de Perfil (P1)
│   ├── Backend: admin/profile.py + account/profile.py
│   ├── Frontend: user-edit-page + account-profile-page
│   └── Depende de: password_policies.py (validación)
│
├── Módulo 2: Invitación por Email (P2)
│   ├── Backend: admin/invite.py
│   ├── Frontend: user-invite-page + set-password-page
│   └── Depende de: Módulo 1 (perfil existe), email/service.py
│
├── Módulo 3: Auditoría (P2)
│   ├── Backend: admin/audit.py
│   ├── Frontend: user-audit-page
│   └── Depende de: user_audit_log collection
│
└── Módulo 4: Políticas de Contraseña (P3)
    ├── Backend: password_policies.py (compartido)
    ├── Frontend: password-policies-page
    └── Depende de: session.py (forzar logout al expirar)
```

## Flujos clave

### Flujo de invitación
```
Admin ingresa email+nombre+rol
  → POST /api/admin/invite
    → Crear user con is_active=false, must_change_password=true
    → Generar token 48 bytes, hash SHA-256 en invitation_token_hash
    → Guardar invitation_expires_at = now + 24h
    → Generar password temporal 12 chars
    → Email: "Bienvenido. Tu contraseña temporal es: XXXX. Link: /set-password?token=YYYY"
    → Registrar en user_audit_log
  → 201 + "Invitación enviada"

Usuario recibe email
  → GET /set-password?token=YYYY
    → Verificar token no expirado
    → Mostrar formulario: nueva contraseña
  → POST /api/auth/set-password
    → Validar contra password_policies
    → Actualizar password_hash
    → Marcar is_active=true, must_change_password=false
    → Limpiar invitation_token_hash
    → Invalidar invitation_expires_at
    → Registrar en user_audit_log
    → Redirigir a login
```

### Flujo de cambio de email
```
Usuario cambia email en su perfil
  → PUT /api/account/profile { email: "nuevo@email.com" }
    → Marcar email_verified=false
    → Enviar verificación al NUEVO email
    → Registrar en user_audit_log con old_value/new_value
  → 200 + "Verifica tu nuevo email"
```

### Flujo de verificación de expiración de contraseña
```
Usuario inicia sesión (POST /api/auth/login)
  → Verificar must_change_password
  → Si true: redirigir a /set-password con mensaje "Debes cambiar tu contraseña"
  → Si password_policies.expiration_days > 0:
    → Calcular días desde password_changed_at
    → Si expirado: redirigir a /set-password con mensaje "Tu contraseña ha expirado"
```

## Notas técnicas

- La validación de contraseña contra políticas se implementa como función pura en `password_policies.py` para poder reutilizarse en registro, cambio propio, reseteo admin, y post-invitación.
- `user_audit_log` usa el mismo patrón que `user_activity_logs` pero es específico para cambios de perfil (contiene old/new value por campo).
- La desactivación con doble confirmación es UI-only: el backend siempre recibe la misma petición; la confirmación doble se maneja en el frontend con estados del modal.
- Para la expiración de contraseña, se verifica en el login (POST /api/auth/login) y se redirige si es necesario.
