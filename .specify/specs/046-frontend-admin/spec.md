# Especificacion: Frontend - Administracion

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T09, CU-T10, CU-T11 (Usuarios, roles, auditoria, monitoreo, permisos)

## 1. Objetivo

UI de administracion: gestion de usuarios y roles, panel de auditoria, monitoreo de servicios.

## 2. Componentes

| Componente | Ruta | CU asociado |
|------------|------|-------------|
| UsersPage | /system/users | CU-T09 |
| RolesPage | /system/permissions | CU-T09 |
| AuditPage | /system/audit | CU-T10 |
| MonitoringPage | /system/monitoring | CU-T11 |
| OwnershipListPage | /ownership/users | CU-T09 |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | UsersPage con tabla de usuarios, activar/desactivar, cambiar rol | Alta |
| RF-002 | RolesPage con matriz de permisos por rol | Alta |
| RF-003 | AuditPage con tabla de actividad filtrable | Alta |
| RF-004 | MonitoringPage con health checks de servicios | Media |

## 4. Dependencias

- frontend/src/app/features/system-admin/
- system-admin.routes.ts
