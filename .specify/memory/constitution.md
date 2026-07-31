# Constitución de HotelData

> **Dominio**: Plataforma híbrida de gestión hotelera y analítica para grupos multi-propiedad.
>
> **Propósito de negocio**: Proveer un sistema unificado donde los hoteleros gestionan su operación diaria (inventario de habitaciones, tarifas, reservas, check-in/out, contenido de propiedad) y simultáneamente obtienen una fuente única de verdad para analítica de reservas, ingresos, ocupación y comportamiento de búsqueda a nivel de portafolio.
>
> **Naturaleza del sistema dual**:
> 1. **Operacional** — CRUD completo para que *property managers* definan tipos de habitación, calendarios de inventario, planes de tarifa, promociones, reservas y check-in/out. Opera directamente sobre MongoDB.
> 2. **Analítico** — Pipeline ETL que ingiere datos desde PocketBase (proxy de fuente externa), los transforma a un modelo estrella (dimensiones + hechos) y los carga en MongoDB para dashboards y BI.

---

## 0 · Estado del Documento

| Campo | Valor |
|-------|-------|
| **Versión** | 0.9 (enmienda content-additive sobre 0.8) |
| **Ratificada** | 2026-06-20 |
| **Última enmienda** | 2026-07-28 |
| **Última verificación contra stack** | 2026-07-28 (commit `49d4450`) |
| **Próxima revisión mayor (1.0)** | Pendiente — requiere evento de ratificación explícito con stakeholders `super_admin` y `admin_sistema` |
| **Audiencia** | Toda persona o agente (humano o LLM) que modifique código, spec o contrato de datos en este repositorio |

**Declaración de supremacía**: En caso de conflicto, esta Constitución prevalece sobre `.specify/specs/*`, `docs/library/*` y `AGENTS.md`. Toda spec que contradiga un principio debe enmendar primero la Constitución.

---

## 1 · Preámbulo

Este documento codifica las **leyes no negociables** que rigen HotelData. Su propósito es:

1. **Prevenir drift arquitectónico**. Cada nueva feature debe poder justificarse contra un principio vigente. Si no encaja, primero se enmienda la Constitución.
2. **Hacer ejecutables los invariantes**. Cada principio lleva una etiqueta `[Enforced By: ...]` que apunta al gate concreto (test, lint, CI check, gate de PR, gate de revisión) que lo valida. Un principio sin gate es un deseo, no una ley.
3. **Proveer un único punto de verdad** para: versiones del stack, separación operacional/analítica, modelo de datos, contratos de datos y cadencia de gobernanza.
4. **Proteger contra alucinaciones del LLM**. Esta Constitución declara explícitamente lo que el sistema **NO es** (§12) y dónde encontrar los detalles de implementación (`knowledge.md`, `.specify/specs/`, ADRs).

**Tono**: declarativo (`MUST`, `SHALL`, `NEVER`, `SHALL NOT`). Lenguaje prescriptivo, no sugerente. No se usan "debería" ni "preferentemente" — la Constitución prescribe.

---

## 2 · Glosario

> Definiciones operativas para evitar ambigüedad entre specs, código y LLM. Orden alfabético para lookup rápido.

| Término | Definición |
|---------|-----------|
| **ADR** | Architecture Decision Record — archivo `.specify/decisions/ADR-NNNN-*.md` que documenta una decisión arquitectónica con contexto, alternativas y consecuencias. §14.5. |
| **Capa Analítica** | Pipeline ETL batch (Airflow + Python) que lee PocketBase y produce dimensiones + hechos en MongoDB. Lectura intensiva, escritura por lotes. |
| **Capa Operacional** | Frontend (Angular) + FastAPI + escritura directa a MongoDB. CRUD activo sobre datos que el property manager crea/actualiza. |
| **Data Contract** | Acuerdo explícito por dataset: schema esperado, owner, SLA de freshness, fuente y consumidor(es). §4.4 los enumera. |
| **`dim_*`** | Colección de dimensiones — atributos descriptivos que rodean los hechos. Se hace `upsert` por clave natural. |
| **Dual-Write** | Patrón donde una mutación operacional (ej. crear reserva, emitir factura) escribe simultáneamente en la colección operacional Y en su `fact_*` correspondiente en la misma request. Si falla el segundo write, se compensa o se registra en `etl_executions` para reconciliación. |
| **Ensure_indexes** | Llamada obligatoria en cada módulo operacional al arrancar — crea índices únicos compuestos, TTL y sorted para garantizar consistencia. |
| **`fact_*`** | Colección de hechos — un registro = un evento medible. Granularidad alta. Se inserta en batch (5k documentos). |
| **Gerente_hotel** | Rol con `mode=single` en `PropertyContextService`. Tiene exactamente UNA propiedad asignada. Todo sidebar link debe llevar `?prop_id=N`. |
| **Hotel_partner / Super_admin** | Roles con `mode=all` o `mode=multi`. Pueden alternar entre propiedades vía property-selector. |
| **Operational-First** | Principio rector: cualquier dato de negocio nace en la Capa Operacional con validación y auditoría. La Capa Analítica es derivada, no fuente. |
| **`rejected_records`** | Colección de control que captura todo registro que el ETL rechaza, con `reason` + `raw_record` + `execution_id`. Nunca se descarta silenciosamente. |
| **spec-kit cascade** | Constitución → Spec → Plan → Tasks → Code. Cada nivel deriva del anterior. No se promueve código sin haber pasado tasks.md. |

---

## 3 · Principios Fundamentales (Leyes No Negociables)

> Cada principio lleva una etiqueta `[Enforced By:]` que apunta al gate ejecutable. Un `[Manual]` significa que el reviewer lo valida en el PR.

### I. Python-First con Separación de Capas

```
Capa Operacional (CRUD directo):
  Web UI → FastAPI → Python (validación + auditoría) → MongoDB

Capa Analítica (ETL batch):
  PocketBase → Python → JSONL → Parquet → Dimensiones (upsert) + Hechos (batch) → MongoDB
```

- **NEVER** `BashOperator` en DAGs de Airflow.
- **NEVER** MongoDB Aggregation Pipeline como transformación ETL principal. `aggregate()` solo para dashboards/consultas *post-carga*.
- **NEVER** transformaciones SQL manuales. Toda limpieza, deduplicación, coerción de tipos y resolución de claves ocurre en Python antes de llegar a MongoDB.
- **SHALL** usar batch streaming. Chunk size: 50,000 filas. Batch insert size: 5,000 documentos.
- **SHALL** escribir datos operacionales directamente vía API con validación en Python + auditoría + control de concurrencia.
- **SHALL** procesar datos analíticos exclusivamente vía el pipeline ETL desde PocketBase.
- `[Enforced By: test_etl_rules.py, test_dag_boundaries.py]`

### II. Límite Airflow ↔ Web

```
┌─────────────────────────────────────────────────┐
│  Airflow (orquestador ETL)                      │
│  Solo importa: src/etl/, src/database/, config/ │
│  NO importa: src.app, templates, static, JS     │
├─────────────────────────────────────────────────┤
│  Web (FastAPI + Angular)                        │
│  Sirve: API operacional + API analítica (lectura)│
│  Nunca ejecuta ETL en operación normal          │
└─────────────────────────────────────────────────┘
```

- **NEVER** importar `src.app`, `templates`, `static`, HTML, CSS ni JS desde un DAG.
- **NEVER** ejecutar lógica ETL desde la capa web durante operación normal (solo lee resultados transformados o escribe operacional directo).
- `[Enforced By: test_dag_boundaries.py]`

### III. Normalización Multi-Propiedad

> La industria hotelera opera con 30 a 70 sistemas diferentes por grupo (PMS, CRS, Channel Manager, RMS, POS, CRM, BI, mantenimiento, finanzas). El problema central de la industria es que los datos no hablan el mismo idioma, no la falta de datos.

HotelData Hub resuelve esto en dos frentes:
- **Operacional**: Interfaz unificada donde property managers gestionan habitaciones, tarifas, inventario y reservas con un modelo consistente entre propiedades.
- **Analítica**: Traducción de fuentes externas (PocketBase como proxy de PMS/CRS heterogéneos) a un esquema estrella estable, normalizando rate codes, segmentos, canales y métricas.

`[Enforced By: dim_* uniqueness en test_schema.py, manual]`

### IV. Calidad de Datos Continua, No Puntual

- **SHALL** generar un reporte de calidad por cada ejecución ETL: conteo de rechazados, campos faltantes, valores inválidos, nulls por columna.
- **SHALL** registrar cada ejecución en `etl_executions` con `execution_id`, `status`, timestamps, conteos y resumen de errores.
- **NEVER** descartar un registro silenciosamente. Todo rechazo va a `rejected_records` con `reason` + `raw_record` + `execution_id`.
- **SHALL** almacenar reportes en dos lugares: filesystem (`data/reports/`) para polling + MongoDB (`data_quality_reports`) para histórico.
- `[Enforced By: data_quality_reports schema, test_transformations.py]`

### V. Desarrollo Basado en Evidencia — Matriz de Trazabilidad

Toda tarea **SHALL** declarar su relación con entregas existentes:

```md
## Relacion con entregas anteriores
| ID | Elemento afectado | Tipo de cambio | Archivo/ruta/coleccion | Estado anterior | Estado nuevo | Criterio de aceptacion |
|----|------------------|----------------|----------------------|----------------|-------------|----------------------|
| IMP-001 | ... | conserva/agrega/modifica/reemplaza/elimina | ... | ... | ... | ... |
```

- Los tipos de cambio son cinco: `conserva`, `agrega`, `modifica`, `reemplaza`, `elimina` — no hay otro.
- Tareas sin matriz de impacto **NO** se consideran completas.
- `[Enforced By: PR template, manual]`

### VI. Mejora Progresiva — Extender, Nunca Reemplazar

- Pipelines nuevos (GA03) **SHALL** extender el patrón TA02: PocketBase → JSONL → Parquet → Dimensiones + Hechos → MongoDB.
- Pipelines legacy (TAF01) **SHALL** mantenerse como línea base — CSV → Python → MongoDB.
- Compatibilidad hacia atrás es obligatoria salvo que se documente y apruebe explícitamente en la matriz de impacto.
- `[Enforced By: backward-compatibility tests, manual]`

### VII. Operacional-First — Dual-Write a Analíticas

- Datos de operación hotelera (reservas, inventario, tarifas, reseñas, facturas, pagos) **SHALL** escribirse directamente vía FastAPI a MongoDB. No esperan al batch ETL.
- Cada módulo operacional que genera datos de negocio **SHALL** implementar dual-write a su `fact_*` en la misma request, con transacción lógica o compensación.
- Colecciones operacionales **SHALL** invocar `ensure_indexes` en startup (unique compuestos, TTL, sorted).
- Colecciones operacionales **SHALL** usar `_id` de string semántico (ej. `{hotel_id}_{date}` en inventario) para upserts idempotentes desde el ETL.
- Concurrencia: optimistic locking (campo `version`) donde API y ETL puedan escribir el mismo registro.
- `[Enforced By: test_schema.py (ensure_indexes), runtime dual-write assertions]`

---

## 4 · Modelo de Dominio

### 4.1 Flujo del Sistema (Diagrama Canónico)

```
  ┌─────────────────────────────────────────────────────────────────┐
  │                    CAPA OPERACIONAL                             │
  │  (Partner Module — CRUD directo sobre MongoDB)                 │
  │                                                                 │
  │  Property Manager → Web UI → FastAPI → MongoDB                 │
  │    • Tipos de habitación (room_types)                          │
  │    • Inventario por fecha (room_inventory_calendar)             │
  │    • Planes de tarifa (rate_plans)                              │
  │    • Calendario de tarifas (hotel_rate_calendar)                │
  │    • Promociones (promotion_campaigns)                          │
  │    • Reservas (booking_orders)                                  │
  │    • Check-in / Check-out                                       │
  │    • Contenido de propiedad (hotel_content_pages,               │
  │      hotel_images, hotel_policies)                              │
  │    • Reseñas (reviews) ← fact_reviews (dual-write)             │
  │    • Facturación (reservation_invoices) → fact_invoices (dw)   │
  │    • Pagos (reservation_payments) → fact_payments (dw)         │
  └──────────────────────┬──────────────────────────────────────────┘
                        │ (A) CRUD operacional sobreescribe dimensión
                        ▼     cuando el registro existe en ambas capas
  ┌─────────────────────────────────────────────────────────────────┐
  │                    CAPA ANALÍTICA                               │
  │  (ETL Pipeline — PocketBase → JSONL → Parquet → MongoDB)       │
  │                                                                 │
  │  PocketBase (datos fuente) → ETL → Star Schema                 │
  │    • 12 dimensiones (dim_hotels, dim_dates, ...)                │
  │    • Fact tables legacy (fact_hotel_events,                     │
  │      fact_hotel_reservations)                                   │
  │    • Fact tables dual-write (fact_reviews,                      │
  │      fact_reservation_invoices, fact_reservation_payments)      │
  │    • Dashboards de conversión, revenue, ocupación               │
  └──────────┬──────────────────────────────────────────────────────┘
            │ (B) ETL batch actualiza dimensiones con datos históricos
            │     que la capa operacional no cubre (dim_dates, geo)
            ▼
```

### 4.2 Datos de Entrada

**Operacionales** (creados por el usuario del sistema):
- Tipos de habitación, inventario y blackouts
- Planes de tarifa y calendario de precios
- Promociones y códigos de cupón
- Reservas de huéspedes con check-in/out
- Contenido de propiedad (descripciones, imágenes, políticas)

**Analíticos** (ingresados vía ETL desde fuente externa):
- Dataset de eventos de búsqueda y reserva al estilo Expedia/Kaggle
- Cargado inicialmente a PocketBase desde CSV
- Procesado a través del pipeline hacia el modelo estrella

### 4.3 Modelo Estrella (Star Schema)

```
┌──────────────────────────────────────────────────────────┐
│                fact_hotel_reservations                   │
│  Un registro = un evento de búsqueda en el sitio con     │
│  indicadores de click y reserva. Grain: sesión-búsqueda  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Dimensiones circundantes (12):                          │
│  dim_hotels, dim_destinations, dim_visitor_countries,    │
│  dim_sites, dim_dates, dim_promotions, dim_click_status, │
│  dim_reservation_status, dim_occupancy_profile,          │
│  dim_stay_length_category, dim_booking_window_category,  │
│  dim_price_category                                      │
└──────────────────────────────────────────────────────────┘
```

| `dim_*` | Clave natural | Descripción |
|---------|---------------|-------------|
| `dim_hotels` | `prop_id` | Propiedades hoteleras con datos de calidad y override |
| `dim_destinations` | `srch_destination_id` | Destinos de búsqueda |
| `dim_visitor_countries` | `visitor_location_country_id` | Países de visitantes |
| `dim_sites` | `site_id` | Canales/sitios de origen |
| `dim_dates` | `date_key` (YYYYMMDD) | Calendario |
| `dim_promotions` | `promotion_flag` | Flag promoción |
| `dim_click_status` | `click_bool` | Click sí/no |
| `dim_reservation_status` | `reserva_bool` | Reserva sí/no |
| `dim_occupancy_profile` | `occupancy_profile_id` | Perfil ocupación |
| `dim_stay_length_category` | `stay_length_category_id` | Estancia corta/media/larga |
| `dim_booking_window_category` | `booking_window_category_id` | Ventana reserva |
| `dim_price_category` | `price_category_id` | Precio bajo/medio/alto/premium |

### 4.4 Contratos de Datos (Data Contracts — Estilo Data Mesh)

> Cada dataset publicado por el sistema tiene un contrato explícito: schema, owner, SLA, fuente y consumidores.

| Dataset | Schema canónico | Owner | SLA de freshness | Fuente | Consumidores |
|---------|-----------------|-------|------------------|--------|--------------|
| `dim_hotels` | `prop_id, name, brand, rating, review_score, country` | `hotel_partner` | < 24h post-extracción ETL; write-through desde CRUD operacional sobreescribe cuando el registro existe en ambas capas (gana operacional por Principio VII) | ETL como fuente dimensional + CRUD operacional como write-through | Dashboards revenue, occupancy, comparativa |
| `fact_hotel_reservations` | `srch_id, date_time, prop_id, price_usd, click_bool, reserva_bool` | `auditor_datos` | < 4h post-extracción | ETL desde PocketBase | Dashboards de conversión, A/B testing |
| `booking_orders` | `_id, prop_id, guest_id, check_in, check_out, status, total` | `gerente_hotel` | Real-time (write-through) | CRUD operacional | Reception, ownership, account |
| `fact_reviews` | `review_id, booking_id, prop_id, rating, written_at` | `hotel_partner` | < 5 min (dual-write desde `reviews`) | Dual-write operacional | Dashboard reputación, NPS |
| `fact_reservation_invoices` | `invoice_id, booking_id, subtotal, taxes, issued_at` | `gerente_hotel` | < 5 min (dual-write) | Dual-write operacional | Revenue reports, COGS |
| `fact_reservation_payments` | `payment_id, booking_id, amount, method, paid_at` | `gerente_hotel` | < 5 min (dual-write) | Dual-write operacional | Cash flow, dashboard financiero |

---

## 5 · Catálogo de Servicios (Stack Real, Verificado el 2026-07-28)

> Las versiones aquí declaradas son vinculantes. Cualquier cambio pasa por un PR que actualice simultáneamente esta tabla, el `requirements.txt`/`package.json` y la fecha de verificación.

### 5.1 Stack Backend

| Componente | Tecnología | Versión | Rol |
|-----------|-----------|---------|-----|
| Runtime | Python | 3.12 | Lógica operacional + ETL |
| Web framework | FastAPI + Uvicorn | >=0.110, <1.0 | API REST CRUD + dashboards |
| Base de datos | MongoDB | **8.0** (puerto **27018**, replica set `rs0`) | Almacenamiento único: operacional + analítico. **Nota de drift**: si `infra/docker-compose.yml` aún monta `image: mongo:7.0`, esto es drift versión-vs-stack a reconciliar en el próximo auto-audit trimestral (§14.4). |
| Caché | Redis | 7.4 | Caché de sesión, rate limit |
| Orquestador | Apache Airflow | **2.x** (`apache-airflow>=2.8, <3.0` en `requirements.txt`) | Pipelines ETL. **Nota**: existe `docker-compose.airflow3.yml` legacy — pendiente deprecación (§5.4). |
| Auth | `passlib[bcrypt]` + `python-jose` | `passlib>=1.7,<2.0`, `bcrypt>=4.0,<4.1`, `python-jose>=3.3,<4.0` | Cookie `hoteldata_session`, TTL 8h |
| Autorización | Middleware PBAC (Permission-Based Access Control) | 13 roles en `app.routes.ts` + permission codes | Centralizado en `init_security_model_ga03.py`. Lista canónica en `.specify/specs/MOD05-Administracion-Global/030-usuarios-roles/`. |
| Datos | Pandas + PyArrow | `pandas>=2.1,<3.0`, `pyarrow>=15,<18` | DataFrames + Parquet I/O |
| Testing | `pytest` + `pytest-asyncio` + `httpx` | `pytest>=8,<10` | `hoteldata_hub_test` para tests |
| Lint | `ruff` + `mypy` | `ruff>=0.15,<1.0`, `mypy>=2.3,<3.0` | Pre-commit + CI |

### 5.2 Stack Frontend

| Componente | Tecnología | Versión | Rol |
|-----------|-----------|---------|-----|
| Framework | Angular | **22** (standalone components, signals-first) | UI completa |
| Lenguaje | TypeScript | 6.x, `target: ES2024`, `strict: true` | Tipado estricto |
| Build | `@angular/build` (esbuild/Vite) | bundled con @angular/cli | Builds rápidos |
| HTTP | `httpResource()` | API estable en v22 | **NEVER** `HttpClient.get` plano en componentes — siempre `httpResource` |
| Reactividad | `signal()` / `computed()` / `effect()` | 177+ signals en uso | **NEVER** `BehaviorSubject` para UI state |
| Change detection | `ChangeDetectionStrategy.OnPush` | mandatory | **NEVER** omitir en componentes nuevos |
| Control flow | `@if` / `@for` / `@switch` | Angular 22 control flow | **NEVER** `*ngIf` / `*ngFor` / `*ngSwitch` |
| Lazy loading | `@defer` blocks + code splitting | — | Performance budget §9 |
| Charts | `chart.js` ^4.5.1 + `ng2-charts` ^10 | ng2-charts sobre Chart.js | Reportes dashboard |
| Grids | `ag-grid-community` | v36+ | Tablas de management |
| PDF/Excel | `jspdf` ^4.2 + `xlsx` ^0.18 | — | Exportación de reportes |
| Deploy | `nginx:alpine` (multi-stage Docker) | — | Servicio de producción (build sobre `node:24-alpine`) |

### 5.3 Catálogo de Servicios (Docker Compose)

> **Estado actual** del `infra/docker-compose.yml`: **8 servicios** (no 6 como indicaba la v0.8 — drift corregido).

| Servicio | Imagen | Puerto host → contenedor | Función |
|----------|--------|--------------------------|---------|
| `frontend` | `node:24-alpine` build → `nginx:alpine` serve | 4200 → 80 | SPA Angular |
| `server` | Custom (python:3.12-slim + FastAPI + Uvicorn) | 8000 → 8000 | API REST |
| `mongo` | `mongo:8.0` *(verificar contra compose — todavía puede tener `mongo:7.0`)* | **27018** → 27017 | DB operacional + analítica, RS `rs0`. **Drift conocido**: confirmar contra `infra/docker-compose.yml` y bumpear en próximo auto-audit si difiere. |
| `mongo-init-rs` | `mongo:8.0` one-shot | — | Inicializa replica set en primer arranque |
| `redis` | `redis:7.4-alpine` | 6379 → 6379 | Caché |
| `pocketbase` | `pocketbase:0.22` | 8090 → 8090 | Fuente para ETL |
| `airflow` | Custom (`apache/airflow:2.x-python3.12` + deps extra) | 8080 → 8080 | Orquestador ETL |
| `change-stream-watcher` | Custom (FastAPI consumer de Mongo change streams) | — | Propaga eventos `booking_orders` → `fact_*` |

### 5.4 Decisión Pendiente — `docker-compose.airflow3.yml`

> `infra/docker-compose.airflow3.yml` existe como archivo legacy pero el código de producción no lo usa (las dependencias pinning `apache-airflow>=2.8,<3.0`). Es drift.

**Acción de cleanup pendiente** (no bloqueante para esta versión): evaluar deprecación del archivo Airflow 3 y, si se justifica el salto a Airflow 3, hacerlo en una versión 1.0+ de esta Constitución con plan de migración.

---

## 6 · Mapa de Colecciones MongoDB

### 6.1 Control (Gobierno de Datos)

| Colección | Propósito | Operación en ETL |
|-----------|-----------|------------------|
| `etl_executions` | Historial de ejecuciones ETL | **NEVER** drop durante ETL |
| `data_quality_reports` | Reportes de calidad por ejecución | **NEVER** drop durante ETL |
| `rejected_records` | Registros rechazados + razón + raw_record + execution_id | Append-only |
| `system_catalogs` | Catálogos maestros (status, tipos, etc.) | **NEVER** drop durante ETL |
| `search_logs` | Logs de búsqueda | **NEVER** drop durante ETL |

### 6.2 Operacional — Partner Module (CRUD activo)

| Colección | Propósito | Servicio responsable | Dual-Write Target |
|-----------|-----------|----------------------|-------------------|
| `room_types` | Definiciones de tipo de habitación por propiedad | `services/rooms.py` | — |
| `hotel_rooms` | Inventario físico de habitaciones | `services/rooms.py` | — |
| `room_inventory_calendar` | Disponibilidad por fecha | `services/rooms.py` | — |
| `room_availability_blocks` | Bloques de disponibilidad | `services/rooms.py` | — |
| `blackout_dates` | Rangos de fecha bloqueados | `services/rooms.py` | — |
| `rate_plans` | Planes de tarifa por propiedad | `services/rates.py` | — |
| `hotel_rate_calendar` | Precios por fecha y plan | `services/rates.py` | — |
| `rate_rules` | Reglas de tarifa | `services/rates.py` (read-only) | — |
| `promotion_campaigns` | Campañas promocionales | `revenue/services/promotions.py` | — |
| `coupon_codes` | Códigos de cupón | `revenue/services/promotions.py` | — |
| `booking_orders` | Órdenes de reserva operativas | `reservations/service/lifecycle.py` | `fact_hotel_reservations` |
| `booking_guests` | Datos de huéspedes | `reservations/service/lifecycle.py` | — |
| `booking_status_history` | Historial de cambios de estado | `reservations/service/` (insert-only) | — |
| `manual_reservations` | Reservas manuales (web) | `reservations/service/lifecycle.py` | `fact_hotel_reservations` |
| `hotel_content_pages` | Descripciones largas, highlights, amenities | `services/content/save.py` | — |
| `hotel_images` | Imágenes por propiedad | `services/content/images.py` | — |
| `hotel_policies` | Políticas (check-in/out, cancelación, mascotas) | `services/content/save.py` | — |
| `hotel_content_changes` | Auditoría de cambios de contenido | Insert-only | — |
| `hotel_profile_changes` | Auditoría de cambios de perfil | Insert-only | — |
| `reviews` | Reseñas de huéspedes | `services/reviews.py` | `fact_reviews` |
| `reservation_invoices` | Facturas | `services/billing.py` | `fact_reservation_invoices` |
| `reservation_payments` | Pagos | `services/payments.py` | `fact_reservation_payments` |

### 6.3 Analítico — Dimensiones y Hechos

Ver §4.3 para el catálogo de 12 dimensiones. Hechos:

- `fact_hotel_events` — Eventos TAF01 (búsqueda + click)
- `fact_hotel_reservations` — Eventos TA02/GA03 (búsqueda + click + reserva)
- `fact_reviews`, `fact_reservation_invoices`, `fact_reservation_payments` — dual-write (ver §6.2)

### 6.4 Analítico — Negocio (cargados vía ETL desde CSV)

`hotels`, `locations`, `contacts`, `websites`, `facilities`, `attractions`, `hotel_quality`, `dataset_container`

### 6.5 Seguridad

`users`, `user_sessions`, `user_activity_logs`, `roles`, `permissions`, `role_permissions`

---

## 7 · Estándares Operacionales

### 7.1 Convenciones de Nomenclatura

| Contexto | Convención | Ejemplo |
|---------|-----------|---------|
| Archivos Python | `snake_case` | `transform_clean.py` |
| Funciones Python | `snake_case` | `build_ta02_dimensions()` |
| Clases Python | `PascalCase` | `AccessRule` |
| Constantes Python | `UPPER_SNAKE_CASE` | `FACT_REQUIRED_COLUMNS` |
| Archivos TypeScript | `kebab-case` | `auth.service.ts` |
| Funciones TypeScript | `camelCase` | `login()` |
| Clases TypeScript | `PascalCase` | `AuthService` |
| Colecciones MongoDB | `lowercase_with_underscores` | `fact_hotel_reservations` |
| DAG IDs | `hoteldata_{pipeline}_{suffix}` | `hoteldata_ga03_etl` |
| Servicios Docker | minúsculas | `server`, `airflow`, `frontend` |
| Archivos JSON reporte | `{pipeline}_{type}_report.json` | `ga03_execution_report.json` |

### 7.2 Orden de Imports

```python
from __future__ import annotations

# Standard library
import json
from pathlib import Path

# Third-party
import pandas as pd
from pydantic import BaseModel

# Local (absolutos desde la raíz del proyecto)
from config.settings import get_settings
from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS
```

### 7.3 Organización de Archivos

- Una unidad lógica por archivo. Si un módulo excede ~400 líneas, extraer la lógica de soporte en archivos hermanos.
- Tests reflejan la fuente: `test_<module>.py` en `server/tests/`.
- Rutas **SHALL** contener solo definiciones + `Depends()`. Lógica de negocio va en `service.py` o paquetes `services/`.

### 7.4 Seguridad del Código

- Contraseñas: bcrypt via `passlib`. Sin texto plano. Sin encriptación reversible.
- Sesiones: 48 bytes `secrets.token_urlsafe`, hash SHA-256 en DB. TTL de 8 horas.
- `.env` **SHALL** estar en `.gitignore`. Solo se trackea `.env.example`.
- Docker secrets no se usan. Variables vía `env_file` o `environment` en compose.

### 7.5 Gestión de Dependencias

- **SHALL** mantener `package-lock.json` y `requirements.txt` con versiones pinneadas (rangos, no flotantes); commits que cambian dependencias **SHALL** describir el motivo en el mensaje.
- **SHALL** trimestralmente ejecutar `npm audit` y `pip-audit`; los findings de severidad **HIGH/CRITICAL** SHALL bloquear release hasta ser triaged.
- **SHALL** NO introducir nuevas dependencias sin aprobación explícita vía PR con justificación (`motivo + alterntiva evaluada + blast radius`).
- **SHALL** preferir alternativas oficiales mantenidas cuando una deprecada sigue funcionando (ej. `whatwg-encoding` deprecada → `@exodus/bytes`).
- `[Enforced By: PR template campo "dependencies", revisión manual]`

### 7.6 Branch Strategy y Releases

- **MUST** usar trunk-based development con ramas efímeras por feature (`feat/<scope>/<kebab-desc>`).
- **MUST** un PR por concern. PRs > 600 líneas SHALL dividirse.
- **NEVER** commit directo a `main` — todo cambio pasa por PR + al menos 1 reviewer aprobador.
- Conventional Commits (`feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, `perf:`, `test:`) **SHALL** usarse en mensajes.
- `[Enforced By: branch protection rules, PR template]`

### 7.7 Estándares de Code Review

- Cada PR **SHALL** tener al menos 1 reviewer aprobador; PRs que tocan `migrations/`, `*.schemas.py`, `core/types.py` o routers requieren 2 reviewers.
- Reviewer **SHALL** verificar: matriz de impacto presente, tests pasan, sin dead code, sin `TODO/FIXME/HACK/XXX` nuevos, sin `except Exception: pass`, sin secretos en código.
- Reviews con > 50 comentarios SHALL reabrirse en sesión sincrónica en lugar de seguir en línea.
- `[Enforced By: branch protection rules, PR template]`

---

## 8 · Observabilidad y Manejo de Errores

### 8.1 Frontend

- `httpResource()` **SHALL** propagar el error al componente, que **SHALL** mostrar fallback user-friendly vía el sistema de toast (`core/toast/toast.service.ts`).
- **NEVER** silenciar errores HTTP con `catchError + EMPTY` sin notificar al usuario.
- Errores inesperados **SHALL** loggearse vía la consola con stack + contexto mínimo (URL + prop_id + user_id).

### 8.2 Backend

- Logging estructurado (JSON): cada request loggea `method`, `path`, `status`, `duration_ms`, `user_id`, `prop_id`, `request_id`.
- **NEVER** nuevo `except Exception: pass`. Usar `logger.exception()` o rethrow con contexto.
- Trace ID: asignar `X-Request-ID` en cada request entrante y propagarlo al log + response header. `[Enforced By: middleware logging]`
- Errores 5xx **SHALL** generar log con nivel `ERROR` + contexto completo. Errores 4xx con nivel `WARNING` (cliente culpable, sin ruido en monitoring).

### 8.3 Métricas mínimas

> Telemetría básica — sin sobreingeniería. Lo que sigue es el piso, no el techo.

- Requests per route + p95 latency (expuesto en `/metrics` formato Prometheus cuando se active).
- ETL: ejecuciones/día, registros procesados, rechazados, duración por pipeline.
- MongoDB: ops por segundo por colección (vía `db.stats()` polling).
- `[Enforced By: monitorización cuando se active el módulo]`

---

## 9 · Performance Budget

> **Estos números son vinculantes.** Aplican al **bundle inicial** de cada feature Angular y al **bundle de management-shell** que se carga al autenticarse.

| Métrica | Target | Hard ceiling |
|---------|--------|--------------|
| Initial JS bundle (gzipped) | < 350 kB | **500 kB** |
| Initial CSS (gzipped) | < 60 kB | **100 kB** |
| Time to Interactive (4G simulada) | < 3.5 s | **6 s** |
| Largest Contentful Paint | < 2.5 s | **4 s** |
| Lazy chunk máximo | < 300 kB raw | — |
| `httpResource` pendiente máximo | < 200 ms | — |
| `prop_id` query param propagation | 100% de management-links | — |

**Reglas operacionales:**

- **SHALL** usar `@defer` blocks para componentes pesados (charts, ag-grid, modales con datos grandes).
- **NEVER** importar `ag-grid-community` o `chart.js` en el shell — siempre en lazy chunks.
- **SHALL** revisar el output de `ng build --stats-json` antes de mergear una feature nueva; chunks > 300kB SHALL justificarse.
- **SHALL** evitar cargar imágenes > 200 kB sin responsive `<picture>` o `srcset`.
- `[Enforced By: lighthouse CI budget (futuro), manual en review]`

---

## 10 · Internacionalización (i18n)

- UI primaria en **español** (mercado objetivo LATAM). Strings **SHALL** vivir en archivos `.i18n.json` por feature, nunca hardcoded en templates.
- **SHALL** preparar hooks de i18n Angular (`$localize`) para sostener inglés/portugués cuando se requiera.
- Contenido hotelero generado por el usuario (descripciones, highlights) **SHALL** respetar UTF-8 completo (acentos, ñ, emojis opcionales en amenidades).
- Currency formatting **SHALL** usar `CurrencyPipe` con `currencyCode` resuelto por `PropertyContextService.currentCurrency()`.
- Fechas **SHALL** usar `'es-MX'` locale por defecto (mercado principal).
- `[Enforced By: manual + lint de strings hardcoded]`

---

## 11 · Quality Gates (Pre-Commit + Pre-Merge)

```
□ npm run build              # 0 errores TS / template
□ python -m pytest -q        # todos los tests pasan
□ ruff check . && mypy src/  # lint Python
□ test_dag_boundaries.py     # sin imports src.app en DAGs
□ test_etl_rules.py          # sin BashOperator, tareas requeridas
□ test_schema.py             # validación de columnas OK
□ test_transformations.py    # correctitud OK
□ matriz de impacto presente # en cuerpo del task / PR
□ sin dead code              # sin imports/vars no usadas
□ sin TODO/FIXME/HACK nuevos # en código commiteado
□ sin except Exception: pass # nuevo
```

### 11.1 Requisitos de Testing

- **Framework**: `pytest` 8+ + `pytest-asyncio` + `httpx` (ASGITransport, sin servidor live).
- **DB de tests**: MongoDB real contra `hoteldata_hub_test`. Aislamiento total — drop todas las colecciones antes de cada test.
- **Fixtures mínimas**: `app`, `client`, `db`, `cliente_user`, `admin_user`.
- **Frontend**: Jest para unit tests; Playwright para E2E.

### 11.2 Cobertura mínima por área

| Área | Cobertura |
|------|-----------|
| Auth flow + middleware RBAC | Obligatoria |
| CORS | Obligatoria |
| DAG boundaries | Obligatoria |
| Reglas ETL (`BashOperator`, etc.) | Obligatoria |
| Schema validation | Obligatoria |
| Transformaciones (correctitud de datos) | Obligatoria |
| Reportes de calidad | Obligatoria |
| CRUD Partner Module | Obligatoria |
| Dual-write (cuando aplique) | Obligatoria |

---

## 12 · Anti-Features — Lo Que Esta Constitución NO Es

> Esto es tan vinculante como los principios I-VII. Es la declaración explícita de scope que previene scope-creep y alucinaciones del LLM.

- **NO** es un tutorial de Angular, FastAPI o MongoDB. Para eso → docs oficiales.
- **NO** contiene snippets de código extensos. La Constitución dice la **ley**; `knowledge.md` y `.specify/specs/` documentan el **cómo**.
- **NO** lista exhaustiva de dependencias. Para eso → `package.json`, `requirements.txt`.
- **NO** lista exhaustiva de archivos del proyecto. Para eso → `tree`, glob, file-picker.
- **NO** trackea issues abiertos o work-in-progress. Para eso → GitHub Issues o `.specify/specs/*/tasks.md`.
- **NO** define APIs individuales. Para eso → OpenAPI/Swagger auto-generado o `*.schemas.py`.
- **NO** entra en decisiones de implementación carga-por-carga. Para eso → ADRs en `.specify/decisions/`.

**Política anti-implementación-detallada**: Si una sección pide más de ~15 líneas de código explicativo, se mueve a `knowledge.md` o a un ADR. La Constitución permanece escaneable en una sentada.

---

## 13 · Cascada Spec Kit (Constitution → Specs → Plans → Tasks → Code)

```
┌─────────────────────────────────────────────────────────────────┐
│  CONSTITUTION  (este archivo)                                   │
│  Leyes no negociables · Declarativo · Cross-cutting            │
└────────────────┬────────────────────────────────────────────────┘
                 │ deriva principios
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  DECISIONS  (.specify/decisions/ADR-NNNN-*.md)                  │
│  Decisiones arquitectónicas con contexto + alternativas         │
└────────────────┬────────────────────────────────────────────────┘
                 │ invocadas por
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  SPECS  (.specify/specs/MOD{N}-{module}/{NNN}-{desc}/spec.md)   │
│  "Qué" + "Por qué" — requisitos + criterios de aceptación      │
└────────────────┬────────────────────────────────────────────────┘
                 │ descompone en
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  PLANS  (.specify/specs/.../plan.md)                            │
│  "Cómo" — fases, dependencias entre tasks, riesgo               │
└────────────────┬────────────────────────────────────────────────┘
                 │ secuencia en
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  TASKS  (.specify/specs/.../tasks.md)                           │
│  Acciones granulares con criterios de aceptación puntuales      │
└────────────────┬────────────────────────────────────────────────┘
                 │ ejecutan
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  CODE  (frontend/, server/, infra/)                             │
│  Implementación + tests + matriz de impacto en PR               │
└─────────────────────────────────────────────────────────────────┘
```

**Regla de promoción**: Nada pasa al siguiente nivel de la cascada sin haber satisfecho el anterior. Un PR que introduce código SHALL tener tasks.md aprobado + plan.md firmado. Una spec SHALL declarar qué principios de la Constitución aplica.

---

## 14 · Gobernanza y Mantenimiento

### 14.1 Jerarquía de Autoridad

1. Esta Constitución
2. ADRs en `.specify/decisions/`
3. Specs en `.specify/specs/` (aprobadas vía review gate)
4. `knowledge.md` (referencia operativa — deroga legacy `.kiro/steering/*` en caso de conflicto)
5. `AGENTS.md` (convenciones de comportamiento para agentes LLM)

### 14.2 Roles y Responsabilidades

| Rol | Sistema | Responsabilidad constitucional |
|-----|---------|-------------------------------|
| `super_admin` | Acceso total | Ratificar versiones mayores (1.0) y aprobar nuevas dependencias core |
| `admin_sistema` | Configuración global | Mantener `package.json`, `requirements.txt`, Docker compose; depurar archivos legacy |
| `hotel_partner` | Multi-propiedad | Mantener datos de sus propiedades; auditar dual-write |
| `gerente_hotel` | Single-propiedad | Operar diariamente; reportar bugs de UI |
| `auditor_datos` | Calidad / reportes | Calidad trimestral de datos + cadencia de Data Contracts |
| `operador_datos` | Pipelines ETL | Mantener DAGs + tests() de boundaries |
| `reception` / `housekeeping` / `maintenance` / `concierge` | Operación hotelera | Consumir APIs operacionales |

### 14.3 Proceso de Enmienda

1. **Proponer**: spec borrador usando `/speckit.specify` describiendo el cambio y su impacto en principios vigentes o stack.
2. **Revisar**: review gate con al menos 1 aprobador de la mesa constitucional (`super_admin` + `admin_sistema`).
3. **Migrar**: documentar plan de migración para trabajo en curso afectado.
4. **Promulgar**: bumpear versión + actualizar fecha `Última enmienda` + actualizar fecha `Última verificación contra stack` + mencionar cambio en el changelog (`git tag` con prefijo `constitution-vX.Y`).

### 14.4 Cadencia de Revisión

- **Trimestral** (`auditor_datos`): Calidad de datos — consistencia de `site_id`, `prop_id`, `srch_destination_id` en hechos legacy. Reservas huérfanas, tarifas sin plan, inventario sin tipo de habitación. Reporte de salud del star schema.
- **Semestral** (`operador_datos` + `auditor_datos`): Auditoría del star schema — validez de dimensiones y fact tables vs. portafolio. Cobertura de canales (`dim_sites`), room types activos vs. sin uso, rate plans sin actividad > 6 meses.
- **Anual** (`super_admin` + `admin_sistema` + `auditor_datos`): Revisión completa del stack — versiones, deprecaciones, avisos de seguridad, alineación con USALI / HSMAI / GDPR.
- **Trimestral** (`admin_sistema`): Auto-auditoría de drift de stack — diff entre §5 de esta constitución y `package.json`/`requirements.txt`/`docker-compose.yml`. PR automático si drift detectado.

### 14.5 ADRs — Pendientes de creación

> Los archivos `.specify/decisions/*.md` aún **no existen** como carpeta en el repo. Cada decisión arquitectónica significativa merece un ADR. Ejemplos de ADRs pendientes:

| ADR pendiente | Tema |
|---------------|------|
| ADR-0001 | ¿Por qué dual-write operacional→analítica en lugar de CDC-only? |
| ADR-0002 | ¿Por qué PythonOperator-only en Airflow? |
| ADR-0003 | ¿Por qué mongo:8.0 con replica-set vs. cluster compartido? |
| ADR-0004 | ¿Por qué Angular 22 (zoneless-ready) y cuándo activar `provideZonelessChangeDetection()`? |
| ADR-0005 | Decisión Airflow 2 → 3 (mantener 2 hasta GA o migrar ya) |

---

## 15 · OKRs y Definition of Done

### 15.1 OKRs del Proyecto

| Objetivo | Key Result | Cómo se mide |
|----------|-----------|-------------|
| **O1: Sistema operacional funcional** | KR1: Property manager puede crear/editar tipos de habitación, tarifas, inventario, promociones y reservas vía UI | Tests E2E + smoke tests manuales |
| | KR2: Check-in/out opera con consistencia (sin race conditions) | `test_checkinout.py` — 3 escenarios de concurrencia |
| | KR3: 100% colecciones operacionales con `ensure_indexes` + Pydantic | `test_schema.py` + revisión de código |
| **O2: Pipeline analítico confiable** | KR1: ETL procesa dataset completo (100k+ registros) sin errores | Reporte de calidad: 0 rejected por error no controlado |
| | KR2: Star schema con 12 dimensiones + 5 fact tables actualizables | `test_schema.py` verifica estructura |
| | KR3: Dashboard de conversión, ABV y CTR actualizado post-ETL | UI dentro de 5 min post-ejecución |
| **O3: Calidad y trazabilidad de datos** | KR1: Cada ejecución ETL produce reporte de calidad en MongoDB + filesystem | `etl_executions` + `data/reports/` |
| | KR2: 0 registros descartados silenciosamente | Reporte: rejected/total = 100% explicado |
| | KR3: Matriz de trazabilidad en cada tarea completada | Review gate |
| **O4: Alineación con TAF06** | KR1: 100% CU-O01 a CU-O25 implementados | Checklist en `docs/library/desalineaciones_TAF06_vs_sistema.md` |
| | KR2: 0 desalineaciones críticas sistema ↔ TAF06 | Auditoría trimestral |
| | KR3: Módulos reseñas/facturación/pagos con dual-write | Smoke + verificación en fact table |

### 15.2 Definition of Done (DoD)

- [ ] Código implementado y funcional (no solo especificado)
- [ ] Tests pasan (`pytest -q`)
- [ ] Sin `TODO`, `FIXME`, `HACK`, `XXX` en código nuevo
- [ ] Sin `except Exception: pass` nuevo (usar `logger.exception()`)
- [ ] Matriz de impacto incluida en la tarea
- [ ] Lint OK
- [ ] Sin nuevas dependencias sin aprobación explícita
- [ ] Documentación de esquema o API actualizada si cambia interfaz pública

---

## 16 · Lo Que Siempre / Nunca Debe Suceder

### NEVER ❌

- `BashOperator` en DAGs
- Importar `src.app`, `templates`, `static` desde Airflow
- Eliminar `system_catalogs` o `search_logs` durante ETL
- Descarte silencioso de registros
- Cargar dataset completo en memoria sin chunking
- MongoDB Aggregation Pipeline como ETL principal
- Escribir secretos a archivos o commitear `.env`
- Cross-propiedad de datos no autorizada
- Definiciones inconsistentes de métricas (RevPAR debe significar lo mismo en todos los dashboards)
- Datos operacionales creados por el pipeline ETL — pertenecen a la capa operacional
- `HttpClient.get` plano en componentes Angular — siempre `httpResource`
- `*ngIf` / `*ngFor` / `*ngSwitch` — siempre `@if` / `@for` / `@switch`
- `BehaviorSubject` para UI state — siempre `signal()`
- Componente nuevo sin `ChangeDetectionStrategy.OnPush`

### ALWAYS ✅

- `upsert` para `dim_*` (evitar duplicación entre ejecuciones)
- `batch insert` (5k docs) para `fact_*`
- Reporte de calidad por ejecución → `data_quality_reports` + `data/reports/`
- Registro de ejecución → `etl_executions` + `data/reports/`
- Rechazos con `reason` + `raw_record` + `execution_id`
- Progreso via JSON files en filesystem (`PROGRESS_PATH`)
- Detención via `.pid` + `.flag` files
- Aislamiento de tests — drop DB de test antes de cada test
- Doc de esquema y mapeo fuente→destino por pipeline
- Validación en escrituras operacionales (precios, fechas, capacidad)
- `ensure_indexes` en startup de cada módulo operacional
- Dual-write cuando aplique (ver §6.2 columna "Dual-Write Target")

---

## 17 · Footer · Cross-References

Esta Constitución se complementa con:

| Recurso | Ruta | Propósito |
|---------|------|-----------|
| `knowledge.md` | `/knowledge.md` | Referencias operativas: stack quickstart, convenciones, gotchas, regex de fix patterns |
| `AGENTS.md` | `/AGENTS.md` | Convenciones de comportamiento para agentes LLM (Buffy, code-reviewer, thinker, etc.) |
| Specs | `.specify/specs/MOD{N}-{module}/{NNN}-{desc}/` | 9 módulos (Experiencia Huésped, Operaciones Recepción, Partner-Propiedad, Revenue, Administración Global, Housekeeping, Facturación-Pagos, Data Pipeline, Infraestructura Core) con sus `spec.md` / `plan.md` / `tasks.md` / `checklist.md` |
| Library | `docs/library/` | TA07, TA11, TA12 + análisis crítico + desalineaciones TAF06 |
| Templates | `.specify/templates/` | Constitution, spec, plan, tasks, checklist templates |
| Pipelines | `server/scripts/`, `server/dags/` | Migraciones, ETL, validación de datos |
| Tests | `server/tests/`, `frontend/src/**/*.spec.ts` | Backend pytest + frontend Jest |

**Esta Constitución NO reemplaza**: `knowledge.md` (operativo), `AGENTS.md` (conducta de agentes), ni los archivos de `.specify/specs/`. Establece la ley encima de todas ellas.

---

**Versión**: 0.9 (enmienda sobre 0.8) | **Ratificada**: 2026-06-20 | **Última enmienda**: 2026-07-28 | **Última verificación contra stack**: 2026-07-28
