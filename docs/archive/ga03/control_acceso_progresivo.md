# Control de acceso progresivo GA03

## Estado del documento

> **Este documento fue escrito para el rollout inicial del control de acceso
> y está parcialmente desactualizado.** La lista vigente de reglas
> protegidas vive en una sola tabla central:
> `src/app/security/route_permissions.py` (`ROUTE_RULES`).
>
> Para saber qué ruta está protegida hoy, revisa ese archivo. Esta
> página conserva el contexto histórico de la fase progresiva y los
> archivos creados, pero **no** la enumeración exacta de rutas.

## Objetivo

Agregar una capa de sesión y permisos sin bloquear todavía toda la aplicación. Las rutas históricas siguen funcionando mientras las nuevas rutas sensibles empiezan a usar control de acceso.

## Archivos creados

- `src/app/security/dependencies.py`
- `src/app/security/permissions.py`
- `src/app/security/route_permissions.py` (tabla central `ROUTE_RULES`)
- `src/app/security/middleware.py` (aplica la tabla por prefijo + método)
- `src/app/modules/admin/routes.py`
- `src/app/modules/admin/service.py`
- `src/app/templates/admin/security.html`
- `src/app/templates/admin/users.html`

## Funciones disponibles

- `get_current_user(request)`: resuelve usuario actual desde la cookie `hoteldata_session`.
- `require_login(request)`: exige sesión activa.
- `require_permission(permission_code)`: exige sesión y permiso específico.

## Cómo se aplica el control hoy

1. El middleware `role_access_middleware` (`src/app/security/middleware.py`)
   lee cada request y busca una `AccessRule` cuyo prefijo matchee
   `path` y cuyo `methods` incluya el `method` HTTP.
2. Si la regla tiene `roles`, se acepta al usuario cuyo `primary_role`
   esté en esa tupla (atajo: `super_admin` siempre pasa).
3. Si la regla tiene `permission`, se acepta al usuario si
   `user_has_permission(db, user, permission)` devuelve `True`
   (`src/app/security/permissions.py`).
4. Si no hay regla que aplique, el default es permitir solo a
   `super_admin` y `admin_sistema` (esto se ve en
   `get_access_rule`, que devuelve un `AccessRule` restrictivo
   cuando no hay match).
5. Si el usuario no está autenticado y la ruta no es pública, se le
   redirige a `/login?next=...` (web) o se devuelve `401` JSON (API).

## Rutas explícitamente públicas

Definidas en `PUBLIC_PREFIXES` y `PUBLIC_PATHS` de
`src/app/security/route_permissions.py`. Lo que **no** esté en esa
lista y no tenga una `AccessRule` permisiva, queda restringido.

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
