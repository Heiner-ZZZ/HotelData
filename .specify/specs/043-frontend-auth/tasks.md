# Tareas: Frontend - Autenticación

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Verificación de componentes existentes

- [ ] T001 Verificar que LoginPage funciona con email + password
- [ ] T002 Verificar que AuthGuard redirige a /auth/login sin sesión
- [ ] T003 Verificar que RoleGuard redirige a /403 si rol no tiene permiso
- [ ] T004 Verificar que AuthInterceptor envía cookie en cada request

## Fase 2: Navegación

- [ ] T005 Verificar que SidebarNav se adapta según rol
- [ ] T006 Verificar que AccessNav muestra solo opciones permitidas

## Fase 3: Validación

- [ ] T007 Verificar flujo de logout (destruye sesión, redirige a login)
