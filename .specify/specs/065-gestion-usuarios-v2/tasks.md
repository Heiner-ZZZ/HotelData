# Tareas: Gestión de Usuarios v2

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 0: Fundación (Shared Infrastructure)

**Propósito**: Colecciones, seed data, y utilidades compartidas que todos los módulos necesitan.

- [ ] T001 Crear colección `password_policies` con seed del documento singleton en script init
- [ ] T002 Crear colección `user_audit_log` con TTL index opcional en script init
- [ ] T003 Agregar campos `password_changed_at`, `password_history`, `invitation_token_hash`, `invitation_expires_at`, `must_change_password` al modelo de usuario
- [ ] T004 [P] Crear `server/src/app/security/password_policies.py` con funciones: `get_password_policies()`, `validate_password(password, policies)`, `is_password_expired(user)`, `check_password_history(user, new_password)`
- [ ] T005 [P] Exportar `invalidate_user_sessions()` desde `server/src/app/security/session.py` (ya existe, asegurar export en `__init__.py`)
- [ ] T006 [P] Agregar helpers de logging de auditoría en `server/src/app/modules/admin/service/_audit_helper.py`: `log_user_change(user_id, changed_by, action, field, old_value, new_value)`
- [ ] T007 Agregar nuevas reglas RBAC en `route_permissions.py` para `/api/admin/audit` y `/api/admin/password-policies`

**Checkpoint**: Fundación lista — colecciones creadas, validación de contraseña funcionando, helpers de auditoría listos.

---

## Fase 1: Edición de Perfil de Usuario (Priority: P1) 🎯 MVP

**Goal**: Admin puede editar nombre/email/rol de cualquier usuario. Usuario puede editar su propio nombre y email, y cambiar su propia contraseña.

### Backend

- [ ] T008 [P] [P1] Crear `server/src/app/modules/admin/service/profile.py` con `update_user_profile()` (cambiar nombre, email, rol por admin)
- [ ] T009 [P] [P1] Crear `server/src/app/modules/account/service/profile.py` con `update_own_profile()` (cambiar nombre, email) y `change_own_password()` (requiere contraseña actual)
- [ ] T010 [P1] Agregar endpoint `PUT /api/admin/users/{user_id}` en `admin/routes.py`
- [ ] T011 [P1] Agregar endpoint `POST /api/admin/users/{user_id}/reset-password` en `admin/routes.py` (genera temporal)
- [ ] T012 [P1] Agregar endpoint `POST /api/admin/users/{user_id}/deactivate` en `admin/routes.py`
- [ ] T013 [P1] Agregar endpoint `GET /api/account/profile` en `account/routes.py`
- [ ] T014 [P1] Agregar endpoint `PUT /api/account/profile` en `account/routes.py`
- [ ] T015 [P1] Agregar endpoint `PUT /api/account/password` en `account/routes.py`
- [ ] T016 [P1] Agregar verificación por email al cambiar email (reutilizar lógica existente de `auth/routes.py`)
- [ ] T017 [P1] Implementar doble confirmación en backend para auto-desactivación (endpoint separado o flag `confirmed`)

### Frontend

- [ ] T018 [P] [P1] Crear página `user-edit-page` en `system-admin/pages/` con formulario: nombre, email, rol, botón reset password, botón desactivar
- [ ] T019 [P] [P1] Crear página `account-profile-page` en `account/pages/` con formulario de nombre y email
- [ ] T020 [P] [P1] Crear página `account-password-page` en `account/pages/` con formulario: contraseña actual + nueva + confirmar
- [ ] T021 [P1] Agregar rutas: `/system/users/:userId/edit`, `/account/profile`, `/account/password` en los routes respective
- [ ] T022 [P1] Agregar modal de doble confirmación para auto-desactivación

**Checkpoint**: Admins pueden editar usuarios, usuarios pueden editar su perfil y cambiar contraseña. ✅ MVP

---

## Fase 2: Invitación por Email (Priority: P2)

**Goal**: Admin puede invitar usuarios por email con contraseña temporal y link de 24h.

### Backend

- [ ] T023 [P] [P2] Crear `server/src/app/modules/admin/service/invite.py` con `create_invitation()` (crea usuario + genera token + password temporal) y `resend_invitation()`
- [ ] T024 [P] [P2] Agregar endpoint `POST /api/admin/invite` en `admin/routes.py`
- [ ] T025 [P] [P2] Agregar endpoint `POST /api/admin/invite/{token}/resend` en `admin/routes.py`
- [ ] T026 [P2] Modificar `auth/routes.py` en `POST /api/auth/login`: verificar `must_change_password` e `invitation_expires_at`
- [ ] T027 [P] [P2] Agregar endpoint `POST /api/auth/set-password` para procesar cambio post-invitación
- [ ] T028 [P] [P2] Agregar endpoint `GET /api/auth/verify-invitation?token=` para validar token antes de mostrar formulario

### Frontend

- [ ] T029 [P] [P2] Crear página `user-invite-page` en `system-admin/pages/` con formulario: email, nombre, rol, y botón "Enviar invitación"
- [ ] T030 [P] [P2] Crear página `set-password-page` en `auth/pages/` con formulario: nueva contraseña + confirmar (post-invitación)
- [ ] T031 [P2] Agregar ruta `/set-password` en `app.routes.ts` (sin auth guard, solo token válido)
- [ ] T032 [P2] Agregar indicador de token expirado con botón "Solicitar nueva invitación"

**Checkpoint**: Flujo de invitación funcional de principio a fin.

---

## Fase 3: Auditoría de Usuarios (Priority: P2)

**Goal**: Panel visual con historial de cambios en usuarios, exportable a CSV/JSON.

### Backend

- [ ] T033 [P] [P2] Crear `server/src/app/modules/admin/service/audit.py` con `list_user_audit_logs(filters)`, `export_user_audit_csv(filters)`, `export_user_audit_json(filters)`
- [ ] T034 [P2] Agregar endpoint `GET /api/admin/users/audit` con filtros: usuario, admin, acción, fecha desde/hasta, página
- [ ] T035 [P] [P2] Agregar endpoint `GET /api/admin/users/audit/export?format=csv|json`

### Frontend

- [ ] T036 [P] [P2] Crear página `user-audit-page` en `system-admin/pages/` con tabla, filtros (fecha, usuario, acción, admin), paginación
- [ ] T037 [P2] Agregar botones de exportación CSV y JSON
- [ ] T038 [P2] Agregar ruta `/system/audit/users` en `system-admin.routes.ts`
- [ ] T039 [P2] Actualizar `sidebar-nav.ts` con entrada "Auditoría de usuarios" en sección Sistema

**Checkpoint**: Auditoría funcional con panel y exportación.

---

## Fase 4: Políticas de Contraseña (Priority: P3)

**Goal**: Super Admin puede configurar políticas de contraseña desde UI.

### Backend

- [ ] T040 [P] [P3] Agregar endpoint `GET /api/admin/password-policies` en `admin/routes.py`
- [ ] T041 [P] [P3] Agregar endpoint `PUT /api/admin/password-policies` en `admin/routes.py`
- [ ] T042 [P3] Integrar `validate_password()` en todos los puntos de cambio de contraseña: registro, cambio propio, reseteo admin, post-invitación
- [ ] T043 [P3] Integrar `is_password_expired()` en `POST /api/auth/login`: si expirado, redirigir a cambio de contraseña
- [ ] T044 [P3] Integrar `check_password_history()` en todos los puntos de cambio de contraseña

### Frontend

- [ ] T045 [P] [P3] Crear página `password-policies-page` en `system-admin/pages/` con controles: slider para min_length, toggles para requisitos, input para expiration_days, input para history_count
- [ ] T046 [P3] Agregar ruta `/system/password-policies` en `system-admin.routes.ts`
- [ ] T047 [P3] Actualizar `sidebar-nav.ts` con entrada "Políticas de seguridad" en sección Sistema

**Checkpoint**: Políticas configurables y aplicadas en todo el sistema.

---

## Fase 5: Integración y Validación

**Propósito**: Asegurar que todo funciona junto.

- [ ] T048 [P] Verificar que `user_audit_log` registra cambios de los 4 módulos
- [ ] T049 [P] Verificar que `password_policies` se aplican en registro, cambio propio, reseteo admin, y post-invitación
- [ ] T050 [P] Verificar expiración de contraseña en login redirige correctamente
- [ ] T051 Verificar que el modal de auto-desactivación requiere dos clics
- [ ] T052 [P] Verificar exportación CSV/JSON de auditoría
- [ ] T053 Verificar flujo completo de invitación: crear → email → set password → login

---

## Dependencias entre fases

| Fase | Depende de | Puede empezar |
|------|-----------|---------------|
| Fase 0 (Fundación) | Nada | Inmediato |
| Fase 1 (Perfil P1) | Fase 0 | Después de Fase 0 |
| Fase 2 (Invitación P2) | Fase 0 + Fase 1 | Después de Fase 1 |
| Fase 3 (Auditoría P2) | Fase 0 | En paralelo con Fase 1 |
| Fase 4 (Políticas P3) | Fase 0 + Fase 1 | Después de Fase 1 |
| Fase 5 (Validación) | Fases 1-4 | Después de Fases 1-4 |

### Oportunidades paralelas

- T001, T002, T003, T004, T005, T006, T007 (Fase 0) pueden ejecutarse en paralelo
- T008 y T009 (Backend perfil admin + account) pueden ejecutarse en paralelo
- T018, T019, T020 (Frontend perfil) pueden ejecutarse en paralelo
- Fase 3 (Auditoría) puede ejecutarse en paralelo con Fase 1 (no depende de ella)

---

## Resumen de archivos

### Archivos nuevos (14 backend + 7 frontend páginas)

```
server/src/app/security/password_policies.py
server/src/app/modules/admin/service/profile.py
server/src/app/modules/admin/service/invite.py
server/src/app/modules/admin/service/audit.py
server/src/app/modules/admin/service/_audit_helper.py
server/src/app/modules/account/service/profile.py
server/src/app/modules/account/routes.py
frontend/src/app/features/system-admin/pages/user-edit-page/*
frontend/src/app/features/system-admin/pages/user-invite-page/*
frontend/src/app/features/system-admin/pages/user-audit-page/*
frontend/src/app/features/system-admin/pages/password-policies-page/*
frontend/src/app/features/account/pages/account-profile-page/*
frontend/src/app/features/account/pages/account-password-page/*
frontend/src/app/features/auth/pages/set-password-page/*
```

### Archivos a modificar

```
server/src/app/modules/admin/routes.py
server/src/app/modules/admin/service/users.py
server/src/app/security/session.py
server/src/app/security/route_permissions.py
server/src/app/modules/auth/routes.py
frontend/src/app/app.routes.ts
frontend/src/app/features/account/account.routes.ts
frontend/src/app/features/system-admin/system-admin.routes.ts
frontend/src/app/shared/ui/sidebar-nav/sidebar-nav.ts
```
