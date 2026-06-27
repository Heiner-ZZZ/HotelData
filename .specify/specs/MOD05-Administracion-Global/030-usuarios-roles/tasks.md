# Tareas: Usuarios, Roles y Permisos

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar `admin/services/users.py`: `list_users(filters)`, `create_user()`, `update_user()`, `deactivate_user()`
- [ ] T002 Implementar `admin/services/roles.py`: `list_roles()`, `update_role_permissions()`
- [ ] T003 Definir 9 roles con permisos en `route_permissions.py`

## Fase 2: Frontend

- [ ] T004 [P] Crear `UsersPage` con tabla y filtros por rol/estado
- [ ] T005 [P] Modal de edición de usuario (rol, activo/inactivo)
- [ ] T006 [P] Crear `RolesPage` con matriz de permisos por rol

## Fase 3: Validación

- [ ] T007 Verificar que guards de Angular protegen rutas por rol
- [ ] T008 Verificar que sidebar/access-nav se adapta según rol
