# Tareas: Monitoreo de Servicios

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar `GET /api/admin/health/details` con verificación de MongoDB, Redis, PocketBase
- [ ] T002 Verificar que GET /health retorna status general

## Fase 2: Frontend

- [ ] T003 [P] Crear `MonitoringPage` con cards por servicio (verde/rojo)
- [ ] T004 [P] Mostrar última comprobación y tiempo de respuesta

## Fase 3: Validación

- [ ] T005 Probar health check con servicios caídos
