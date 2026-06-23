# Tareas: ETL - Fact Tables

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Implementación

- [ ] T001 Verificar que `ta02_fact.py` construye fact_hotel_reservations con batch insert de 5k documentos
- [ ] T002 Verificar validaciones: campos obligatorios, price_usd > 0, occupancy válida
- [ ] T003 Verificar que srch_id duplicados se rechazan
- [ ] T004 Verificar que registros rechazados van a `rejected_records`

## Fase 2: Calidad

- [ ] T005 Verificar conteo de insertados vs rechazados en reporte
- [ ] T006 Verificar que rejected_records contiene raw_record + rejection_reason

## Fase 3: Validación

- [ ] T007 Ejecutar pipeline de prueba y verificar conteos
