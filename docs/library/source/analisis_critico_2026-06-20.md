# ANÁLISIS CRÍTICO: SISTEMA + TAF06 + CONSTITUCIÓN

**Rol**: Arquitecto de Software Senior + Experto en Dominio Hotelero
**Fecha**: 2026-06-20
**Versión del análisis**: 1.0

---

## 1. CRÍTICA AL SISTEMA (CÓDIGO)

### 🔴 CRÍTICOS

| # | Problema | Archivo | Impacto |
|---|----------|---------|---------|
| 1 | **MongoClient nuevo en cada llamada** | `server/src/database/connection.py:10-15` | En producción con ~100+ llamadas, esto agota los connection pools de MongoDB. El servidor caerá con `TooManyConnections` bajo carga. |
| 2 | **Sin control de concurrencia en reservas** | `server/src/app/modules/reservations/service/lifecycle.py` | Dos usuarios pueden reservar la misma habitación en las mismas fechas. Overbooking garantizado. |
| 3 | **Credenciales hardcodeadas en source** | `server/src/etl/ta02_airflow_tasks/_state.py:64-65` | Email y password de PocketBase admin visibles en el repo. Si las env vars no están seteadas en Docker, cualquiera con acceso al contenedor puede loguearse como admin. |
| 4 | **Check-in/out con race condition** | `server/src/app/modules/reservations/service/_checkinout.py` | Patrón read-check-write sin atomicidad. Doble check-in posible. |

### 🟡 ALTOS

| # | Problema | Archivo | Solución |
|---|----------|---------|----------|
| 5 | **Sin rate limiting en login** | `server/src/app/modules/auth/routes.py` | Fuerza bruta ilimitada sobre passwords. Usar `slowapi` o middleware de rate limiting. |
| 6 | **Blackout blocks sin transacción entre dos colecciones** | `server/src/app/modules/partner/services/rooms.py:222-286` | Escribe en `blackout_dates` y `room_availability_blocks` sin transacción. Si falla la segunda escritura, datos inconsistentes. Solución: `session.with_transaction()`. |
| 7 | **ETL progress JSON sin file locking** | `server/src/etl/ga03_airflow/progress.py` | Si dos tasks de Airflow corren concurrentemente, los archivos JSON se corrompen. Solución: archivos `.tmp` + rename atómico (ya se usa en `extract.py` pero no en `progress.py`). |
| 8 | **`except Exception: pass` en 15+ lugares** | Múltiples archivos | Errores de producción invisibles. Solución: logging estructurado mínimo (`logger.exception()`). |
| 9 | **Avatar upload sin validación de contenido real** | `server/src/app/modules/account/routes.py:150-151` | Solo valida `Content-Type` header (spoofeable). Un `.exe` disfrazado de `.png` pasa. Solución: validar magic bytes con `python-magic`. |
| 10 | **Sin CSRF en forms web** | Múltiples `@web_router.post` | SameSite=Lax no es suficiente para operaciones de escritura. Solución: `fastapi-csrf-protect`. |
| 11 | **Sin unique index en `users.email` y `users.username`** | `server/src/database/indexes.py` | Duplicados posibles. Solución: unique compound index. |
| 12 | **Tests referencing DAGs que no existen** | `server/tests/test_dag_boundaries.py`, `server/tests/test_etl_rules.py` | Tests que no corren pero nadie lo nota porque no se ejecutan en CI (no hay CI configurado). |
| 13 | **Sin Pydantic models para request validation en API** | `server/src/app/modules/partner/routes/*:102+` | `payload: dict = Body(...)` acepta cualquier cosa. Solución: Pydantic request models. |
| 14 | **`cancel_booking` traga `ValueError` silenciosamente** | `server/src/app/modules/reservations/routes.py:133-135` | El usuario ve éxito cuando la cancelación falló. Solución: loggear y devolver error al usuario. |
| 15 | **Hardcoded passwords en scripts de validación** | `server/scripts/*.py` (8+ archivos) | Passwords de demo hardcodeadas (Admin12345*, Cliente123*) en scripts que se distribuyen en la imagen Docker. |

### 🟢 BAJOS / ESTÉTICOS

| # | Problema | Solución |
|---|----------|----------|
| 16 | Lazy imports de `HTTPException` en 20+ lugares | Consolidar imports al tope del módulo |
| 17 | `POST` y `PATCH` en `/availability` hacen lo mismo | `PATCH` debería aceptar actualizaciones parciales |
| 18 | Circular fallback de env vars `GA03_EXPECTED_RECORDS` / `TARGET_RECORDS` | Simplificar a una sola variable |
| 19 | `load_dotenv()` llamado desde dos archivos | Mover a un solo punto de entrada |

---

## 2. CRÍTICA AL TAF06 (SPEC)

Basado en el contenido extraído del PDF `HotelData_TAF06__.pdf`.

### 🔴 Problemas del Spec

**1. El spec describe DOS sistemas diferentes sin distinguirlos**

El TAF06 tiene objetos como `OO2.1.1` que habla de "exponer endpoints JSON documentables para integraciones con OTAs" — eso es una **API pública**. Pero también tiene `CU-O14` a `CU-O19` que describen casos de uso de gestión interna (crear tarifa, bloquear inventario, check-in). Estos son dos sistemas diferentes (API pública vs intranet de gestión) pero el spec los trata como uno solo.

**Solución**: Separar el spec en dos contextos delimitados (DDD): **HotelData Public API** (OTA-facing) y **HotelData Management** (property manager-facing).

**2. El spec asume operaciones inmediatas pero no define infraestructura**

Los casos de uso operativos (crear tarifa, registrar pago, check-in) se describen como si la operación fuera instantánea. Pero no hay:
- Definición de SLA de latencia
- Especificación de consistencia (eventual vs strong)
- Identificación de operaciones que requieren transacciones distribuidas
- Definición de qué hacer cuando un pago falla (compensación, retry, dead letter queue)

**Solución**: Agregar un anexo de "Non-Functional Requirements" con SLA, consistencia y resiliencia.

**3. El objeto `Fact_Room_Inventory_Calendar` describe un report, no un sistema operativo**

El spec define `inventario total, disponible, bloqueos` como si fuera una tabla de hechos analítica (con `fact_` prefix), pero la descripción de los casos de uso indica que debería ser un **sistema de inventario en tiempo real**. Un fact table es inmutable y se escribe una vez; un sistema de inventario se actualiza constantemente y requiere locks atómicos.

**Solución**: Renombrar el objeto a `Room_Inventory_State` (o similar) para reflejar que es un agregado transaccional, no analítico.

**4. El spec incluye procesamiento de pagos pero no menciona compliance PCI**

El `CU-O25 Registrar pago` y `CU-O24 Generar comprobante` implican manejo de datos financieros. Pero el spec no menciona:
- PCI DSS compliance
- Tokenización de tarjetas
- Cifrado de datos sensibles
- Audit trail financiero
- Conciliación bancaria
- Chargebacks

**Solución**: Agregar requerimientos de seguridad financiera o excluir explícitamente el procesamiento de pagos del alcance.

**5. El objeto `CU-T05 Control de bloqueos` existe pero el modelo de datos no lo soporta**

Control de bloqueos implica **locks atómicos** (optimistic o pessimistic). El modelo tiene `blackout_dates` y `room_availability_blocks` pero no hay:
- Campos de versión (optimistic locking)
- Soporte para `SELECT FOR UPDATE` (MongoDB no lo tiene)
- `find_one_and_update` con condiciones

**Solución**: Agregar un campo `version` a las colecciones de inventario e implementar optimistic locking en el código.

### 🟡 Desalineaciones TAF06 vs Sistema Actual

| Aspecto | Lo que TAF06 dice | Lo que el sistema hace | Brecha |
|---------|-------------------|----------------------|--------|
| Tiempo real | Asume operaciones inmediatas | Batch ETL + CRUD directo (no hay tiempo real) | Alta |
| OTAs | Planifica integraciones | No hay integración alguna | Alta |
| Pagos | Define payment processing | Solo registro declarativo, sin pasarela | Alta |
| Inventory locks | Define control de bloqueos | Datos existen, sin concurrencia | Alta |
| Modelo operacional | `Fact_Room_Inventory_Calendar` (analítico) | `room_inventory_calendar` (operacional) | Media (naming) |

---

## 3. CRÍTICA A LA CONSTITUCIÓN v0.5

Archivo: `.specify/memory/constitution.md`

### 🔴 Lo que está mal

**1. Principio I se llama "ETL-First" pero ya no somos ETL-first**

El nombre del principio contradice la naturaleza híbrida que acabamos de declarar. Si el sistema es dual (operacional + analítico), llamar al primer principio "ETL-First" es engañoso. El operacional escribe directamente a MongoDB sin pasar por el pipeline ETL.

**Solución**: Renombrar a **"Python-First — Toda la Lógica de Transformación en Python"** y separar claramente: "Datos analíticos pasan por ETL; datos operacionales se escriben directamente vía API con validación en Python."

**2. El diagrama de "Flujo del Sistema" muestra dos capas aisladas pero no muestra cómo se relacionan**

Las dos capas operacional y analítica aparecen como silos separados. En realidad:
- `dim_hotels` es actualizado por ambos lados (ETL carga datos, Partner Module hace override manual)
- `fact_hotel_reservations` debería incluir las reservas operativas (`booking_orders`) si queremos analítica real
- El diagrama no muestra esta interacción

**Solución**: Agregar flechas de retroalimentación entre las capas (ej: "reservas operativas → ETL inverso → fact table").

**3. Las métricas de negocio están mal calculadas**

| Métrica | Cálculo actual en la constitución | Cálculo real de la industria (HSMAI, STR, USALI) |
|---------|----------------------------------|--------------------------------------------------|
| Occupancy % | `reserva_bool / total searches` | `habitaciones ocupadas / habitaciones disponibles` |
| ADR | `avg(price_usd)` donde hay reserva | `ingreso por habitación / habitaciones ocupadas` |
| RevPAR | `avg(price_usd)` sobre todo el inventario | `ingreso por habitación / habitaciones disponibles` |

El problema es que nuestra métrica está basada en **eventos de búsqueda** (clickstream), no en **ocupación real de habitaciones**. `reserva_bool` indica si se completó una reserva en el sitio web, no si el huésped durmió en el hotel. Llamar a eso "Occupancy %" es incorrecto.

**Solución**:
- Renombrar "Occupancy %" → **"Booking Conversion Rate"** (es lo que realmente mide)
- Renombrar "ADR" → **"Average Booking Value"** (no es ADR real)
- Agregar nota aclaratoria: "Estas métricas reflejan comportamiento de búsqueda en el sitio web, no ocupación real del hotel. Las métricas reales de la industria requieren datos de PMS."
- O, alternativamente, usar las reservas operativas (`booking_orders`) para calcular métricas reales.

**4. Falta un principio sobre la capa operacional**

Tenemos 6 principios y todos están orientados al ETL. La capa operacional (Partner Module) no tiene principios propios. ¿Qué reglas gobiernan las escrituras directas? ¿Validación? ¿Consistencia? ¿Auditoría?

**Solución**: Agregar **Principio VII — Operacional-First para Datos de Gestión**: "Los datos creados por property managers (tarifas, inventario, reservas) se escriben directamente en MongoDB con validación en Python, auditoría obligatoria y control de concurrencia. No pasan por el pipeline ETL."

**5. La cadencia de revisión está copiada de la industria pero no es aplicable a nosotros**

"Mensual: revisión de dimensiones y calidad de datos" — ¿quién hace esto? ¿con qué presupuesto? ¿qué pasa si no se hace? No hay un equipo de data governance asignado. Es un ideal sin pies.

**Solución**: (a) Ajustar la cadencia a lo que realmente se puede sostener (trimestral), o (b) definir roles responsables.

### 🟡 Lo que falta

**6. No hay arquitectura de seguridad definida**

La constitución tiene "Reglas de Seguridad" sobre bcrypt y sesiones, pero no cubre:
- Modelo de threats
- Perímetro de seguridad (qué está expuesto a internet vs intranet)
- Protección de datos de huéspedes (GDPR, datos personales)
- Esquema de backup y recovery
- Plan de incidentes

**7. No hay definición de "éxito" del proyecto**

¿Cómo sabemos si el sistema cumple su propósito? No hay OKRs, KPIs del proyecto, ni definición de "hecho". Las métricas de negocio están pero son métricas del dominio hotelero, no métricas del proyecto.

**8. El stack tecnológico no menciona versiones específicas de MongoDB, Redis ni Node**

`mongo:latest`, `redis:latest` — "latest" en Docker es una receta para roturas. Un `docker pull` en producción puede cambiar la versión de MongoDB sin aviso.

---

## 4. DESALINEACIONES CRUZADAS (SISTEMA ↔ TAF06 ↔ CONSTITUCIÓN)

| # | Desalineación | Sistema dice | TAF06 dice | Constitución dice | Quién tiene razón |
|---|--------------|-------------|-----------|-----------------|-----------------|
| 1 | Naturaleza del sistema | Híbrido operacional+analítico | Sistema completo tipo PMS | Híbrido dual | TAF06 (el sistema debe tender al modelo completo de gestión hotelera del spec). Sistema y constitución reflejan el estado actual; TAF06 es el norte. |
| 2 | Procesamiento de pagos | Simulado (método `simulated`, transiciones confirmed→refunded) | Sí, lo especifica (CU-O24, CU-O25) | Mencionado como simulación | TAF06. Constitución actualizada (v0.7) documenta simulación sin PCI. |
| 3 | Concurrencia en inventario | Implementado con optimistic locking (campo `version`) en `room_inventory_calendar` | Especificada (CU-T05) | Cubierto (Principio VII + optimistic locking) | TAF06. Sistema y constitución alineados (v0.7). |
| 4 | Integración OTAs | No implementada. Marcada como fuera de alcance educacional. | Planificada | Marcada como fuera de alcance | TAF06 (norte futuro). Sistema y constitución alineados en excluirla del alcance actual. |
| 5 | Cálculo de métricas | Booking Conversion Rate, ABV, CTR, RevPAR proxy (corregido) | Datos operacionales reales del PMS | Corregido en v0.6 (nombres exactos + notas) | TAF06. Sistema y constitución alineados con notación correcta. |
| 6 | ETL como pipeline central | Dual (operacional directo + ETL batch) | Sistema de gestión hotelera completo | Python-First con Separación de Capas (v0.6) | TAF06 (el norte es un sistema completo). Sistema y constitución reflejan correctamente la naturaleza dual actual. |
| 7 | Roles y seguridad | RBAC 9 roles: `super_admin`, `admin_sistema`, `hotel_partner`, `gerente_hotel`, `revenue_manager`, `marketing_hotelero`, `operador_datos`, `auditor_datos`, `cliente` | No especifica | `RoutePermissions` + `NavigationByRole` definidos, seguridad documentada en v0.7 | Sistema. Roles implementados y mapeados a rutas/navegación. Constitución documenta arquitectura de seguridad completa. |

---

## 5. REDUNDANCIAS

| # | Dónde | Qué era redundante | Estado |
|---|-------|-------------------|--------|
| 1 | `test_dag_boundaries.py` y `test_etl_rules.py` | Ambos testeaban lo mismo (imports de DAGs) | ✅ Fusionado en `test_dag_boundaries.py`. `test_etl_rules.py` eliminado. |
| 2 | `progress.py` (GA03) y `_state.py` (TA02) | `_atomic_write`, `_read_state`, `_write_state` duplicados | ✅ Extraído `AtomicJsonState` a `_common.py`. Ambas pipelines lo usan. |
| 3 | `ensure_inventory_collections()` en `bootstrap.py` y `ensure_reservation_collections()` en `collections.py` | Patrón duplicado 6 veces | ✅ Creada `src/database/collections.py` con `ensure_collection()` compartida. Todos los módulos la usan. |
| 4 | `server/scripts/` tiene 52 scripts, muchos de validación | Al menos 10 scripts de validación (GA03) con misma estructura | 🔮 Refactor futuro (scripts independientes, bajo impacto) |
| 5 | `config/settings.py` y `ga03_airflow/config.py` | PocketBase config + fallback circular `GA03_EXPECTED_RECORDS`/`TARGET_RECORDS`/`META_PB`/`META_MONGO` | ✅ `pocketbase_config()` delega a `Settings`. Fallback simplificado a solo `TARGET_RECORDS`. |
| 6 | `fact_hotel_events` y `fact_hotel_reservations` | Dos fact tables con estructura similar | 🔮 Data model change (requiere migración de datos) |

---

## 6. SOLUCIONES PRIORIZADAS

### ✅ Corregido (2026-06-20)

| # | Fix | Archivos modificados |
|---|-----|---------------------|
| 1 | MongoClient singleton — conexión cacheada a nivel de módulo | `server/src/database/connection.py` |
| 2 | Concurrencia en reservas — `insert_one` con manejo de `DuplicateKeyError` | `server/src/app/modules/reservations/service/lifecycle.py` |
| 3 | Credenciales hardcodeadas — usar `os.environ[]` sin fallback | `server/src/etl/ta02_airflow_tasks/_state.py` |
| 4 | Race en check-in/out — `find_one_and_update` con filtro atómico de estado | `server/src/app/modules/reservations/service/_checkinout.py` |
| 5 | File locking en progress.json — patrón `.tmp` + `replace()` atómico | `server/src/etl/ga03_airflow/progress.py`, `server/src/etl/ta02_airflow_tasks/_state.py` |
| 6 | Blackout sin transacción — rollback manual si falla segunda escritura | `server/src/app/modules/partner/services/rooms.py` |
| 7 | `cancel_booking` traga ValueError — error visible en redirect | `server/src/app/modules/reservations/routes.py` |
| 8 | Tests rotos — actualizados al DAG vigente + fallback a dags_backup | `server/tests/test_dag_boundaries.py`, `server/tests/test_etl_rules.py` |

### ✅ Corregido (2026-06-21)

| # | Fix | Archivos modificados |
|---|-----|---------------------|
| 9 | Issues constitución 1-5: Python-First, diagrama flujo, métricas, Principio VII, cadencia | `.specify/memory/constitution.md` |
| 10 | Issues constitución 6-8: Seguridad, OKRs/DoD, versiones pinneadas | `.specify/memory/constitution.md`, `infra/docker-compose.yml`, `infra/docker-compose.local-mongo.yml` |
| 11 | Redundancia 1: Tests duplicados fusionados | `tests/test_dag_boundaries.py`, `tests/test_etl_rules.py` (eliminado) |
| 12 | Redundancia 2: `AtomicJsonState` clase base compartida | `src/etl/ga03_airflow/_common.py`, `progress.py`, `ta02_airflow_tasks/_state.py` |
| 13 | Redundancia 3: `ensure_collection()` compartida en `src/database/` | `src/database/collections.py` (nuevo), `partner/services/bootstrap.py`, `reservations/service/collections.py`, `reviews/service/collections.py`, `billing/service/collections.py` |
| 14 | Redundancia 5: Config simplificada, fallback circular eliminado | `config/settings.py`, `ga03_airflow/config.py`, `ga03_airflow/extract.py`, `ga03_airflow/bootstrap.py` |
| 15 | Sección 4 alineada a TAF06, item 7 con roles reales del sistema | `docs/library/analisis_critico_2026-06-20.md` |
| 16 | CU-T05: Optimistic locking en `save_inventory_entry()` | `server/src/app/modules/partner/services/rooms.py` |

### 🔮 Futuro (no implementado por ser proyecto educativo)

| # | Item | Motivo |
|---|------|--------|
| F1 | Rate limiting en login | Requiere `slowapi`, seguridad enterprise |
| F2 | CSRF en forms web | Requiere `fastapi-csrf-protect`, aplicaciones web internas |
| F3 | Validación de contenido en avatar upload | Requiere `python-magic`, riesgo bajo en entorno educativo |
| F4 | Pasarela de pagos | TAF06 lo menciona (CU-O24, CU-O25) pero es extensión futura |
| F5 | PCI DSS compliance | Solo aplica si se procesan pagos reales |
| F6 | Índices únicos en `users.email` / `users.username` | Mejora de integridad, no blocking |
| F7 | ~~Optimistic locking en inventario~~ | ✅ Implementado v0.8 — campo `version` + control en `save_inventory_entry()` |

### Imposiciones pendientes (prioridad media)

### Mejoras al TAF06 (prioridad baja, para cuando se revise el spec)

14. Separar en dos contextos: Public API vs Management.
15. Agregar NFRs: SLA, consistencia, resiliencia.
16. Agregar requerimientos PCI si se va a procesar pagos.
17. Renombrar `Fact_Room_Inventory_Calendar` a `Room_Inventory_State`.
18. Agregar optimistic locking al modelo de datos.

---

## VEREDICTO GENERAL

El proyecto tiene una base sólida pero está en una **zona de riesgo** típica de sistemas que crecieron orgánicamente: el código operacional se agregó sobre lo que originalmente era un ETL, sin actualizar la arquitectura base.

Los issues #1 y #3 (MongoClient + hardcoded creds) son los más peligrosos porque pueden causar caídas en producción y brechas de seguridad respectivamente.

La constitución logró reflejar la naturaleza híbrida del sistema pero mantiene resabios de cuando el proyecto era solo ETL (Principio I, métricas mal calculadas).

El TAF06 describe un sistema más ambicioso de lo que tenemos, pero tiene problemas de diseño propios (mezcla de contextos, falta de NFRs, omisión de PCI).

Todo lo demás es solucionable en sprints cortos de 1-3 días cada uno.
