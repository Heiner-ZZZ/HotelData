# Plan de Implementación: Usuarios, Roles y Permisos

**Branch**: `030-usuarios-roles` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Admin
  → UsersPage (CRUD usuarios)
  → RolesPage (matriz de permisos)
    → GET/POST/PUT /api/admin/users
    → GET/PUT /api/admin/roles
      → admin/services/users.py
      → admin/services/roles.py
        → users, roles, permissions collections
        → route_permissions.py (backend RBAC)
```

## Componentes existentes

| Archivo | Propósito |
|---------|-----------|
| `server/src/app/security/permissions.py` | `get_user_permission_codes()`, `ROUTE_RULES` |
| `server/src/app/security/route_permissions.py` | Reglas de ruta por rol |
| `server/src/app/security/dependencies.py` | `require_permission()` |

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/admin/users | Listar usuarios con filtros |
| POST | /api/admin/users | Crear usuario |
| PUT | /api/admin/users/{id} | Actualizar rol/estado |
| POST | /api/admin/users/{id}/deactivate | Desactivar usuario |
| GET | /api/admin/roles | Listar roles con permisos |
| PUT | /api/admin/roles/{id}/permissions | Actualizar permisos de un rol |

## 9 roles del sistema

`super_admin`, `admin_sistema`, `cliente`, `recepcionista`, `hotel_partner`, `gerente_hotel`, `revenue_manager`, `marketing_hotelero`, `auditor_datos`
