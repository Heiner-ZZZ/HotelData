# Tareas GA03 - HotelData Reservas

## Principio de ejecución

Estas tareas documentan GA03 sin cambiar el ETL validado, Airflow, PocketBase, MongoDB ni scripts de pipeline. La consistencia documental debe reflejar 32 CU exactos en 8 paquetes.

## Tareas técnicas ya representadas por GA03

- [x] Configurar tarea `TASK_NUMBER=03`.
- [x] Configurar `TARGET_RECORDS=300000`.
- [x] Usar colección PocketBase `hotel_reservation_events_03`.
- [x] Mantener MongoDB `hoteldata_hub`.
- [x] Mantener hecho principal `fact_hotel_reservations`.
- [x] Mantener 12 dimensiones activas.
- [x] Documentar flujo CSV -> PocketBase como preparación administrativa.
- [x] Documentar flujo PocketBase -> JSONL -> Parquet -> MongoDB como ETL principal.
- [x] Mantener DAG `hoteldata_reservas_03_pipeline`.
- [x] Mantener Docker y Redis como preparación futura, no como ejecución obligatoria.

## Tareas documentales

### TASK-001: Alinear requisitos GA03

- [x] `requirements.md` declara 32 CU exactos.
- [x] `requirements.md` declara 8 paquetes exactos.
- [x] `requirements.md` conserva datos reales GA03.
- [x] Login, roles, pagos, PMS, reservas reales, habitaciones, tarifas y CMS quedan planificados o parciales.

### TASK-002: Alinear diseño GA03

- [x] `design.md` separa modelo actual implementado y modelo futuro planificado.
- [x] `design.md` documenta 12 dimensiones activas.
- [x] `design.md` documenta `/etl-status` como interfaz administrativa ampliada.
- [x] `design.md` indica que Docker y Redis son preparación futura.

### TASK-003: Documentar 32 casos de uso

- [x] `docs/ga03/casos_uso_ga03.md` contiene CU01-CU32.
- [x] Cada CU incluye ID, paquete, nombre, actor principal, actores secundarios, prioridad, tipo, estado, propósito, descripción, 4 historias e imagen pendiente/no aplica.
- [x] Los CU se agrupan en 8 paquetes.
- [x] Los estados no inventan funcionalidades no implementadas.

### TASK-004: Crear diagrama de casos de uso

- [x] `docs/ga03/diagrama_casos_uso_ga03.md` contiene PlantUML embebido.
- [x] `diagrams/ga03_use_cases.puml` contiene diagrama renderizable.
- [x] El diagrama muestra 32 CU en 8 paquetes.
- [x] PocketBase y MongoDB aparecen como sistemas técnicos externos.

### TASK-005: Crear diseño de base de datos

- [x] `docs/ga03/diseno_base_datos_ga03.md` separa modelo actual implementado y modelo futuro planificado.
- [x] `diagrams/ga03_database.puml` contiene diagrama renderizable.
- [x] Se incluyen hechos, 12 dimensiones, control, documental/operativo actual y legado.
- [x] Se documentan colecciones futuras como planificadas.

### TASK-006: Documentar modelo futuro

- [x] `docs/ga03/modelo_futuro_ga03.md` explica seguridad, usuarios, viajero, partner central, inventario, tarifas, reservas, pagos, integraciones, Redis y Docker.
- [x] Todo elemento futuro queda marcado como planificado.

### TASK-007: Documentar Docker y Redis

- [x] `docs/ga03/docker_redis_plan.md` explica Docker y Redis como preparación futura.
- [x] `docker-compose.yml` queda como scaffolding.
- [x] `docker-compose.airflow.yml` queda opcional.
- [x] Redis no se conecta al ETL actual.

### TASK-008: Preparar PDF final

- [ ] Generar PDF final.
- [ ] Agregar link al video en primera página.
- [ ] Incluir diagrama de base de datos renderizado.
- [ ] Incluir diagrama de casos de uso renderizado.
- [ ] Incluir documentación de 32 CU.
- [ ] Incluir evidencias reales sin inventar resultados.

## Paquetes definitivos

1. Experiencia del cliente y búsqueda hotelera.
2. Cuenta, sesión y perfil de usuario.
3. Core de reservas hoteleras.
4. Gestión hotelera / Partner Central.
5. Habitaciones, inventario y disponibilidad.
6. Tarifas, promociones y revenue.
7. Analytics, BI y toma de decisiones.
8. Administración, datos, ETL y gobierno.

## Estados definitivos por CU

- Implementado: CU25, CU29, CU30, CU32.
- Parcial: CU01, CU02, CU03, CU04, CU12, CU24, CU26, CU27, CU28.
- Planificado: CU05, CU06, CU07, CU08, CU09, CU10, CU11, CU13, CU14, CU15, CU16, CU17, CU18, CU19, CU20, CU21, CU22, CU23, CU31.
