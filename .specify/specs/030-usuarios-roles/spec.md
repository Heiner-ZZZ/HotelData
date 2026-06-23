# Especificacion: Usuarios, Roles y Permisos

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T09 (Administrar usuarios, roles, permisos y navegacion por rol)

## 1. Objetivo

Administrar usuarios del sistema, roles, permisos y reglas de navegacion por rol (RBAC completo). 9 roles con permisos granulares.

## 2. Contexto

El sistema tiene 9 roles: super_admin, admin_sistema, cliente, recepcionista, hotel_partner, gerente_hotel, revenue_manager, marketing_hotelero, auditor_datos.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Super Admin | Administracion global del sistema |
| Admin Sistema | Gestion operativa de usuarios |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe listar usuarios con filtros por rol, estado activo/inactivo | Alta |
| RF-002 | El sistema debe permitir activar/desactivar usuarios | Alta |
| RF-003 | El sistema debe permitir cambiar el rol de un usuario | Alta |
| RF-004 | El sistema debe definir permisos por rol en route_permissions.py | Alta |
| RF-005 | El sistema debe proteger rutas con AuthGuard + RoleGuard | Alta |
| RF-006 | El sistema debe adaptar sidebar segun el rol del usuario | Alta |

## 5. Reglas de negocio

- 9 roles fijos con permisos predefinidos
- Un usuario tiene exactamente un rol
- Los permisos se definen en route_permissions.py
- Frontend: AuthGuard y RoleGuard protegen rutas

## 6. Escenarios

### Escenario 1: Cambiar rol de usuario
```gherkin
Dado que el admin selecciona un usuario hotel_partner
Cuando cambia su rol a gerente_hotel
Entonces el usuario accede a las rutas de gerente_hotel
```

### Escenario 2: Desactivar usuario
```gherkin
Dado que el admin desactiva un usuario
Cuando el usuario intenta iniciar sesion
Entonces el sistema rechaza el login
```

## 7. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | CRUD de usuarios funciona con filtros |
| CA-002 | Cambio de rol actualiza permisos inmediatamente |
| CA-003 | Usuario desactivado no puede iniciar sesion |
| CA-004 | Guards de Angular protegen rutas correctamente |

## 8. Dependencias

- Colecciones: users, roles, permissions, role_permissions
- Modulo: src/app/security/permissions.py, route_permissions.py
- Frontend: auth.guard.ts, role.guard.ts, sidebar-nav.ts

## 9. Fuera de alcance

- Roles personalizados (solo 9 fijos)
- Permisos granulares por recurso (solo por ruta)
