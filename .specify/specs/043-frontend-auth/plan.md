# Plan de Implementación: Frontend - Autenticación

**Branch**: `043-frontend-auth` | **Spec**: [spec.md](spec.md)

## Componentes (existente)

| Componente | Archivo | Propósito |
|-----------|---------|-----------|
| LoginPage | `features/auth/pages/login/` | Formulario email + password |
| AuthGuard | `core/guards/auth.guard.ts` | Protege rutas sin sesión |
| RoleGuard | `core/guards/role.guard.ts` | Protege rutas por rol |
| AuthInterceptor | `core/interceptors/auth.interceptor.ts` | Adjunta cookie de sesión |
| AccessNav | `shared/ui/access-nav/` | Navegación adaptativa |
| SidebarNav | `shared/ui/sidebar-nav/` | Sidebar por rol |

## Rutas

| Ruta | Componente | Guard |
|------|-----------|-------|
| /auth/login | LoginPage | — |
| /auth/logout | — (acción) | AuthGuard |
| /403 | ForbiddenPage | — |
| /* | (resto) | AuthGuard + RoleGuard |

## Entregables

Este spec documenta la UI de autenticación existente y asegura que todos los componentes estén correctamente implementados y probados.
