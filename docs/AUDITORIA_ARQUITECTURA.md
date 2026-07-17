# Auditoría Arquitectónica — HotelData Hub

> **Fecha:** 2026-07-17
> **Alcance:** Frontend (Angular 22) + Backend (FastAPI + MongoDB)
> **Propósito:** Identificar inconsistencias, deuda técnica, y oportunidades de mejora priorizadas.

---

## 🔴 Código Rojo — Crítico

### R1. Backend síncrono bloquea el event loop de FastAPI

**Dónde:** `server/src/app/` — todos los routers y servicios.

**Problema:** FastAPI corre sobre ASGI (asíncrono por naturaleza), pero virtualmente todos los endpoints son funciones `def` síncronas. Cada request bloquea un hilo del thread pool de Uvicorn. Adicionalmente, el driver de MongoDB es `pymongo` (síncrono), no `motor` (asíncrono). Esto significa que:

- Una request que hace una consulta MongoDB tarda sin liberar el event loop.
- Bajo concurrencia, los threads se agotan y las requests encolan.
- No se aprovecha la capacidad asíncrona del servidor.

**Propuesta:** Migrar a `async def` endpoints con `motor` como driver de MongoDB. Alternativa transitoria: envolver llamadas sync con `run_in_executor()`.

**Archivos clave:**
- `server/src/database/connection.py` — `MongoClient` singleton sync
- `server/src/app/main.py` — `create_app()` con routers sync

---

### R2. MongoDB sin migraciones ni esquema versionado

**Dónde:** Múltiples archivos definen el "schema" de forma dispersa.

**Problema:** No existe una fuente única de verdad para la estructura de los documentos en MongoDB. Las definiciones están repartidas en:

| Archivo | Define |
|---------|--------|
| `src/etl/schema.py` | Columnas legacy (LEGACY_HOTEL_COLUMNS, FACT_REQUIRED_COLUMNS) |
| `src/etl/ta02_fact.py` | 31 columnas del fact table |
| `src/etl/ta02_dimensions.py` | 12 dimensiones con sus key fields |
| `src/database/indexes.py` | Índices de 20+ colecciones |
| `src/database/repositories.py` | Constantes de nombres de colecciones |
| `src/database/collections.py` | `ensure_collection()` — creación en runtime |

No hay un sistema de migraciones tipo Alembic. Los cambios de esquema se aplican en el `lifespan` de FastAPI (código de aplicación), lo que significa que el esquema evoluciona con el deploy, no con migraciones versionadas.

**Propuesta:** Centralizar toda la definición del schema en un solo lugar (ej: `server/src/database/schema.py` con dataclasses tipadas por colección), y considerar `mongoengine` o `beanie` como ODM que versiona esquemas.

---

### R3. Frontend: Cero cobertura de tests

**Dónde:** `frontend/`

**Problema:** No existe ni un solo archivo `*.spec.ts` en todo el frontend. El `package.json` no tiene dependencias de testing (ni Jasmine, ni Karma, ni Jest, ni Playwright, ni Cypress, ni Testing Library). Esto implica que:

- Cualquier refactor o cambio se hace a ciegas.
- No hay regression testing posible.
- El proyecto no puede adoptar TDD ni CI/CD con calidad.

**Propuesta:** Instalar Jest + `@angular-builders/jest` (o Playwright Component Testing) y establecer cobertura mínima del 40% en componentes críticos (auth, billing, reservations).

**Archivos clave:**
- `frontend/package.json` — faltan devDependencies de testing
- `frontend/angular.json` — falta configuración de test builder

---

### R4. Estado global mutable sin control en backend

**Dónde:** `server/src/database/connection.py`

**Problema:**

```python
_client: MongoClient | None = None

def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    return _client
```

- `global _client` es mutable y compartido entre todos los hilos/requests.
- No hay mecanismo de reset (ej: para tests que necesitan una DB falsa).
- `serverSelectionTimeoutMS=5000` es el único timeout configurado (no hay `maxPoolSize`, `minPoolSize`, `connectTimeoutMS`, `socketTimeoutMS`).
- No hay health checks ni reconexión explícita.

**Propuesta:** Usar `FastAPI.lifespan` para inicializar y cerrar el cliente, y exponerlo vía `request.state` o un `Depends()` para facilitar testing.

---

## 🟠 Alto Impacto

### A1. Sin inyección de dependencias en backend

**Dónde:** Toda la carpeta `server/src/app/`.

**Problema:** `get_database()` se llama directamente desde más de 50 archivos (routers, servicios, features, modules). No hay un contenedor DI, no hay `Depends()` para acceso a datos, no hay abstracción entre la capa de datos y la lógica de negocio.

Consecuencias:
- Imposible hacer unit testing de servicios sin conectar a MongoDB real.
- Alto acoplamiento: cambiar de MongoDB a otra base implica reescribir todos los archivos.
- No hay request-scoped connections ni transacciones por request.

**Propuesta:** Implementar repositorios inyectables via `Depends()`. Ejemplo:

```python
# server/src/database/deps.py
async def get_db(request: Request) -> Database:
    return request.app.state.db

# server/src/app/modules/hotels/repository.py
class HotelRepository:
    def __init__(self, db: Database = Depends(get_db)):
        self.db = db
```

**Archivos clave:**
- `server/src/database/connection.py` — origen del singleton
- Cualquier `service.py` o `routes.py` que llame `get_database()`

---

### A2. System admin routes eager-loaded

**Dónde:** `frontend/src/app/features/system-admin/system-admin.routes.ts`

**Problema:** 6 page components se importan directamente con `() => component` en vez de `loadComponent()`. Esto los incluye en el bundle inicial (≈20KB+), a pesar de que solo usuarios con roles `super_admin` o `admin_sistema` pueden acceder.

```typescript
// ❌ Carga eager
{ path: 'audit', component: AuditPageComponent }
{ path: 'monitoring', component: MonitoringPageComponent }
// ...
```

vs el patrón correcto:

```typescript
// ✅ Carga lazy
{ path: 'audit', loadComponent: () => import('./audit-page/audit-page.component').then(m => m.AuditPageComponent) }
```

**Propuesta:** Migrar todas las rutas eager a `loadComponent()`.

---

### A3. `features/` vs `modules/` sin criterio arquitectónico

**Dónde:** `server/src/app/features/` vs `server/src/app/modules/`

**Problema:** Ambos directorios existen pero no hay una regla clara de qué va en cada uno:

| `features/` | `modules/` |
|-------------|------------|
| audit | account, admin, amenities, auth, billing, expenses |
| catalogs | geo_catalog, global_settings, hotels, housekeeping |
| collections | hr, instay, kpi, lost_and_found, map |
| company | notifications, partner, payments, reception |
| dashboard | reservations, revenue, reviews, settings |
| etl_status | tracking, users |
| problems, quality, records | |
| ta02_crud | |

Esto genera confusión a la hora de agregar nuevas funcionalidades y duplica patrones.

**Propuesta:** Elegir una convención (ej: solo `modules/` con dominio de negocio) y migrar `features/` progresivamente. Usar `features/` solo para capacidades transversales (ETL, calidad, auditoría).

---

### A4. Manejo de errores inconsistente

**Dónde:** Todos los routers del backend.

**Problema:** Coexisten 3 patrones distintos para reportar errores:

1. `HTTPException` con código y detalle (en auth, security)
2. `return {"error": "mensaje"}` con status 200 (en dashboard, ETL)
3. `try/except` con `logger.exception()` y respuesta genérica (en varios features)

No hay un formato unificado. El frontend recibe errores con estructura distinta según el endpoint.

**Propuesta:** Implementar un `exception_handler` global y una jerarquía de excepciones personalizadas:

```python
class AppError(Exception):
    status_code: int
    code: str
    detail: str

class NotFoundError(AppError): ...
class UnauthorizedError(AppError): ...
class ValidationError(AppError): ...
```

---

## 🟡 Mediano

### M1. Dual map libraries (Leaflet + MapLibre GL)

**Dónde:** `frontend/angular.json` (allowedCommonJsDeps), `frontend/src/styles.scss` (importa maplibre-gl)

**Problema:** Ambos `leaflet` y `maplibre-gl` están como dependencias y ambos se cargan en el bundle. Si solo uno se usa activamente, el otro suma peso muerto. Además están marcados como CommonJS (impiden tree-shaking óptimo).

**Propuesta:** Verificar cuál se usa en producción y eliminar el otro. Si ambos se necesitan (Leaflet para mapas livianos, MapLibre para GL 3D), considerar lazy loading del segundo.

---

### M2. Startup bottleneck — ~20 ensure_* síncronos en lifespan

**Dónde:** `server/src/app/main.py` — función `lifespan()`

**Problema:** El startup ejecuta secuencialmente:

- `ensure_collections()` → crea N colecciones
- `ensure_indexes()` → crea índices compuestos
- `ensure_auth_collections()` → colecciones de seguridad
- `ensure_default_catalogs()` → datos por defecto
- `ensure_outbox_collection()` → outbox pattern
- `process_pending_outbox()` → procesa mensajes pendientes

Cada una conecta a MongoDB, verifica existencia, y escribe. Con MongoDB en otro contenedor, esto puede sumar 5–15 segundos al startup.

**Propuesta:** Ejecutar ensure en paralelo con `asyncio.gather()`. Adicionalmente, considerar mover la creación de colecciones e índices a un script de init separado (no en el lifespan de la app).

---

### M3. Solo 1 httpResource en frontend

**Dónde:** `frontend/src/app/features/availability/` — único uso de `httpResource`

**Problema:** El proyecto usa Angular 22 que tiene `httpResource()` estable, pero solo el módulo Availability lo aprovecha. El resto del frontend sigue usando el patrón Observable tradicional:

```typescript
// ❌ Observable legacy
this.httpClient.get<T>('/path').pipe(
    map(dto => mapper(dto)),
    catchError(err => ...)
).subscribe(...)

// ✅ httpResource (disponible en Angular 22)
const resource = httpResource<T>(() => '/path', { parse: (res) => mapper(res) })
```

**Propuesta:** Migrar progresivamente los servicios a `httpResource`, empezando por los módulos más usados (reservations, billing, hotels).

---

### M4. `await import()` no estándar en admin.routes.ts

**Dónde:** `frontend/src/app/features/admin/admin.routes.ts`

**Problema:** Se usa un patrón no convencional:

```typescript
...(await import('./submodulo/submodulo.routes')).MAP_ROUTES
```

Dentro de un array síncrono `Routes`. Angular espera que los `Routes` sean estáticos o que usen `loadChildren`. Esta expresión async dentro de un array puede fallar silenciosamente según el bundler.

**Propuesta:** Reemplazar por `loadChildren` estándar:

```typescript
{
    path: 'submodulo',
    loadChildren: () => import('./submodulo/submodulo.routes').then(m => m.MAP_ROUTES)
}
```

---

### M5. Dos sistemas de toast

**Dónde:**
- `frontend/src/app/core/toast/toast.service.ts`
- `frontend/src/app/shared/services/toast.service.ts`
- `frontend/src/app/shared/ui/toast/toast.component.ts`

**Problema:** Existen dos implementaciones:

1. **Core Toast** — función `toast()` que manipula el DOM directamente (vanilla). Usada en interceptores y auth service (contextos fuera de Angular DI).
2. **Shared Toast** — servicio Angular con signals + componente que consume las signals.

Ambos hacen lo mismo pero con APIs distintas. Mantener ambos duplica código y confunde.

**Propuesta:** Unificar. El core toast puede ser un wrapper liviano que use el shared toast service internamente, o migrar los interceptores a usar el servicio Angular.

---

## 🟢 Bajo — Mejoras

### L1. Sin preloading strategy en frontend

**Dónde:** `frontend/src/app/app.config.ts`

**Problema:** No hay estrategia de precarga. El usuario ve pantalla en blanco mientras se descarga cada módulo bajo demanda.

```typescript
// ❌ Actual: sin preload
provideRouter(routes, withComponentInputBinding())

// ✅ Propuesta:
provideRouter(routes, withComponentInputBinding(), withPreloading(PreloadAllModules))
```

---

### L2. Archivos TS >25KB y HTML >20KB sin dividir

| Archivo | Tamaño | Propuesta |
|---------|--------|-----------|
| `hr/employee-onboarding-page.ts` | 40KB | Dividir en wizard steps como componentes hijos |
| `expenses/ledger-page.ts` | 40KB | Separar secciones (PNL chart, trial balance, statements) |
| `rates/rates-page.ts` | 33KB | Separar calendar, KPI grid, plan table |
| `in-stay/guest-portal-page.html` | 35KB | Extraer bento panels, forms, modals a partials |
| `rates/rates-page.html` | 31KB | Extraer tablas y formularios |

**Propuesta:** Dividir páginas grandes en componentes hijos responsabilidad única.

---

### L3. Paths mixtos en API services

**Problema:** Algunos servicios usan rutas limpias confiando en `baseUrlInterceptor` (ej: `/reservations`), mientras otros construyen la URL completa con `${baseUrl}/api/reservations`.

**Propuesta:** Estandarizar a rutas limpias siempre (sin base URL hardcodeada).

---

### L4. `OnPush` faltante en shared components

**Dónde:** `frontend/src/app/shared/ui/`

**Problema:** Componentes como `StatusBadgeComponent`, `LoadingStateComponent`, `ErrorStateComponent` no tienen `changeDetection: ChangeDetectionStrategy.OnPush` explícito. Aunque Angular 22 lo tiene por defecto, tenerlo explícito comunica la intención.

**Propuesta:** Agregar `changeDetection: ChangeDetectionStrategy.OnPush` a todos los shared components.

---

### L5. ETL acoplado a Airflow

**Dónde:** `server/src/etl/`, `server/dags/`, `server/dags_backup/`

**Problema:** La lógica ETL vive en `src/etl/` pero es invocada directamente desde el DAG de Airflow. Hay código legacy en `dags_backup/` que ya no se usa. Esto mezcla responsabilidades (orquestación vs lógica de transformación).

**Propuesta:** Extraer la lógica ETL a un paquete independiente (`hoteldata-etl`) y que Airflow solo la invoque. Eliminar `dags_backup/`.

---

### L6. `load_dotenv()` sin path explícito

**Dónde:** `server/config/settings.py`

**Problema:**

```python
load_dotenv()  # Confía en CWD
```

Si el proceso no se ejecuta desde la raíz del proyecto, el `.env` no se carga silenciosamente.

**Propuesta:**

```python
load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')
```

---

### L7. Background thread vs `asyncio.create_task`

**Dónde:** `server/src/app/main.py`

**Problema:**

```python
threading.Thread(target=refresh_kpis_background, daemon=True).start()
```

En lugar de:

```python
asyncio.create_task(refresh_kpis_async())
```

**Propuesta:** Migrar a `asyncio.create_task()` para mantener la coherencia async del framework.

---

## Resumen de prioridades

| Prioridad | Cantidad |
|-----------|----------|
| 🔴 Crítico | 4 |
| 🟠 Alto impacto | 4 |
| 🟡 Mediano | 5 |
| 🟢 Bajo | 7 |
| **Total** | **20** |

---

## Sobre Playwright en Zed vs VS Code

No necesitás moverte a VS Code para que funcione. Playwright se ejecuta desde la terminal (CLI) independientemente del IDE. Yo puedo correrlo directamente con comandos como:

```bash
npx playwright test
npx playwright install
```

Mi integración es por línea de comandos, no depende de extensiones del editor. La extensión de VS Code solo agrega una GUI bonita (test explorer, debugger visual), pero la funcionalidad es la misma.

**Eso sí:** Si querés correr los tests hoy, primero hay que instalar Playwright en el proyecto, configurarlo, y crear los tests. ¿Querés que lo haga?
