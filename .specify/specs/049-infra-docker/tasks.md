# Tareas: Infraestructura Docker

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Verificación

- [ ] T001 Verificar que docker-compose.yml tiene 6 servicios con health checks
- [ ] T002 Verificar que versiones están pinneadas
- [ ] T003 Verificar que cada servicio tiene Dockerfile o imagen específica

## Fase 2: Volúmenes

- [ ] T004 Verificar volúmenes persistentes (mongo_data, redis_data, pb_data)
- [ ] T005 Verificar red compartida entre servicios

## Fase 3: Validación

- [ ] T006 Verificar que `docker-compose up` levanta todos los servicios
- [ ] T007 Verificar health checks responden correctamente
