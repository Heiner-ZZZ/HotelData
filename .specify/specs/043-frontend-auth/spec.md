# Especificacion: Frontend - Autenticacion

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O01, CU-O28, CU-O29 (Login, logout, cambio de contrasena y perfil)

## 1. Objetivo

Componentes frontend de autenticacion: login page, guards, interceptors, layouts por rol.

## 2. Componentes

| Componente | Ruta | Descripcion |
|------------|------|-------------|
| LoginPage | /auth/login | Formulario de inicio de sesion |
| AuthGuard | - | Protege rutas que requieren autenticacion |
| RoleGuard | - | Protege rutas segun rol del usuario |
| AuthInterceptor | - | Adjunta cookie de sesion a requests |
| AccessNav | - | Navegacion adaptativa por rol |
| SidebarNav | - | Sidebar con modulos segun rol |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | LoginPage con formulario de email + contrasena | Alta |
| RF-002 | AuthGuard redirige a /auth/login si no hay sesion | Alta |
| RF-003 | RoleGuard redirige a /403 si el rol no tiene permiso | Alta |
| RF-004 | AuthInterceptor envia cookie en cada request | Alta |
| RF-005 | Sidebar/access-nav se adapta segun el rol | Alta |

## 4. Dependencias

- frontend/src/app/features/auth/
- frontend/src/app/core/guards/
- frontend/src/app/core/interceptors/
