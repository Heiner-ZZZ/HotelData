# Auditoría de Lógica, Datos y Arquitectura — v0.1

> **Generado:** 2026-07-06  
> **Alcance:** `server/src/`, `server/scripts/`, `server/dags*/`, `server/src/etl/`, `frontend/src/`, `infra/`, `docs/database/`  
> **Archivos analizados:** ~200  
> **Hallazgos totales:** 19  
> **Clasificación:** 🔴 Crítico (5) · 🟡 Inestable (7) · 🟢 Poco Beneficio (7)

---

## 📊 Resumen Ejecutivo

Tras revisar **~200 archivos** de código (backend FastAPI + frontend Angular + scripts + configs), analizar **14 seed scripts**, **3+ pipelines ETL**, **110+ colecciones MongoDB**, y consultar mejores prácticas de StackOverflow, MongoDB Docs y Angular Docs, se identificaron **19 hallazgos**.

| Nivel | Cantidad | Acción |
|-------|----------|--------|
| 🔴 Crítico | 5 | Corregir AHORA — riesgo de datos inconsistentes o pérdida |
| 🟡 Inestable | 7 | Corregir en próximas 2-4 semanas |
| 🟢 Poco Beneficio | 7 | Backlog — deuda técnica |

---

## 🔴 NIVEL CRÍTICO

### C1. Dual-Write sin patrón transaccional — `_write_both()`

| Campo | Valor |
|-------|-------|
| **Archivos** | `server/src/app/modules/reviews/service/lifecycle/_helpers.py:23`  
| | `server/src/app/modules/billing/service/lifecycle/_helpers.py:22` |
| **Severidad** | 🔴 Crítico |
| **Categoría** | Integridad de datos |

**Problema:** Se implementa dual-write (`reviews` → `fact_reviews`, `reservation_invoices` → `fact_reservation_invoices`, `reservation_payments` → `fact_reservation_payments`) con dos `insert_one()` secuenciales dentro de la misma función `_write_both()`. Si el segundo `insert_one()` falla, el primero ya está escrito y no hay rollback. Esto es el clásico **"dual-write problem"** documentado por Confluent y MongoDB como anti-patrón.

```python
# reviews/service/lifecycle/_helpers.py
def _write_both(collection: str, fact_collection: str, doc: dict) -> ObjectId:
    result = db[collection].insert_one(doc)       # ← OK
    db[fact_collection].insert_one(fact_doc)       # ← Si esto falla → inconsistencia
    return result.inserted_id
```

**Usos encontrados:**
- `reviews/service/lifecycle/create.py:84,104,124` — 3 llamadas a `_write_both`
- `billing/service/lifecycle/invoices.py:107,650` — 2 llamadas
- `billing/service/lifecycle/payments.py:49` — 1 llamada

**Riesgo:** Datos inconsistentes entre operacional y analítico. Reviews/facturas/pagos existen en la tabla operacional pero no aparecen en dashboards/KPIs. Sin mecanismo de detección ni reconciliación.

**Solución recomendada (StackOverflow / MongoDB Docs):**
1. **Opción A (recomendada):** Usar MongoDB **Change Streams** para propagar `operacional → analítico` de forma asíncrona (CDC pattern). Ya existe `change_stream_watcher.py` que puede extenderse.
2. **Opción B:** Usar transacción MongoDB `with client.start_session()` + `session.start_transaction()` para atomicidad entre colecciones.
3. **Opción C:** Implementar **Transactional Outbox Pattern**: escribir en colección `outbox` dentro de transacción, worker separado propaga a `fact_*`.

---

### C2. 14 seed scripts con datos hardcodeados — lógica duplicada

| Campo | Valor |
|-------|-------|
| **Archivos** | 14 scripts en `server/scripts/seed_*.py` |
| **Severidad** | 🔴 Crítico |
| **Categoría** | Mantenibilidad / Fuente única de verdad |

**Scripts duplicados y qué hardcodean:**

| # | Script | Qué hardcodea |
|---|--------|--------------|
| 1 | `seed_booking_data.py` | `HOTEL_NAMES[10]`, `ROOM_TYPE_SPECS[3]`, `RATE_PLAN_SPECS[2]` |
| 2 | `seed_operational_demo_ga03.py` | Mismos specs + sufijo "Demo", `amenities_catalog` hardcodeado |
| 3 | `cleanup_demo_data.py` | `ROOM_TYPE_SPECS[5]` diferente de los otros |
| 4 | `seed_dummy_hotels_temp.py` | `prop_id=[1001..1005]`, MongoDB URI hardcodeada |
| 5 | `delete_dummy_hotels.py` | `[1001..1005]` duplicado, MongoDB URI hardcodeada |
| 6 | `seed_inv.py` | Lógica de inventario (120 días) |
| 7 | `seed_inventory_fast.py` | **~97% duplicado** de `seed_inv.py` |
| 8 | `seed_ledger.py` | Transacciones contables hardcodeadas, limpia con `delete_many({})` |
| 9 | `seed_master_collections.py` | Dimensiones estáticas (`SHORT_STAY`, `LOW_PRICE`, etc.) |
| 10 | `seed_masters_from_reduced.py` | Similar a `seed_master_collections.py` |
| 11 | `seed_chart_of_accounts.py` | Catálogo contable hardcodeado |
| 12 | `seed_roles_users.py` | Roles, permisos y usuarios demo |
| 13 | `seed_hotel_products.py` | Productos + amenities hardcodeados |
| 14 | `seed_employees_hr.py` | Empleados demo |

**Amenities repetidos en 4 scripts distintos:**
```
"Wi-Fi", "Desayuno incluido", "Piscina", "Gimnasio", "Estacionamiento"
→ seed_booking_data.py, seed_operational_demo_ga03.py, cleanup_demo_data.py, seed_system_catalogs.py
```

**Riesgo:** Si cambia la estructura de `room_types`, hay que actualizar 5+ scripts. Si se añade una propiedad, hay que modificar `delete_dummy_hotels.py`. La lógica de inventario está duplicada. Las amenities cambian en un lugar pero no en otros.

**Solución:**
- Centralizar datos de seed en `data/seeds/*.json` o `data/seeds/*.yaml`
- Un único script `seed_all.py` que lea de esos archivos
- Usar `Pydantic BaseSettings` para configuración en vez de constantes hardcodeadas

---

### C3. Conexiones MongoDB hardcodeadas — ignoran `get_database()`

| Campo | Valor |
|-------|-------|
| **Archivos** | `server/scripts/seed_dummy_hotels_temp.py`, `server/scripts/delete_dummy_hotels.py`, `infra/docker/airflow3-entrypoint.sh` |
| **Severidad** | 🔴 Crítico |
| **Categoría** | Seguridad / Configuración |

```python
# seed_dummy_hotels_temp.py y delete_dummy_hotels.py
client = MongoClient("mongodb://mongo:27018")  # ← URI + puerto hardcodeados
db = client["hoteldata_hub"]                    # ← nombre BD hardcodeado
```

```bash
# airflow3-entrypoint.sh
airflow users create ... --password Admin12345*  # ← contraseña en texto plano en repositorio
```

**Riesgo:** Estos scripts ignoran `config/settings.py` y `get_database()`. Si se cambia el puerto/BD/nombre, estos scripts fallan o se conectan a la BD incorrecta. La contraseña de Airflow está expuesta en el repositorio.

**Solución:**
- Reemplazar con `from src.database.connection import get_database`
- Mover credenciales Airflow a `.env` (ya existe el mecanismo en `docker-compose.yml`)

---

### C4. `seed_inv.py` y `seed_inventory_fast.py` — 97% código duplicado

| Campo | Valor |
|-------|-------|
| **Archivos** | `server/scripts/seed_inv.py`, `server/scripts/seed_inventory_fast.py` |
| **Severidad** | 🔴 Crítico |
| **Categoría** | DRY / Mantenibilidad |

Ambos scripts iteran `prop_id`, `room_types`, 120 días con la misma fórmula `max(total - (day_offset % 3), 0)`. Única diferencia: `seed_inv.py` tiene report de orphaned records.

**Solución:** Eliminar `seed_inventory_fast.py`, renombrar `seed_inv.py` a `seed_inventory.py`.

---

### C5. `dim_date` y `dim_countries` — colecciones legacy vacías con nombres confusos

| Campo | Valor |
|-------|-------|
| **Archivos** | `server/scripts/audit_mongodb_model_ga03.py:81-82`, `server/tests/conftest.py:76-77` |
| **Severidad** | 🔴 Crítico |
| **Categoría** | Integridad de esquema |

El modelo GA03 usa `dim_dates` (con 's'), `dim_visitor_countries`. Pero existen colecciones legacy `dim_date` (sin 's') y `dim_countries` que están vacías y clasificadas como "Legacy sin uso". Ambas se incluyen en `TEST_COLLECTIONS` para limpieza de tests.

**Riesgo:** `dim_countries` vs `dim_visitor_countries` — nombres confusos. Código nuevo podría escribir en la colección incorrecta.

**Solución:** Renombrar a `dim_date_legacy` y `dim_countries_legacy`, o dropearlas si están vacías.

---

## 🟡 NIVEL INESTABLE

### I1. `booking_status_history` disperso en 22+ ubicaciones

| Campo | Valor |
|-------|-------|
| **Archivos** | 22+ ubicaciones (ver detalle abajo) |
| **Severidad** | 🟡 Inestable |
| **Categoría** | DRY / Consistencia de datos |

Cada módulo inserta en `booking_status_history` con su propio diccionario, sin helper centralizado:

| Módulo | Archivo | Línea(s) |
|--------|---------|----------|
| Reservations | `lifecycle/create/core.py` | 123, 311 |
| Reservations | `_transitions/_core.py` | 53 |
| Reservations | `_transitions/_inventory.py` | 92 |
| Reservations | `_checkinout/_checkin.py` | 56, 174 |
| Reservations | `_checkinout/_checkout.py` | 128 |
| Reservations | `_checkin_detail.py` | 183 |
| Reservations | `_checkout_detail.py` | 244 |
| Reservations | `management_impl/_rooms.py` | 121 |
| Reservations | `cleanup.py` | 184 |
| Partner | `hotel_products.py` | 166, 194 |
| Billing | `lifecycle/invoices.py` | 572, 675 |
| Reviews | `lifecycle/reports.py` | 79 |

**Riesgo:** Campos inconsistentes entre módulos. Si se añade un campo requerido, hay que modificar 22+ lugares.

**Solución:** Centralizar en un helper: `def log_booking_event(db, booking_id, event_type, **metadata) -> str`

---

### I2. 4 pipelines ETL con lógica de carga duplicada

| Campo | Valor |
|-------|-------|
| **Archivos** | `server/src/etl/load.py`, `load_reservations.py`, `ga03_airflow/load.py`, `ta02_airflow_tasks/load.py` |
| **Severidad** | 🟡 Inestable |
| **Categoría** | DRY / Arquitectura ETL |

Los 4 comparten el patrón `delete_many({})` + `insert_many(batch)` y la lógica `_insert_jsonl_batches()`. Solo `ga03_airflow/load.py` implementa modo incremental.

**Solución:** Unificar en clase `MongoLoader` con estrategias `full | incremental | upsert`.

---

### I3. `fact_hotel_events` vs `fact_hotel_reservations` — dos fuentes de verdad

| Campo | Valor |
|-------|-------|
| **Archivos** | `audit_mongodb_model_ga03.py:77`, `_common.py:156`, `_helpers.py:42`, `common.py:72` |
| **Severidad** | 🟡 Inestable |
| **Categoría** | Single Source of Truth |

`fact_hotel_events` está clasificada como "Legacy/compatibilidad" pero **sigue usándose activamente** por 5+ módulos (`hotels/_helpers.py`, `revenue/common.py`, `partner/_common.py`, `dashboard/service.py`, `kpi/bsc_service.py`). Mientras, `fact_hotel_reservations` es la tabla "Activa" GA03.

**Riesgo:** KPIs calculados desde `fact_hotel_events` pueden no coincidir con `fact_hotel_reservations`.

**Solución:** Migrar todos los consumidores a `fact_hotel_reservations`, marcar `fact_hotel_events` como legacy.

---

### I4. Falta de comunicación atómica Housekeeping ↔ Reservas en check-out

| Campo | Valor |
|-------|-------|
| **Archivos** | `reservations/service/_checkinout/_checkout.py:210`, `housekeeping/service/lifecycle/cleaning_actions.py` |
| **Severidad** | 🟡 Inestable |
| **Categoría** | Gap lógico entre módulos |

En el check-out se crea `housekeeping_tasks` con `insert_one()`. Si falla, el check-out ya está completado. Tampoco se dispara transición `occupied_dirty → vacant_dirty` en `room_sm` automáticamente.

**Solución:** Evento post-check-out que propague a housekeeping. O transacción MongoDB跨 colecciones.

---

### I5. `hotel_booking_context()` sin caché — N+1 queries

| Campo | Valor |
|-------|-------|
| **Archivo** | `server/src/app/modules/reservations/service/queries.py:17` |
| **Severidad** | 🟡 Inestable |
| **Categoría** | Rendimiento |

```python
def hotel_booking_context(prop_id: int) -> dict[str, Any]:
    return db.dim_hotels.find_one({"prop_id": prop_id}, {...}) or {}
```

Llamada múltiples veces por request. Para lista de 25 reservas = **25+ consultas** a `dim_hotels`.

**Solución:** Caché en Redis (ya existe `server/src/cache/`) o LRU cache en memoria con TTL de 5 min.

---

### I6. `seed_booking_data.py` sobrescribe `prop_id` 1-10 con `upsert=True`

| Campo | Valor |
|-------|-------|
| **Archivo** | `server/scripts/seed_booking_data.py:64-80` |
| **Severidad** | 🟡 Inestable |
| **Categoría** | Integridad de datos |

```python
for i in range(1, NUM_HOTELS + 1):  # 1..10
    db.dim_hotels.update_one({"prop_id": i}, {"$set": {...}}, upsert=True)
```

`prop_id` 1-10 son usados por seeds demo Y por el ETL real. El seed sobrescribe datos reales.

**Solución:** Usar rango dedicado (ej: `9001-9010`) o flag `seed_source` para filtrar sin colisionar.

---

### I7. `cleanup_demo_data.py` define `ROOM_TYPE_SPECS` diferente a `seed_booking_data.py`

| Campo | Valor |
|-------|-------|
| **Archivos** | `cleanup_demo_data.py:21` vs `seed_booking_data.py:41` |
| **Severidad** | 🟡 Inestable |
| **Categoría** | Consistencia |

`cleanup_demo_data.py` define 5 tipos (`premium`, `family` extra) mientras `seed_booking_data.py` define 3. `cleanup` intenta limpiar tipos que nunca se crearon, y deja huérfanos los creados por otros scripts.

**Solución:** Unificar specs en archivo JSON compartido.

---

## 🟢 NIVEL POCO BENEFICIO

### B1. Referencias a archivos frontend inexistentes

**Archivos referenciados pero no existentes:**
- `frontend/src/app/features/demo/demo-widget/demo-widget.component.ts`
- `frontend/src/app/core/interceptors/mock.interceptor.ts`
- `frontend/src/app/features/demo/data/demo-mock-data.ts`
- `frontend/src/app/features/demo/services/demo.service.ts`
- `frontend/src/app/core/services/mock-data.service.ts`

Sugiere una limpieza incompleta de la feature `demo`.

---

### B2. Colecciones `PREPARED_COLLECTIONS` sin distinción demo/real

13 colecciones clasificadas como "Operativa parcial" o "Preparada sin datos". Muchas tienen flag `demo_seed: True`. No hay query fácil para distinguir datos demo de reales.

---

### B3. Colecciones legacy parciales: `hotels`, `locations`, `contacts`, `websites`, `facilities`, `attractions`

6 colecciones del modelo antiguo con datos pero fuera del modelo GA03. Clasificadas como "Operativa parcial".

---

### B4. `search_logs` sin índice TTL — crecimiento ilimitado

`search_logs` se escribe en cada búsqueda sin política de rotación. Solución: `db.search_logs.create_index("searched_at", expireAfterSeconds=2592000)` (30 días).

---

### B5. `state_machine.md` duplica documentación del código

El archivo `state_machine.md` en raíz documenta manualmente transiciones ya definidas en `StateMachine.to_dict()`. Riesgo de desincronización.

---

### B6. Faltan índices en colecciones operativas

`booking_orders.booking_id` sin índice único explícito en `indexes.py`, `room_status_log.(prop_id, room_label)` sin índice compuesto, `guest_folios.booking_id` sin índice.

---

### B7. `seed_system_catalogs.py` hardcodea amenities también presentes en otros 3 scripts

Amenities "Wi-Fi", "Piscina", etc. están en 4 archivos distintos.

---

## 📚 Mejores Prácticas identificadas (StackOverflow + Docs)

| Práctica | Fuente | Estado |
|----------|--------|--------|
| Usar Motor async para MongoDB en FastAPI | FastAPI Best Practices (GitHub) | ❌ PyMongo síncrono |
| Transactional Outbox para dual-write | Confluent.io | ❌ `_write_both()` sin tx |
| Schema Versioning para migraciones | MongoDB Docs | ❌ Sin `schema_version` |
| Centralizar seeds en JSON/YAML | FastAPI Best Practices | ❌ 14 scripts hardcodeados |
| Change Streams en vez de dual-write | MongoDB Docs | ❌ `change_stream_watcher.py` no aprovechado |
| Índices TTL para logs | MongoDB Docs | ❌ `search_logs` sin TTL |
| Environment files para toggle mock/prod | Angular Docs | ✅ `.env` existe pero scripts no lo usan |
| Functional interceptors (Angular 17+) | Angular Docs | ✅ `HttpInterceptorFn` |
| Lazy loading de feature modules | Angular Architecture | ✅ Implementado |

---

## 📊 Métricas

| Métrica | Cantidad |
|---------|----------|
| Hallazgos 🔴 Críticos | 5 |
| Hallazgos 🟡 Inestables | 7 |
| Hallazgos 🟢 Poco Beneficio | 7 |
| Seed scripts redundantes | 14 → 1 propuesto |
| Scripts con MongoDB URI hardcodeada | 2 |
| Colecciones legacy sin uso | 5 |
| ETL pipelines redundantes | 4 → 1 propuesto |
| Ubicaciones dispersas `booking_status_history` | 22+ → 1 helper |
| Fuentes de verdad duplicadas (facts) | 2 |

---

## 🎯 Plan de Acción

### Sprint 1 (Semana 1-2): 🔴 CRÍTICOS

| ID | Acción | Esfuerzo |
|----|--------|----------|
| C1 | Refactorizar `_write_both()` → Outbox Pattern o Change Streams | M |
| C2 | Centralizar seed data → `data/seeds/*.json` + `seed_all.py` | L |
| C3 | Migrar `seed_dummy_hotels_temp.py` y `delete_dummy_hotels.py` a `get_database()` | XS |
| C4 | Eliminar `seed_inventory_fast.py`, renombrar `seed_inv.py` | XS |
| C5 | Renombrar `dim_date` → `dim_date_legacy`, `dim_countries` → `dim_countries_legacy` | XS |

### Sprint 2 (Semana 3-4): 🟡 INESTABLES

| ID | Acción | Esfuerzo |
|----|--------|----------|
| I1 | Centralizar `log_booking_event()` helper | M |
| I2 | Unificar ETL pipelines en `MongoLoader` class | L |
| I3 | Migrar consumidores `fact_hotel_events` → `fact_hotel_reservations` | M |
| I4 | Conectar Housekeeping ↔ Reservas con evento post-check-out | M |
| I5 | Agregar caché Redis a `hotel_booking_context()` | S |
| I6 | Migrar seed booking a `prop_id >= 9001` | XS |
| I7 | Unificar `ROOM_TYPE_SPECS` en `data/seeds/room_types.json` | XS |

### Backlog (Sprint 5+): 🟢 POCO BENEFICIO

| ID | Acción | Esfuerzo |
|----|--------|----------|
| B1 | Limpiar referencias a archivos demo inexistentes | XS |
| B2 | Agregar flag `is_demo` a colecciones y query de limpieza | S |
| B3 | Migrar datos legacy → GA03, dropear colecciones antiguas | M |
| B4 | Agregar índice TTL a `search_logs` | XS |
| B5 | Generar `state_machine.md` desde `StateMachine.to_dict()` | S |
| B6 | Agregar índices faltantes en `database/indexes.py` | XS |
| B7 | Unificar amenities en `data/seeds/amenities.json` | XS |

---

*Fin del documento — HotelData: Auditoría de Lógica v0.1*
