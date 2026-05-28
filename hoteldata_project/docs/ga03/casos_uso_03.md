# Casos de uso GA03

Este documento se conserva por compatibilidad con entregas previas. La versión vigente y completa está en:

- `docs/ga03/casos_uso_ga03.md`
- `docs/ga03/diagrama_casos_uso_ga03.md`
- `diagrams/ga03_use_cases.puml`

## Decisión vigente

GA03 documenta exactamente 32 casos de uso agrupados en 8 paquetes:

1. Experiencia del cliente y búsqueda hotelera.
2. Cuenta, sesión y perfil de usuario.
3. Core de reservas hoteleras.
4. Gestión hotelera / Partner Central.
5. Habitaciones, inventario y disponibilidad.
6. Tarifas, promociones y revenue.
7. Analytics, BI y toma de decisiones.
8. Administración, datos, ETL y gobierno.

## Configuración real

- `TASK_NUMBER=03`
- `TARGET_RECORDS=300000`
- `POCKETBASE_COLLECTION=hotel_reservation_events_03`
- MongoDB: `hoteldata_hub`
- DAG: `hoteldata_reservas_03_pipeline`
- Flujo administrativo: CSV -> PocketBase
- ETL principal: PocketBase -> JSONL -> Parquet -> MongoDB
- Hecho principal: `fact_hotel_reservations`
- Dimensiones activas: 12

## Estados

- Implementado: CU25, CU29, CU30, CU32.
- Parcial: CU01, CU02, CU03, CU04, CU12, CU24, CU26, CU27, CU28.
- Planificado: CU05, CU06, CU07, CU08, CU09, CU10, CU11, CU13, CU14, CU15, CU16, CU17, CU18, CU19, CU20, CU21, CU22, CU23, CU31.

No se documenta como implementado login real, roles reales, pagos, PMS, reservas transaccionales, habitaciones, tarifas operativas ni CMS hotelero.
