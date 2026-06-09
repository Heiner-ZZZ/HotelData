# Requisitos GA03 - HotelData Reservas

## Objetivo

GA03 documenta y consolida el avance de **HotelData Hub Analytics** como plataforma web/responsiva de reservas hoteleras inspirada en Expedia/Trivago.

GA03 no crea una app separada. Representa una fase del sistema completo con avance funcional aproximado del 25%, centrado en datos, analítica, CRUD analítico, auditoría y ETL.

## Configuración real GA03

- `TASK_NUMBER=03`
- `TARGET_RECORDS=300000`
- `POCKETBASE_COLLECTION=hotel_reservation_events_03`
- MongoDB database: `hoteldata_hub`
- DAG Airflow: `hoteldata_reservas_03_pipeline`
- Hecho principal: `fact_hotel_reservations`
- Dimensiones activas: 12
- Preparación administrativa: CSV -> PocketBase
- ETL principal: PocketBase -> JSONL -> Parquet -> MongoDB

## Alcance implementado real

El núcleo implementado de GA03 corresponde a:

- Preparación de fuente operacional desde CSV hacia PocketBase.
- Validación de `TARGET_RECORDS=300000`.
- Pipeline ETL principal hacia MongoDB.
- Generación de JSONL y Parquet.
- Carga de `fact_hotel_reservations` y dimensiones activas.
- Reportes de ejecución, calidad y validación.
- Panel `/etl-status` ampliado para GA03.
- Dashboard, consultas, CRUD analítico y auditoría existentes.

## Alcance planificado

Quedan como planificados o parciales, según corresponda:

- Login real, sesiones, roles y permisos.
- Pagos, transacciones, reembolsos y facturas.
- Reservas transaccionales reales.
- Partner Central completo.
- Habitaciones, inventario, disponibilidad y tarifas operativas.
- CMS hotelero, imágenes y políticas gestionadas por partner.
- PMS / Channel Manager.
- Redis como cache o estado temporal.
- Docker como despliegue ejecutado.

Docker y Redis quedan como preparación futura documentada, no como requisito ejecutado de GA03.

## Casos de uso requeridos

GA03 debe documentar exactamente **32 casos de uso agrupados en 8 paquetes**.

### Paquete 1: Experiencia del cliente y búsqueda hotelera

- CU01 Buscar hoteles por destino, fecha y ocupación.
- CU02 Filtrar hoteles por precio, estrellas, promoción y servicios.
- CU03 Consultar detalle de hotel.
- CU04 Comparar hoteles disponibles.

### Paquete 2: Cuenta, sesión y perfil de usuario

- CU05 Registrarse como usuario.
- CU06 Iniciar sesión y validar rol.
- CU07 Gestionar perfil de viajero.
- CU08 Consultar historial de actividad.

### Paquete 3: Core de reservas hoteleras

- CU09 Crear solicitud de reserva.
- CU10 Consultar estado de reserva.
- CU11 Cancelar reserva según política.
- CU12 Registrar reserva manual.

### Paquete 4: Gestión hotelera / Partner Central

- CU13 Administrar perfil del hotel.
- CU14 Administrar imágenes y contenido del hotel.
- CU15 Administrar políticas del hotel.
- CU16 Consultar rendimiento de propiedades.

### Paquete 5: Habitaciones, inventario y disponibilidad

- CU17 Administrar tipos de habitación.
- CU18 Administrar inventario por calendario.
- CU19 Bloquear fechas no disponibles.
- CU20 Sincronizar disponibilidad con PMS / Channel Manager.

### Paquete 6: Tarifas, promociones y revenue

- CU21 Administrar planes tarifarios.
- CU22 Configurar tarifas por fecha.
- CU23 Crear campañas promocionales.
- CU24 Evaluar impacto de promociones.

### Paquete 7: Analytics, BI y toma de decisiones

- CU25 Consultar dashboard de reservas.
- CU26 Analizar conversión búsqueda-click-reserva.
- CU27 Analizar ingresos brutos por hotel y destino.
- CU28 Analizar comportamiento por país visitante y canal.

### Paquete 8: Administración, datos, ETL y gobierno

- CU29 Ejecutar pipeline ETL de reservas.
- CU30 Validar Parquet, calidad y registros rechazados.
- CU31 Administrar usuarios, roles y permisos.
- CU32 Consultar auditoría y trazabilidad de ejecuciones.

## Estado esperado de los CU

- Implementado: CU25, CU29, CU30, CU32.
- Parcial: CU01, CU02, CU03, CU04, CU12, CU24, CU26, CU27, CU28.
- Planificado: CU05, CU06, CU07, CU08, CU09, CU10, CU11, CU13, CU14, CU15, CU16, CU17, CU18, CU19, CU20, CU21, CU22, CU23, CU31.

La clasificación debe ser honesta: no se debe marcar como implementado login, pagos, PMS, tarifas operativas, habitaciones, partner central ni reservas reales si no existen.

## Requisitos documentales

Cada CU debe incluir:

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
- 4 historias de usuario en formato: Como [rol], quiero [acción], para [beneficio].
- Imagen del caso de uso implementado: [Pendiente] o [No aplica en GA03].

## Requisitos de diagramas

GA03 debe entregar:

- Diagrama de base de datos con modelo actual implementado y modelo futuro planificado.
- Diagrama de casos de uso con 32 CU y 8 paquetes.
- PlantUML en Markdown y archivos `.puml` en `diagrams/`.

## Requisitos de PDF

El PDF final debe incluir en primera página un espacio para link al video. También debe incluir alcance, configuración real, flujo, diagramas, descripción de 32 CU, evidencias sugeridas, resultados sin inventar y próximos pasos.
