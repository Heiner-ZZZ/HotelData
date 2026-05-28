# Criterios de aceptación GA03 - HotelData Reservas

## CA-001: Configuración real documentada

La documentación debe conservar:

- `TASK_NUMBER=03`
- `TARGET_RECORDS=300000`
- `POCKETBASE_COLLECTION=hotel_reservation_events_03`
- MongoDB `hoteldata_hub`
- DAG `hoteldata_reservas_03_pipeline`
- Hecho `fact_hotel_reservations`
- 12 dimensiones activas
- CSV -> PocketBase como preparación administrativa
- PocketBase -> JSONL -> Parquet -> MongoDB como ETL principal

## CA-002: Casos de uso alineados

La documentación debe indicar exactamente **32 CU agrupados en 8 paquetes**. No debe conservar cifras anteriores ni rangos ampliados.

Los paquetes obligatorios son:

1. Experiencia del cliente y búsqueda hotelera.
2. Cuenta, sesión y perfil de usuario.
3. Core de reservas hoteleras.
4. Gestión hotelera / Partner Central.
5. Habitaciones, inventario y disponibilidad.
6. Tarifas, promociones y revenue.
7. Analytics, BI y toma de decisiones.
8. Administración, datos, ETL y gobierno.

## CA-003: Estados honestos de implementación

La documentación debe clasificar:

- Implementado: CU25, CU29, CU30, CU32.
- Parcial: CU01, CU02, CU03, CU04, CU12, CU24, CU26, CU27, CU28.
- Planificado: CU05, CU06, CU07, CU08, CU09, CU10, CU11, CU13, CU14, CU15, CU16, CU17, CU18, CU19, CU20, CU21, CU22, CU23, CU31.

No se debe marcar como implementado:

- Login real.
- Roles y permisos reales.
- Pagos reales.
- PMS / Channel Manager.
- Reservas transaccionales reales.
- Habitaciones e inventario operativos.
- Tarifas operativas.
- CMS/Partner Central completo.

## CA-004: Documentación de CU completa

`docs/ga03/casos_uso_ga03.md` debe contener CU01-CU32. Cada CU debe incluir:

- ID.
- Paquete.
- Nombre.
- Actor principal.
- Actores secundarios.
- Prioridad 1-10.
- Tipo: Operativo, Táctico o Estratégico.
- Estado: Implementado, Parcial o Planificado.
- Propósito.
- Descripción.
- 4 historias de usuario.
- Imagen: [Pendiente] o [No aplica en GA03].

## CA-005: Diagramas actualizados

Debe existir:

- `docs/ga03/diagrama_casos_uso_ga03.md`
- `docs/ga03/diseno_base_datos_ga03.md`
- `diagrams/ga03_use_cases.puml`
- `diagrams/ga03_database.puml`

Los diagramas deben reflejar 32 CU y el modelo actual/futuro sin sobrecargar casos de uso con pasos internos de ETL.

## CA-006: Modelo de base de datos actual y futuro

El modelo actual debe incluir:

- `fact_hotel_reservations`
- `fact_hotel_events`
- 12 dimensiones activas
- `etl_executions`
- `data_quality_reports`
- `rejected_records`
- Colecciones documentales/operativas actuales
- Colecciones legadas `dim_countries` y `dim_date`

El modelo futuro debe quedar marcado como planificado, no implementado.

## CA-007: Docker y Redis

Docker y Redis deben documentarse como preparación futura:

- Docker no es requisito ejecutado de GA03.
- Redis no está conectado al ETL actual.
- Redis se proyecta para cache de dashboard, búsquedas frecuentes, sesiones futuras, estado temporal de jobs y rate limiting futuro.

## CA-008: PDF final

El PDF final debe contener:

- Link al video en primera página.
- Alcance GA03.
- Configuración real.
- Diagrama de base de datos.
- Diagrama de casos de uso.
- Documentación de 32 CU.
- Evidencias sugeridas.
- Resultados obtenidos únicamente si existen evidencias reales.
- Próximos pasos.

## CA-009: No inventar ejecución

La documentación no debe inventar que Docker fue ejecutado, que Redis está activo, que login existe, que pagos funcionan, que PMS está conectado o que se ejecutó un pipeline si no hay evidencia real.

## CA-010: Cierre SDD

GA03 queda consistente cuando requirements, design, tasks, acceptance criteria, documentos GA03 y diagramas indican 32 CU exactos, 8 paquetes exactos y estado real del núcleo implementado: datos, analítica, CRUD analítico, auditoría y ETL.
