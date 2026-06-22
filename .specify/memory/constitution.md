# Constitución de HotelData Hub

> **Dominio**: Plataforma híbrida de gestión hotelera y analítica para grupos multi-propiedad.
>
> **Propósito de negocio**: Proveer un sistema unificado donde los hoteleros gestionan su operación diaria (inventario de habitaciones, tarifas, reservas, check-in/out, contenido de propiedad) y simultáneamente obtienen una fuente única de verdad para analítica de reservas, ingresos, ocupación y comportamiento de búsqueda a nivel de portafolio.
>
> **Naturaleza del sistema**: Es un sistema **dual**:
> 1. **Operacional** — CRUD completo para que property managers definan tipos de habitación, calendarios de inventario, planes de tarifa, promociones, reservas de huéspedes y check-in/out. Opera directamente sobre MongoDB.
> 2. **Analítico** — Pipeline ETL que ingiere datos desde PocketBase (proxy de fuente externa), los transforma a un modelo estrella (dimensiones + hechos) y los carga en MongoDB para dashboards y BI.

---

## Principios Fundamentales

### I. Python-First con Separación de Capas — Toda la Lógica en Python (NO NEGOCIABLE)

```
Capa Operacional (CRUD directo):
  Web UI → FastAPI → Python (validación + auditoría) → MongoDB

Capa Analítica (ETL batch):
  PocketBase → Python → JSONL → Parquet → Dimensiones (upsert) + Hecho (batch) → MongoDB
```

- **No `BashOperator`**. Todas las tareas de Airflow usan `PythonOperator`.
- **No MongoDB Aggregation Pipeline como ETL**. `aggregate()` solo para dashboards y consultas *después* de cargar el fact table.
- **No transformaciones SQL manuales**. Toda limpieza, deduplicación, coerción de tipos y resolución de claves ocurre en Python antes de llegar a MongoDB.
- **Batch streaming**. Nunca cargar el dataset completo en memoria. Chunk size: 50k filas. Batch insert size: 5k documentos.
- **Datos operacionales se escriben directamente vía API** con validación en Python + auditoría obligatoria + control de concurrencia. No pasan por el pipeline ETL.
- **Datos analíticos pasan por el pipeline ETL** desde PocketBase hasta el modelo estrella.
- **Por qué**: Este diseño sigue el patrón "transform in the pipeline, not in the database" usado por plataformas hoteleras modernas (Shiji Enterprise Platform, Mews BI, Actabl). Toda la lógica de transformación queda bajo control de versiones, testeable con `pytest`, debugeable en aislamiento. Y los datos operacionales se escriben con la latencia mínima que requiere la operación hotelera.

### II. Límite Airflow-Web — Separación Estricta de Capas

```
┌─────────────────────────────────────────────────┐
│  Airflow (orquestador ETL)                      │
│  Solo importa: src/etl/, src/database/, config/ │
│  NO importa: src.app, templates, static, JS     │
├─────────────────────────────────────────────────┤
│  Web (FastAPI + Angular)                        │
│  Sirve: API operacional (CRUD) + API analítica  │
│  (lectura MongoDB) + dashboards                 │
│  Nunca ejecuta ETL en operación normal          │
└─────────────────────────────────────────────────┘
```

- Los DAGs **nunca** importan `src.app`, `templates`, `static`, HTML, CSS ni JS.
- La capa web **nunca** ejecuta lógica ETL durante operación normal (solo lee resultados transformados o escribe datos operacionales directamente en MongoDB).
- Los tests lo enforce: `test_dag_boundaries.py` valida imports de DAGs.

### III. Normalización Multi-Propiedad — El Problema Central de la Industria

> La industria hotelera opera con 30 a 70 sistemas diferentes por grupo (PMS, CRS, Channel Manager, RMS, POS, CRM, BI, mantenimiento, finanzas). Cada sistema tiene su propio esquema, sus propios rate codes, sus propias definiciones de segmento. El problema #1 no es la falta de datos — es que los datos no hablan el mismo idioma.

Nuestra plataforma resuelve esto en **dos frentes**:
- **Operacional**: Proporciona una interfaz unificada para que los property managers gestionen habitaciones, tarifas, inventario y reservas con un modelo de datos consistente entre propiedades.
- **Analítico**: Traduce datos de diferentes fuentes (PocketBase como proxy de diversos PMS/CRS) a un esquema estrella consistente, normalizando rate codes, segmentos, canales y métricas.

**Contexto de la industria**:
- Actabl recibió una patente en 2026 por su método de normalización hotelera basado en tags — validación externa de que este es el problema central sin resolver.
- Mews, Shiji, Oracle OPERA Cloud y Zepth compiten exactamente en este espacio: unificar datos multi-propiedad en un modelo analítico consistente.
- Wyndham (9,000 propiedades) redujo 40% el tiempo de gestión de su infraestructura de datos al centralizar en AWS.

### IV. Calidad de Datos como Proceso Operativo, No como Proyecto Puntual

- Cada ejecución ETL **debe** producir un reporte de calidad: conteo de registros rechazados, campos faltantes, valores inválidos, nulls por columna.
- Cada ejecución **debe** registrarse en `etl_executions` con: `execution_id`, status, timestamps, conteos de registros, resumen de errores.
- **Nunca** descartar un registro silenciosamente. Los rechazos van a `rejected_records` con la razón exacta (campos faltantes, valores inválidos, precios negativos).
- Los reportes de calidad tienen doble almacenamiento: JSON filesystem (`data/reports/`) para polling en tiempo real + MongoDB (`data_quality_reports`) para consultas históricas.
- **Análogo hotelero**: Así como un grupo hotelero audita sus rate codes mensualmente y sus canales trimestralmente, nuestra plataforma audita cada ejecución ETL. La calidad de datos no se arregla una sola vez — se degrada continuamente a medida que rotan fuentes, cambian esquemas y se acumulan excepciones.

### V. Desarrollo Basado en Evidencia — Matriz de Trazabilidad Obligatoria

Cada tarea **debe** declarar su relación con las entregas existentes:

```md
## Relacion con entregas anteriores
| ID | Elemento afectado | Tipo de cambio | Archivo/ruta/coleccion | Estado anterior | Estado nuevo | Criterio de aceptacion |
|----|------------------|----------------|----------------------|----------------|-------------|----------------------|
| IMP-001 | ... | conserva/agrega/modifica/reemplaza/elimina | ... | ... | ... | ... |
```

- "Conserva", "agrega", "modifica", "reemplaza", "elimina" — no hay otro tipo de cambio posible.
- Las tareas sin matriz de impacto no se consideran completas.

### VI. Mejora Progresiva — Extender, Nunca Reemplazar

- Los pipelines nuevos (GA03) extienden el patrón TA02: PocketBase → JSONL → Parquet → Dimensiones + Hecho → MongoDB.
- Los pipelines legacy (TAF01) se mantienen como línea base — CSV → Python → MongoDB.
- La compatibilidad hacia atrás es obligatoria a menos que se documente y apruebe explícitamente en la matriz de impacto.
- **Por qué**: Los grupos hoteleros operan en ciclos tecnológicos de 5 a 10 años (migraciones de PMS, cambios de channel manager). Nuestra arquitectura debe soportar adopción por fases sin romper consumidores downstream.

### VII. Operacional-First — Consistencia CRUD con Dual-Write a Analíticas

- Los datos de operación hotelera (reservas, inventario, tarifas, reseñas, facturas, pagos) se escriben directamente vía FastAPI a MongoDB. No esperan el batch ETL.
- Cada módulo operacional que genera datos de negocio debe implementar dual-write a su fact table correspondiente en el mismo request, dentro de una transacción lógica (o compensación si falla el segundo write).
- Las colecciones operacionales usan `ensure_indexes` para consistencia (unique compuestos, TTL, sorted).
- Las colecciones operacionales usan `_id` de string semántico (ej. `{hotel_id}_{date}` en inventario) para permitir upserts idempotentes desde el ETL.
- El control de concurrencia se implementa con optimistic locking (versión/campo `version`) en colecciones donde dos fuentes (API + ETL) pueden escribir el mismo registro.
- **Por qué**: El huésped no espera al batch de medianoche para que su reseña aparezca, ni el hotel espera al ETL para ver su factura. La operación hotelera exige consistencia transaccional en escritura, no eventual.

---

## Modelo de Dominio — Plataforma Hotelera Híbrida

### Flujo del Sistema

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

### Datos de Entrada

Dos categorías de datos alimentan el sistema:

1. **Operacionales** (creados por el usuario del sistema):
   - Tipos de habitación, inventario y blackouts
   - Planes de tarifa y calendario de precios
   - Promociones y códigos de cupón
   - Reservas de huéspedes con check-in/out
   - Contenido de propiedad (descripciones, imágenes, políticas)

2. **Analíticos** (ingresados vía ETL desde fuente externa):
   - Dataset de eventos de búsqueda y reserva al estilo Expedia/Kaggle
   - Cargado inicialmente a PocketBase desde CSV
   - Procesado a través del pipeline hacia el modelo estrella

### Modelo Estrella (Star Schema) — Diseño Canónico

```
┌──────────────────────────────────────────────────────────┐
│                fact_hotel_reservations                   │
│  Un registro = un evento de búsqueda en el sitio con     │
│  indicadores de click y reserva. Grain: sesión-búsqueda  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Dimensiones circundantes (12):                          │
│                                                          │
│  dim_hotels           → prop_id                          │
│    (propiedad hotelera: rating, review_score, brand)      │
│                                                          │
│  dim_destinations     → srch_destination_id               │
│    (destino de viaje)                                     │
│                                                          │
│  dim_visitor_countries → visitor_location_country_id      │
│    (país de origen del visitante)                         │
│                                                          │
│  dim_sites            → site_id                          │
│    (canal de distribución: web, móvil, OTA, etc.)        │
│                                                          │
│  dim_dates            → date_key (YYYYMMDD)              │
│    (calendario: año, mes, día, día_semana)               │
│                                                          │
│  dim_promotions       → promotion_flag                    │
│    (Flag: con/sin promoción asociada)                    │
│                                                          │
│  dim_click_status     → click_bool                        │
│    (Flag: el usuario hizo click en el resultado)         │
│                                                          │
│  dim_reservation_status → reserva_bool                    │
│    (Flag: el usuario completó una reserva)               │
│                                                          │
│  dim_occupancy_profile → occupancy_profile_id             │
│    (Perfil: A2_C0_R1 = 2 adultos, 0 niños, 1 hab)       │
│                                                          │
│  dim_stay_length_category → stay_length_category_id       │
│    (Categoría: SHORT_STAY / MEDIUM_STAY / LONG_STAY)     │
│                                                          │
│  dim_booking_window_category → booking_window_category_id │
│    (Categoría: LAST_MINUTE / SHORT_TERM / MEDIUM_TERM /  │
│     LONG_TERM)                                           │
│                                                          │
│  dim_price_category   → price_category_id                 │
│    (Categoría: LOW_PRICE / MEDIUM_PRICE / HIGH_PRICE /   │
│     PREMIUM_PRICE)                                       │
└──────────────────────────────────────────────────────────┘
```

### Métricas de Negocio

| Métrica | Cálculo | Notas |
|---------|---------|-------|
| **Booking Conversion Rate** | `count(reserva_bool=1) / count(total searches)` | Mide cierre de búsqueda→reserva. NO es Occupancy % (requiere noches ocupadas / habitaciones disponibles * noches del período). |
| **Average Booking Value (ABV)** | `sum(price_usd) / count(reserva_bool=1)` | Valor promedio por reserva. NO es ADR (requiere ingresos / noches ocupadas). |
| **Revenue Per Booking (RPB)** | `sum(price_usd) / count(reserva_bool=1)` | Alias de ABV. |
| **Click-Through Rate (CTR)** | `count(click_bool) / count(total searches)` | Efectividad de búsqueda. |
| **RevPAR proxy** | `(sum(price_usd) WHERE reserva_bool=1) / total available rooms` | Proxy informativo. RevPAR real requiere revenue total / habitaciones disponibles. |
| **Estrellas de reseña promedio** | `avg(rating.overall) FROM fact_reviews` | Calidad desde reseñas de huéspedes. |
| **NPS** | `% promoters (rating.overall ≥ 9) — % detractors (≤ 6)` | Lealtad desde reseñas. |
| **Gross Bookings USD** | `sum(reservas_brutas_usd)` | Revenue bruta por segmento/canal |
| **Booking Window** | `dim_booking_window_category` | Distribución de ventanas de reserva |
| **Perfil de Ocupación** | `dim_occupancy_profile` | Distribución adultos+niños+habitaciones |
| **Efectividad de Promociones** | Comparación con/sin `promotion_flag` | Diferencia en conversión y revenue |

### Controles de Calidad — Específicos de Datos Hoteleros

| Control | Qué detecta | Impacto en negocio hotelero |
|---------|------------|---------------------------|
| Campos obligatorios faltantes | `srch_id`, `date_key`, `prop_id`, `price_usd` ausentes | Reserva sin fecha o precio = registro inservible para forecasting de demanda |
| Precios negativos | `price_usd < 0` | Rate code mal asignado en PMS — distorsiona ADR y RevPAR |
| Ocupación inválida | `adults=0`, `rooms=0` | Reserva fantasma — infla ocupación, distorsiona pick-up curves |
| Tarifas nulas | `price_usd = null` sin reserva | Gap en el rate calendar — imposible calcular RevPAR |
| `srch_id` duplicado | Mismo `srch_id` cargado dos veces | Doble conteo en CTR y conversión |
| Valores atípicos en precio | `price_usd` > 3 desviaciones | Posible error en rate code o moneda incorrecta |
| Discrepancias en fecha | `date_time` > fecha actual en datos históricos | Corrupción en extracción — necesita investigación |

---

## Stack Tecnológico y Arquitectura

### Backend
| Componente | Tecnología | Versión | Rol |
|-----------|-----------|---------|-----|
| Runtime | Python | 3.12 | Capa de lógica operacional + ETL |
| Web framework | FastAPI + Uvicorn | 0.110+ | API REST para operaciones CRUD + dashboards |
| Base de datos | MongoDB | 7.0 | Almacenamiento único: datos operacionales y analíticos |
| Caché | Redis | 7.4 | Opcional, caché de sesión |
| Orquestador | Apache Airflow | 3.2.2 | Programación de pipelines ETL |
| Autenticación | `passlib[bcrypt]` + `python-jose` | — | Session cookie `hoteldata_session`, TTL 8h |
| Autorización | Middleware RBAC | — | 9 roles, `ROUTE_RULES` config declarativa |
| Datos | Pandas + PyArrow | 2.1+ / 15+ | DataFrames, Parquet I/O |
| Testing | `pytest` + `pytest-asyncio` + `httpx` | 8+ | MongoDB real para tests |

### Frontend
| Componente | Tecnología | Propósito |
|-----------|-----------|-----------|
| Framework | Angular 21 standalone | Signals-first, detección de cambios zoneless |
| Build | `@angular/build` (Vite/ESBuild) | Builds rápidos |
| Routing | `@angular/router` | Lazy-loaded, `authGuard` + `roleGuard` |
| HTTP | Interceptores funcionales | Token de auth, manejo de errores |
| Estilos | SCSS | — |
| PDF/Excel | `jspdf` + `xlsx` | Exportación de reportes de calidad |
| Deploy | `nginx:alpine` (multi-stage Docker) | Servicio de producción |

### Infraestructura
```
Docker Compose (6 servicios):
  mongo:7.0          → MongoDB (datos operacionales + analíticos)
  redis:7.4          → Caché (opcional)
  pocketbase:0.22    → Fuente de datos para pipeline ETL
  server (custom)    → python:3.12-slim + FastAPI + Uvicorn
  airflow (custom)   → apache/airflow:3.2.2-python3.12 + deps extra
  frontend (custom)  → node:22-alpine build → nginx:alpine serve
```

### Arquitectura de Almacenamiento
```
Capa               Ubicación               Formato     Ciclo de vida
──────             ────────                ──────      ────────────
Fuente raw         data/raw/hotels.csv      CSV         Estático (TAF01)
Subidas            data/uploads/            CSV         Efímero (GA03)
Staging            data/staging/            JSONL       Eliminable, regenerable
Procesado          data/processed/          Parquet     Eliminable, regenerable
                                           + JSONL
Reportes           data/reports/            JSON        Evidencia permanente
Progreso           data/reports/            JSON        Efímero (polling)
MongoDB            hoteldata_hub            Documentos  Destino final (operacional + analítico)
PocketBase         hotel_reservation_       JSON        Fuente para pipeline ETL
                    events_03
```

### Mapa de Colecciones MongoDB

**Control (Gobierno de Datos):**
- `etl_executions` — Historial de ejecuciones ETL
- `data_quality_reports` — Reportes de calidad por ejecución
- `rejected_records` — Registros rechazados + razón + `raw_record` + `execution_id`
- `system_catalogs` — Catálogos maestros (NO borrar durante ETL)
- `search_logs` — Logs de búsqueda (NO borrar durante ETL)

**Operacional — Partner Module (CRUD activo):**
| Colección | Propósito | Operaciones |
|-----------|-----------|-------------|
| `room_types` | Definiciones de tipo de habitación por propiedad | CRUD desde `services/rooms.py` |
| `hotel_rooms` | Inventario físico de habitaciones | CRUD desde `services/rooms.py` |
| `room_inventory_calendar` | Disponibilidad por fecha (total, disponible, bloqueado) | CRUD desde `services/rooms.py` |
| `room_availability_blocks` | Bloques de disponibilidad | CRUD desde `services/rooms.py` |
| `blackout_dates` | Rangos de fecha bloqueados | CRUD desde `services/rooms.py` |
| `rate_plans` | Planes de tarifa por propiedad | CRUD desde `services/rates.py` |
| `hotel_rate_calendar` | Precios por fecha y plan de tarifa | CRUD desde `services/rates.py` |
| `rate_rules` | Reglas de tarifa | Solo lectura desde `services/rates.py` |
| `promotion_campaigns` | Campañas promocionales con % descuento | CRUD desde `revenue/services/promotions.py` |
| `coupon_codes` | Códigos de cupón por campaña | CRUD desde `revenue/services/promotions.py` (creados junto con la campaña) |
| `booking_orders` | Órdenes de reserva operativas | CRUD desde `reservations/service/lifecycle.py` |
| `booking_guests` | Datos de huéspedes por reserva | CRUD desde `reservations/service/lifecycle.py` |
| `booking_status_history` | Historial de cambios de estado por reserva | Insert-only desde `reservations/service/` |
| `manual_reservations` | Reservas manuales (desde web) | CRUD desde `reservations/service/lifecycle.py` |
| `hotel_content_pages` | Descripciones largas, highlights, amenities | CRUD desde `services/content/save.py` |
| `hotel_images` | Imágenes por propiedad | CRUD desde `services/content/images.py` |
| `hotel_policies` | Políticas (check-in/out, cancelación, mascotas) | CRUD desde `services/content/save.py` |
| `hotel_content_changes` | Auditoría de cambios de contenido | Insert-only |
| `hotel_profile_changes` | Auditoría de cambios de perfil | Insert-only |

**Analítico — Dimensiones (12 activas):**
| Colección | Key | Descripción |
|-----------|-----|------------|
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

**Analítico — Hechos:**
- `fact_hotel_events` — Eventos TAF01 (búsqueda + click)
- `fact_hotel_reservations` — Eventos TA02/GA03 (búsqueda + click + reserva)

**Analítico — Negocio (cargados vía ETL desde CSV):**
`hotels`, `locations`, `contacts`, `websites`, `facilities`, `attractions`, `hotel_quality`, `dataset_container`

**Seguridad:**
`users`, `user_sessions`, `user_activity_logs`, `roles`, `permissions`, `role_permissions`

---

## Estándares de Desarrollo

### Convenciones de Nomenclatura

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

### Orden de Imports
```
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

### Reglas de Organización de Archivos
- Una unidad lógica por archivo. Si un módulo excede ~400 líneas, extraer la lógica de soporte en archivos hermanos.
- Los archivos de test reflejan la fuente: `test_<module>.py` en `server/tests/`.
- Los archivos de ruta solo deben contener definiciones de rutas + `Depends()`. La lógica de negocio va en `service.py` o el paquete `services/`.

### Reglas de Seguridad
- Contraseñas: bcrypt via `passlib`. Sin almacenamiento en texto plano. Sin encriptación reversible.
- Sesiones: 48 bytes `secrets.token_urlsafe`, hash SHA-256 en DB. TTL de 8 horas.
- Los archivos `.env` están en `.gitignore`. Solo trackear `.env.example`.
- Docker secrets no se usan — las variables de entorno se pasan via `env_file` o `environment` en compose.

---

## Arquitectura de Seguridad

### Postura General
Este es un proyecto educacional sin datos reales de huéspedes ni procesamiento de pagos reales. La postura de seguridad está diseñada para:
1. **Prevenir exposición accidental** de credenciales y datos sintéticos.
2. **Establecer buenas prácticas** transferibles a un entorno productivo.
3. **Documentar explícitamente** lo que está fuera de alcance (seguridad enterprise).

### Perímetro de Seguridad

```
                  ┌──────────────────────────────┐
                  │        Internet               │
                  │  (solo frontend Angular)      │
                  └──────────────┬───────────────┘
                                 │ :80 / :443
                  ┌──────────────┴───────────────┐
                  │     Nginx (reverse proxy)     │
                  │   • TLS termination           │
                  │   • Static file serving       │
                  │   • Rate limit (futuro)       │
                  └──────────────┬───────────────┘
                                 │ /api/* → :8000
                  ┌──────────────┴───────────────┐
                  │     FastAPI (backend)         │
                  │   • Auth: session cookie      │
                  │   • RBAC: 9 roles             │
                  │   • CORS: origen frontend     │
                  └──────────────┬───────────────┘
                                 │ :27017
                  ┌──────────────┴───────────────┐
                  │     MongoDB                   │
                  │   • Sin auth habilitada       │
                  │     (red interna Docker)      │
                  └──────────────────────────────┘
```

### Lo que está protegido
| Activo | Protección | Riesgo si se expone |
|--------|-----------|-------------------|
| Credenciales de usuario | bcrypt + sesiones TTL 8h | Suplantación de identidad en entorno de demo |
| Sesiones activas | Hash SHA-256 en DB, cookie `httponly` | Secuestro de sesión |
| Datos sintéticos de huéspedes | Solo accesibles vía API autenticada | Bajo (datos sintéticos, no reales) |
| .env con secrets | `.gitignore` + `env_file` Docker | Exposición de PocketBase admin (solo datos sintéticos) |

### Lo que está FUERA de alcance (seguridad enterprise)
| Práctica | Motivo de exclusión |
|----------|-------------------|
| Rate limiting en login (`slowapi`) | Requiere middleware adicional; riesgo bajo en entorno educacional |
| CSRF tokens (`fastapi-csrf-protect`) | Aplicable solo si hay forms web internos; las rutas web existentes usan SameSite=Lax |
| Validación de contenido real en uploads (`python-magic`) | `Content-Type` spoofing es riesgo bajo; no hay usuarios reales subiendo archivos |
| PCI DSS compliance | No se procesan pagos reales — solo simulación declarativa (CU-O24/O25) |
| Cifrado en reposo (MongoDB encryption-at-rest) | No hay datos sensibles reales; aplica solo en producción con datos reales |
| Hardening de contenedores (no-root, read-only FS) | Proyecto educacional; imágenes base estándar |

### Respaldo y Recuperación (Backup & Recovery)
| Componente | Estrategia | Responsable |
|-----------|-----------|-------------|
| MongoDB | `mongodump` semanal de `hoteldata_hub` vía script o cron opcional | Operador del entorno |
| .env / configs | Versionadas en `.env.example` + documentación; `.env` real no se respalda | Desarrollador |
| Docker volumes | Volúmenes nombrados (`mongo_data`, `redis_data`); respaldo manual | Operador del entorno |
| Código fuente | Git (GitHub); todo el código se regenera desde el repo + `.env` | Git |

### Plan de Incidentes (Educacional)
| Escenario | Detección | Respuesta |
|-----------|-----------|-----------|
| Credencial comprometida en `.env` commit | `git log --all -p` busca patrones | Rotar credencial, revocar acceso PocketBase, forzar cambio de contraseñas de usuario |
| Cuenta de usuario comprometida | Revisar `user_activity_logs` por actividad sospechosa | Deshabilitar cuenta vía DB directa, resetear sesiones |
| Inyección MongoDB | Auditoría de logs de aplicación | Restaurar desde backup si hay corrupción; corregir validación de entrada |
| Fuga de datos sintéticos | No aplica (datos no reales) | Documentar lección aprendida |

---

## Quality Gates — Lista de Verificación Pre-Commit

```
□ python -m pytest -q           # Todos los tests pasan
□ test_dag_boundaries.py        # Sin imports de src.app en DAGs
□ test_etl_rules.py             # Sin BashOperator, tareas requeridas presentes
□ test_schema.py                # Validación de columnas pasa
□ test_transformations.py       # Correctitud de los datos
□ matriz de impacto incluida    # La tarea declara sus cambios
□ Sin dead code                  # Eliminar imports y variables no usadas
□ Lint (si está configurado)    # Sin errores de sintaxis/tipos
```

### Requisitos de Testing
- **Framework**: `pytest` 8+ con `pytest-asyncio` + `httpx` (ASGITransport, sin servidor live).
- **Base de datos**: MongoDB real contra `hoteldata_hub_test`. Aislamiento total — dropear todas las colecciones antes de cada test.
- **Fixtures**: `app`, `client`, `db`, `cliente_user`, `admin_user`.
- **Áreas de cobertura**: flujo de auth, middleware RBAC, CORS, boundaries de DAG, reglas ETL, validación de schema, transformaciones (correctitud de datos), reportes de calidad, operaciones CRUD del Partner Module.

---

## Reglas Operacionales

### Lo Que Nunca Debe Suceder
- ❌ `BashOperator` en DAGs de Airflow
- ❌ Importación de `src.app`, `templates`, `static` desde Airflow
- ❌ Eliminación de `system_catalogs` o `search_logs` durante el ETL
- ❌ Descarte silencioso de registros (siempre capturar en `rejected_records`)
- ❌ Carga del dataset completo en memoria sin chunking
- ❌ MongoDB Aggregation Pipeline como transformación ETL principal
- ❌ Escritura de secretos a archivos o commit de `.env` a git
- ❌ Cross-propiedad de datos no autorizada (cada propiedad debe ser consultable de forma aislada)
- ❌ Definiciones inconsistentes de métricas (RevPAR debe significar lo mismo en todos los dashboards)
- ❌ Datos operacionales (reservas, tarifas, inventario) creados por el pipeline ETL — pertenecen a la capa operacional

### Lo Que Siempre Debe Suceder
- ✅ `upsert` para colecciones de dimensiones (evitar duplicación entre ejecuciones)
- ✅ `batch insert` para colecciones de hechos (5k documentos por batch)
- ✅ Reporte de calidad por cada ejecución ETL → `data_quality_reports` + `data/reports/`
- ✅ Registro de ejecución por corrida → `etl_executions` + `data/reports/`
- ✅ Registros rechazados capturados con `reason` + `raw_record` + `execution_id`
- ✅ Seguimiento de progreso via JSON files en filesystem (`PROGRESS_PATH`)
- ✅ Mecanismo de detención via archivo `.pid` + archivo `.flag`
- ✅ Aislamiento de tests — limpiar base de datos de test antes de cada test
- ✅ Documentación de esquema y mapeo fuente→destino para cada pipeline
- ✅ Validación de datos en escrituras operacionales (precios válidos, fechas coherentes, capacidad no excedida)

---

## Gobernanza

### Jerarquía de Autoridad
1. Esta Constitución
2. Specs de `.specify/` (aprobadas via review gate)
3. `.kiro/steering/*.md` (referencia legacy, reemplazada donde haya conflicto)

### Proceso de Enmienda
1. **Proponer**: Escribir un spec usando `/speckit.specify` describiendo el cambio y su impacto en el modelo de datos o las reglas del dominio hotelero.
2. **Aprobar**: Pasar un review gate con criterios de aceptación claros.
3. **Migrar**: Documentar un plan de migración para cualquier trabajo en curso que se vea afectado.
4. **Promulgar**: Actualizar la versión, fecha y sección modificada de esta constitución.

### Cadencia de Revisión

- **Trimestral (Responsable: `auditor_datos`)**: Revisión de calidad de datos — verificar consistencia de `site_id`, `prop_id` y `srch_destination_id` en fact tables legacy. Identificar reservas huérfanas, tarifas sin plan, inventario sin tipo de habitación. Publicar reporte de salud del modelo estrella.
- **Semestral (Responsable: `operador_datos` + `auditor_datos`)**: Auditoría del star schema — validar que dimensiones y fact tables reflejan el estado actual del portafolio hotelero. Revisar cobertura de canales (`dim_sites`), room types activos vs. sin uso, rate plans sin actividad en los últimos 6 meses.
- **Anual (Responsable: `super_admin` + `admin_sistema`)**: Revisión completa del stack — versiones de tecnologías, deprecaciones, avisos de seguridad, alineación con estándares de la industria (USALI, HSMAI KPI definitions, GDPR). Evaluar nuevas dimensiones o métricas requeridas por el negocio.
- **Por qué**: Este proyecto educacional no tiene un equipo dedicado de calidad de datos. Una cadencia mensual generaría reportes sin acción. La trimestral da tiempo suficiente para acumular datos significativos, planificar correcciones y ejecutarlas dentro del ciclo normal de desarrollo.

### Definición de Éxito del Proyecto

#### OKRs del Proyecto (Objectives & Key Results)

| Objetivo | Key Result | Cómo se mide |
|----------|-----------|-------------|
| **O1: Sistema operacional funcional** | KR1: Property manager puede crear/editar tipos de habitación, tarifas, inventario, promociones y reservas vía UI | Tests E2E + smoke tests manuales |
| | KR2: Check-in/out opera con consistencia (sin race conditions) | `test_checkinout.py` — 3 escenarios de concurrencia |
| | KR3: 100% de colecciones operacionales tienen `ensure_indexes` + validación Pydantic | `test_schema.py` + revisión de código |
| **O2: Pipeline analítico confiable** | KR1: ETL procesa dataset completo (100k+ registros) sin errores | Reporte de calidad: 0 rejected por error no controlado |
| | KR2: Star schema con 12 dimensiones + 5 fact tables actualizables | `test_schema.py` verifica estructura |
| | KR3: Dashboard de conversión, ABV y CTR actualizado post-ETL | Visualización en frontend dentro de 5 min post-ejecución |
| **O3: Calidad y trazabilidad de datos** | KR1: Cada ejecución ETL produce reporte de calidad en MongoDB + filesystem | Consulta `etl_executions` + `data/reports/` |
| | KR2: 0 registros descartados silenciosamente (todos con razón en `rejected_records`) | Reporte: rejected / total = 100% explicado |
| | KR3: Matriz de trazabilidad presente en cada tarea completada | Review gate verifica inclusión |
| **O4: Alineación con TAF06** | KR1: 100% de casos de uso operacionales del TAF06 implementados (CU-O01 a CU-O25) | Checklist en `docs/library/desalineaciones_TAF06_vs_sistema.md` |
| | KR2: 0 desalineaciones críticas entre sistema y TAF06 | Auditoría trimestral |
| | KR3: Módulos de reseñas, facturación y pagos funcionales con dual-write | Prueba de escritura + verificación en fact table |

#### Definition of Done (DoD) — Criterio para dar una tarea por completa

- [ ] Código implementado y funcional (no solo especificado)
- [ ] Tests pasan (`pytest -q`)
- [ ] Sin `TODO`, `FIXME`, `HACK`, `XXX` en el código nuevo
- [ ] Sin `except Exception: pass` nuevo (usar `logger.exception()`)
- [ ] Matriz de impacto incluida en la tarea
- [ ] Lint OK (si aplica)
- [ ] No se introdujeron nuevas dependencias sin aprobación explícita
- [ ] Documentación de esquema o API actualizada si el cambio afecta interfaz pública

---

**Versión**: 0.8 | **Ratificada**: 2026-06-20 | **Última enmienda**: 2026-06-21
