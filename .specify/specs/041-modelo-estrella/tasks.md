# Tareas: Modelo Estrella

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Verificación de estructura

- [ ] T001 Verificar que existen las 12 colecciones de dimensiones en MongoDB
- [ ] T002 Verificar que existen fact_hotel_reservations y fact_hotel_events
- [ ] T003 Verificar que existen colecciones de control (etl_executions, data_quality_reports, rejected_records)

## Fase 2: Integridad referencial

- [ ] T004 Verificar que fact tables referencian dimensiones por key field
- [ ] T005 Verificar que dimensiones se cargan primero (upsert) y hechos después

## Fase 3: Documentación

- [ ] T006 Documentar grain de cada fact table
- [ ] T007 Documentar relaciones entre dimensiones y hechos
