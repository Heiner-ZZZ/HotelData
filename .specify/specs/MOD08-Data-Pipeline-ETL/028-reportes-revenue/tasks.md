# Tareas: Reportes de Revenue

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar `services/reports.py`: `get_revenue_summary(periodo)`, `get_top_hotels()`, `get_top_destinations()`
- [ ] T002 Implementar agregaciones con MongoDB aggregation pipeline + $lookup
- [ ] T003 Calcular KPIs: eventos totales, reservas, clicks, revenue, precio promedio

## Fase 2: Frontend

- [ ] T004 [P] Crear dashboard con cards de KPIs
- [ ] T005 [P] Tablas de top hoteles, destinos y países
- [ ] T006 [P] Filtros por período (día, semana, mes, trimestre)

## Fase 3: Validación

- [ ] T007 Verificar que datos coinciden con fact_hotel_reservations
