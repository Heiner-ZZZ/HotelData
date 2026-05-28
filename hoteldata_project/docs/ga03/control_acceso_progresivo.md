# Control de acceso progresivo GA03

## Objetivo

Agregar una capa de sesión y permisos sin bloquear todavía toda la aplicación. Las rutas históricas siguen funcionando mientras las nuevas rutas sensibles empiezan a usar control de acceso.

## Archivos creados

- `src/app/security/dependencies.py`
- `src/app/security/permissions.py`
- `src/app/modules/admin/routes.py`
- `src/app/modules/admin/service.py`
- `src/app/templates/admin/security.html`
- `src/app/templates/admin/users.html`

## Funciones disponibles

- `get_current_user(request)`: resuelve usuario actual desde la cookie `hoteldata_session`.
- `require_login(request)`: exige sesión activa.
- `require_permission(permission_code)`: exige sesión y permiso específico.

## Rutas protegidas ahora

- `/auth/me`: requiere login.
- `/admin/users`: requiere `users.manage`.
- `/admin/security`: requiere `users.manage`.

## Rutas no protegidas todavía

- `/ta02`
- `/ta02/crud`
- `/etl-status`

## Permisos

Los permisos se validan usando:

- `users`
- `roles`
- `permissions`
- `role_permissions`
- `user_sessions`

El rol `super_admin` tiene acceso total por convención de seguridad.

## Flujo de prueba

1. Crear modelo de seguridad:

```powershell
python scripts/init_security_model_ga03.py
```

2. Iniciar sesión:

```text
/auth/login
```

3. Probar sesión:

```text
/auth/me
```

4. Probar rutas administrativas:

```text
/admin/security
/admin/users
```

## Alcance

Este control es progresivo. No implementa todavía protección global, políticas avanzadas ni edición de usuarios desde UI.
