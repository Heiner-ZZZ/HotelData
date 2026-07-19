# BITÁCORA DE ERRORES Y REINICIOS — VERSIÓN 3 (DEFINITIVA)

> **Asignatura:** Construcción del Software — Tarea 10 — Sexto Semestre  
> **Proyecto:** HotelData — Plataforma de analítica y gestión hotelera empresarial  
> **Pipeline de datos:** Datasets masivos de Expedia → **PocketBase** (extracción inicial, v0.26.3) → JSONL → Parquet → ETL con Apache Airflow → **MongoDB** (modelo dimensional: star schema con fact + dimensiones) → API REST (FastAPI) → Frontend SPA (Angular)  
> **Alcance actual:** Nivel operativo (registro de movimientos INSERT/UPDATE/DELETE que el negocio necesita)  
> **Autor:** Heiner Ariel Zambrano Ronquillo  
> **Período:** Mayo 27 – Julio 12, 2026 | **Ramas:** `main` (278 archivos) → `ga03-integraciones` (39 commits, 576 archivos) → `ta06-integrations` (780 commits, 1,723 archivos)

---

## ÍNDICE

1. [Introducción: Contexto Real del Proyecto](#1-introducción-contexto-real-del-proyecto)
2. [Los 8 Conceptos de Clase que Guían Esta Bitácora](#2-los-8-conceptos-de-clase-que-guían-esta-bitácora)
3. [Época 0: `main` — La Visión Inicial Server-Rendered](#3-época-0-main--la-visión-inicial-server-rendered)
4. [Época 1: `ga03-integraciones` — El Primer Intento Híbrido](#4-época-1-ga03-integraciones--el-primer-intento-híbrido)
5. [Época 2: `ta06` Fase I — Reconstrucción Arquitectónica](#5-época-2-ta06-fase-i--reconstrucción-arquitectónica)
6. [Época 3: `ta06` Fase II — La Explosión de Features](#6-época-3-ta06-fase-ii--la-explosión-de-features)
7. [Época 4: `ta06` Fase III — Pulido y Estándares](#7-época-4-ta06-fase-iii--pulido-y-estándares)
8. [Resumen Cronológico](#8-resumen-cronológico)
9. [Tabla de Correspondencia: 18 Errores → 8 Conceptos de Clase → Decisiones](#9-tabla-de-correspondencia-18-errores--8-conceptos-de-clase--decisiones)
10. [Matriz de Impacto: Qué Concepto Causó Qué Cambio](#10-matriz-de-impacto-qué-concepto-causó-qué-cambio)
11. [Conclusión](#11-conclusión)

---

## 1. INTRODUCCIÓN: CONTEXTO REAL DEL PROYECTO

HotelData es una plataforma enterprise de analítica y gestión operativa hotelera, construida para un **cliente empresarial real** con mentalidad de negocio. El proyecto se alimenta de **datasets masivos de Expedia** como fuente cruda. La cadena de procesamiento es: los datos se extraen inicialmente a **PocketBase** (v0.26.3, ejecutándose como servicio Docker en puerto 8090), desde donde el pipeline ETL los transforma a través de los formatos JSONL y Parquet, los carga en **MongoDB** aplicando un modelo dimensional derivado por ingeniería inversa (star schema con tablas de hechos y dimensiones), y finalmente los expone mediante una API REST en **FastAPI** que alimenta el frontend SPA en **Angular**. Todo el proceso está orquestado por **Apache Airflow** mediante DAGs.

PocketBase no es solo un almacén intermedio: es el punto de extracción inicial donde los datos de Expedia se depositan y desde donde los DAGs de Airflow disparan las tareas `extract_from_pocketbase` → `save_pocketbase_extract` que alimentan todo el pipeline subsiguiente. Su versión fue migrada durante el desarrollo del proyecto y está integrado con MongoDB, los DAGs, Airflow y finalmente con el frontend a través de la API.

El stack tecnológico completo es: **Angular v22** (frontend SPA con standalone components) + **FastAPI** (backend API REST pura) + **MongoDB** (base de datos documental) + **PocketBase** (extracción inicial de datos) + **Apache Airflow** (ETL/orquestación) + **Docker** (contenedores multi-servicio).

El alcance actual se mantiene en el **nivel operativo**: registrar movimientos (INSERT/UPDATE/DELETE) que el negocio hotelero necesita — reservas, facturación, housekeeping, check-ins/outs, tarifas, disponibilidad. Los niveles táctico (simulaciones, forecasting) y estratégico (dynamic pricing, revenue management avanzado) están planificados pero **no implementados** — una decisión consciente de acotar el alcance.

El proyecto no se construyó de forma lineal. A lo largo de 47 días atravesó **tres ramas principales** y **dos reinicios completos desde cero**:

| Rama | Commits | Archivos | Período | Rol |
|------|---------|----------|---------|-----|
| `main` | 1 | 278 | 28 mayo | Visión inicial — arquitectura SSR monolítica |
| `ga03-integraciones` | 39 | 576 | 27 mayo → 9 junio | Primer intento real — híbrido SSR + SPA Angular |
| `ta06-integrations` | 780 | 1,723 | 9 junio → 12 julio | Construcción definitiva — SPA pura + API pura |

El patrón fue siempre el mismo: **Construir → Descubrir error por aplicación de teoría → Reestructurar → Reiniciar con base más sólida.**

---

## 2. LOS 8 CONCEPTOS DE CLASE QUE GUÍAN ESTA BITÁCORA

Todos provienen de una sola materia: **Construcción de Software** (6to semestre), que integra ETL, arquitectura de sistemas, modelo de negocios, Airflow, Python, y objetivos operativos/tácticos/estratégicos.

| # | Concepto | Principio |
|---|----------|-----------|
| **C1** | **Especificación como Contrato (Spec-Driven)** | Una especificación no es un documento accesorio — es el plano del sistema. Debe cubrir no solo lo que el software hace, sino también lo que NO debe hacer (restricciones) y qué ocurre cuando algo falla (casos de error). Además, debe organizarse alrededor de los procesos que el negocio ejecuta, no alrededor de las capas técnicas que el desarrollador implementa. |
| **C2** | **Caso de Uso Completo (Más Allá del Camino Feliz)** | Documentar únicamente el escenario donde todo sale bien es diseñar a ciegas. El verdadero valor está en preguntarse: ¿qué sucede cuando dos partes del sistema modifican el mismo dato sin coordinarse? ¿qué pasa si el paso 3 falla después de que el paso 2 ya se ejecutó? Esas intersecciones entre módulos son donde viven los bugs más caros. |
| **C3** | **Alcance Acotado al Nivel que Corresponde** | "Operativo" tiene un significado concreto: registrar lo que ocurre (altas, bajas, cambios). No es hacer simulaciones, ni forecasting, ni contabilidad completa. Cuando el alcance se desborda, rara vez se detecta mirando el código — lo detecta alguien de fuera que pregunta "¿esto quién lo pidió?". |
| **C4** | **El Motor de Base de Datos No es Transparente** | Diseñar un modelo en papel (ER, star schema) es solo el primer paso. Cada motor de base de datos implementa las operaciones de forma distinta. Lo que en un motor es atómico, en otro no. Lo que en uno es una columna, en otro es un campo opcional dentro de un documento. Ignorar estas diferencias es diseñar sobre supuestos falsos. |
| **C5** | **Scripts que se Ejecutan una Sola Vez (Idempotencia)** | Un script que borra y vuelve a crear no debe vivir en un punto donde se dispare automáticamente en cada despliegue o cada reinicio. Si se ejecuta dos veces por accidente, la segunda ejecución debe ser inofensiva — o mejor aún, el script debe verificar el estado actual antes de actuar. Esto aplica tanto a migraciones SQL como a pipelines ETL que hacen `delete_many({})`. |
| **C6** | **Capas Independientes y Configuración en el Momento Correcto** | Un sistema con extracción (PocketBase + Airflow), procesamiento (FastAPI) y presentación (Angular) debe mantener cada capa aislada. El backend no genera HTML; expone datos. El frontend no consulta la base de datos directamente; consume APIs. La configuración que se hornea en la imagen Docker no es la misma que se monta en runtime — confundirlas genera comportamientos que solo aparecen en producción. |
| **C7** | **Parsers que No Ven lo que Hay Dentro del Dato** | *(Principio de baja aplicabilidad al proyecto — ver Apéndice A)* Partir una cadena por un carácter delimitador sin considerar que ese mismo carácter puede aparecer dentro de un valor (un punto y coma en un string SQL, una coma en una dirección CSV) es asumir que el mundo es más simple de lo que es. En este proyecto (MongoDB + Python, sin SQL ejecutado), este riesgo no llegó a materializarse como causa de cambio. |
| **C8** | **Una Sola Forma de Hacer Cada Cosa (Convenciones)** | Cuando existen dos mecanismos para generar lo mismo — dos formatos de ID, dos estilos de nomenclatura, dos patrones de mapper — tarde o temprano se desincronizan. Y cuando fallan, el mecanismo que es distinto a todos los demás es el que se rompe primero. La consistencia no es estética: es defensa contra el caos. |

---

## 3. ÉPOCA 0: `main` — LA VISIÓN INICIAL SERVER-RENDERED

> **1 commit, 278 archivos, 28 de mayo de 2026 | 3 errores descubiertos**

### 3.1 Estado del Proyecto

`main` era una aplicación **FastAPI + Jinja2 Templates** con Server-Side Rendering. El backend generaba todo el HTML. No existía frontend independiente — el mismo servidor que procesaba datos de MongoDB también renderizaba las vistas con `Jinja2Templates`. La estructura estaba anidada bajo `hoteldata_project/`, y el acceso a datos era directo (`pymongo.collection.find()` sin repositorios ni DTOs).

---

### 🔴 Error 0.1 — Arquitectura SSR Acoplada

**Descubrimiento paulatino:** Al intentar agregar reactividad en tiempo real (actualización de disponibilidad sin recargar la página), se hizo evidente que el modelo SSR era un callejón sin salida. Cada interacción requería un ciclo completo de request-response con renderizado HTML.

**Evidencia forense:**
```python
# main: src/app/main.py
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="src/app/templates")

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
```

**Concepto de clase violado:** `C6` — En un sistema con pipeline PocketBase → Airflow → MongoDB → API → Frontend, cada capa debe ser independiente. El backend nunca debe generar HTML; debe exponer APIs REST que el frontend consume.

**Veredicto:** 🔴 **Crítico.** Causó el primer reinicio total. Los 278 archivos fueron abandonados. Solo se rescató el conocimiento del dominio hotelero y los casos de uso.

---

### 🔴 Error 0.2 — Modelo de Datos Plano sin Abstracción

**Descubrimiento paulatino:** Al modificar la estructura de una colección MongoDB, múltiples rutas dejaron de funcionar porque cada una accedía directamente a `collection.find()` sin capa intermedia.

**Evidencia forense:** Los features en `main` (`src/app/features/audit/routes.py`, `src/app/features/catalogs/routes.py`, etc.) llamaban directamente a PyMongo sin repositorios, DTOs ni mappers.

**Concepto de clase violado:** `C1` y `C4` — Spec-Driven Development: la arquitectura de datos (repositorios, DTOs, mappers) debe ser parte de la especificación desde el inicio. También `C4`: acceder directamente a MongoDB sin capa de abstracción ignora cómo el motor documental difiere del modelo dimensional en papel.

**Veredicto:** 🔴 **Crítico.** Obligó a planear repositorios + DTOs + mappers desde el día 0 del siguiente intento.

---

### 🔴 Error 0.3 — Proyecto Anidado en Subdirectorio

**Descubrimiento paulatino:** Las rutas de importación (`from hoteldata_project.src.app...`) y los Dockerfiles se volvieron frágiles. Mover un archivo requería actualizar imports en cascada.

**Concepto de clase violado:** `C1` — Spec-Driven Development. La estructura de directorios es parte de la especificación del proyecto. Debe ser plana y semántica desde el inicio.

**Veredicto:** 🟡 **Medio.** Se corrigió en `ga03` con la estructura `frontend/`, `server/`, `infra/`, `docs/`, `scripts/`.

---

## 4. ÉPOCA 1: `ga03-integraciones` — EL PRIMER INTENTO HÍBRIDO

> **39 commits, 576 archivos, 27 mayo → 9 junio 2026 | 4 errores descubiertos | REINICIO TOTAL (99.8% descartado)**

### 4.1 Estado del Proyecto

`ga03` introdujo **Angular** como frontend, pero mantuvo **Jinja2** en el backend — una arquitectura híbrida SSR + SPA. Usaba Angular con `@NgModule` (patrón de módulos tradicional). La rama tuvo dos fases: desarrollo de features (#1–#17) y mega-reestructuración (#18–#39, 19 commits de "reubica").

---

### 🔴 Error 1.1 — Templates Jinja2 Persistentes (SSR Residual)

**Descubrimiento paulatino:** Angular y Jinja2 competían por las mismas rutas. Una página servida por Angular no podía beneficiarse del SEO de Jinja2, y una página Jinja2 no tenía la reactividad de Angular.

**Evidencia forense:**  
- `requirements.txt` aún contenía `jinja2>=3.1,<4.0`
- `main.py` aún importaba `Jinja2Templates`
- **Commit final `bf78aec`:** `"elimina templates legacy del backend server rendered"` — la confesión explícita del error

**Concepto de clase violado:** `C6` — El frontend debe ser 100% independiente, servido como archivos estáticos por Nginx. Cualquier renderizado del lado del servidor rompe la cadena PocketBase → Airflow → MongoDB → API → SPA.

**Veredicto:** 🔴 **Crítico.** Este fue el error definitivo que provocó el reinicio hacia `ta06`.

---

### 🔴 Error 1.2 — Angular con NgModules en Vez de Standalone

**Descubrimiento paulatino:** Cada nuevo feature requería crear un `*.module.ts` con declaraciones, imports y providers. El boilerplate crecía exponencialmente.

**Evidencia forense:** 167 archivos JS/TS en `ga03`, incluyendo `rates.module.ts`, `reservations.module.ts`, etc. **0 NgModules** en `ta06` actual (verificado: Angular v22 + `bootstrapApplication` + `app.config.ts`).

**Concepto de clase violado:** `C1` — En un sistema con 32 módulos de negocio, cada componente debe ser autosuficiente. NgModules genera acoplamiento que dificulta el lazy loading granular.

**Veredicto:** 🔴 **Crítico.** Los 167 archivos fueron descartados. `ta06` se construyó con Angular Standalone Components.

---

### 🔴 Error 1.3 — Estructura de Archivos Desordenada

**Descubrimiento paulatino:** Los imports entre módulos eran caóticos. No había separación entre servicios compartidos, modelos, DTOs y utilidades.

**Evidencia forense:** **19 commits consecutivos** (#18–#38) titulados "reubica" — moviendo archivos uno por uno para estandarizar `frontend/`, `server/`, `infra/`, `docs/`, `scripts/`.

**Concepto de clase violado:** `C1` y `C8` — Sin convenciones documentadas, cada desarrollador ubicaba archivos donde le parecía. La estructura es parte del contrato del equipo.

**Veredicto:** 🟡 **Medio.** El esfuerzo de 19 commits fue agotador pero necesario. Demostró que la estructura debe definirse el día 0.

---

### 🔴 Error 1.4 — Sin Plan de Pruebas

**Descubrimiento paulatino:** Solo 2 commits de "fix" en 39 commits totales. Los errores se detectaban en runtime, no en tests.

**Evidencia forense:**  
- `2ff00ae`: `"Fix sobre datos de reportes, métricas reales de BD, e indicadores operativos"`
- `4ee9fa4`: `"fix(tsconfig): correct rootDir in app configuration"`

**Concepto de clase violado:** `C2` (parcialmente) — La falta de tests de integración entre capas (ETL → API → Frontend) significó que los errores en intersecciones de módulos solo se detectaran en producción. Es un problema transversal de calidad que toca múltiples conceptos; C2 es el que mejor captura la consecuencia (fallos en producción por no probar las intersecciones).

**Veredicto:** 🟡 **Medio.** `ta06` incluyó suite de tests (pytest + Jasmine/Karma) desde etapas más tempranas.

---

## 5. ÉPOCA 2: `ta06` FASE I — RECONSTRUCCIÓN ARQUITECTÓNICA

> **~250 commits, 160 → ~800 archivos, 9 junio → 20 junio 2026 | 3 errores descubiertos**

### 5.1 El Tercer Arranque

`ta06` y `ga03` comparten el mismo commit inicial (`e417b02`). Pero cuando `ga03` terminó, los desarrolladores no continuaron sobre esa rama — iniciaron `ta06` desde el mismo origen pero con solo **160 archivos** (vs. 576), descartando preventivamente el 99.8% del código. Conservaron la estructura de directorios (el "plano") y reconstruyeron con materiales nuevos: Angular Standalone + FastAPI puro.

**Descubrimiento paulatino de esta fase:** Fue durante la migración de Airflow y la reorganización del backend cuando se hizo evidente que ciertos archivos Python habían crecido sin control, y que cada módulo abría sus propias conexiones a MongoDB.

---

### 🔴 Error 2.1 — "God Files" Monolíticos

**Descubrimiento paulatino:** La incomodidad de editar un archivo de 1,098 líneas para cambiar una sola función llevó a cuestionar la estructura.

**Evidencia forense:**

| Archivo | Tamaño | Problema |
|---------|--------|----------|
| `availability.store.ts` | **1,098 líneas** | Disponibilidad, calendario, editor de celdas — todo junto |
| `dashboard.py` | masivo | Métricas, reportes, visualizaciones |
| `content.py` | masivo | 5 responsabilidades distintas |
| `properties.py` | masivo | CRUD, validación, búsqueda, filtros |

**Concepto de clase violado:** `C1` — Cada módulo debe tener una sola razón de cambio. Un "god file" que mezcla CRUD con validación, tarifas y folios es imposible de mantener.

**Veredicto:** 🔴 **Crítico.** Descomposición masiva: `dashboard.py` → 4 submódulos, `content.py` → 5, `properties.py` → 6, `availability.store.ts` → múltiples archivos enfocados.

---

### 🔴 Error 2.2 — Migración Airflow 2→3 Mal Planificada

**Descubrimiento paulatino:** Al actualizar Airflow, los DAGs que procesaban datos de Expedia dejaron de funcionar. Los operadores y la API de conexiones cambiaron incompatiblemente.

**Evidencia forense:** ~55 commits dedicados a la migración:
- `docker-compose.airflow.yml` → `docker-compose.airflow3.yml`
- `"extrae servicios airflow legacy"` → `"consolida stack airflow3"`

**Concepto de clase violado:** `C5` — Las migraciones de infraestructura crítica (el orquestador ETL) deben planificarse como mini-proyectos con pruebas de regresión sobre los pipelines de datos.

**Veredicto:** 🟡 **Medio.** Se debió elegir Airflow 3 desde el inicio.

---

### 🔴 Error 2.3 — Conexiones MongoDB No Centralizadas

**Descubrimiento paulatino:** Errores intermitentes de conexión forzaron a investigar. Se descubrió que cada script y cada módulo abría su propia conexión sin pool compartido.

**Evidencia forense:**  
- `76cd536`: `"Refactor server scripts to use centralized database connection"`
- `fa90aad`: `"Refactor GA03 validation script to use project database connection"`

**Concepto de clase violado:** `C4` — En un sistema donde ETL, API y scripts comparten MongoDB, un pool centralizado es la única forma de garantizar consistencia y evitar fugas.

**Veredicto:** 🟡 **Medio.** Se implementó `server/src/database/` como módulo centralizado.

---

## 6. ÉPOCA 3: `ta06` FASE II — LA EXPLOSIÓN DE FEATURES

> **~326 commits, ~800 → ~1,300 archivos, 21 junio → 30 junio 2026 | 4 errores descubiertos**

### 6.1 El Período Más Productivo

~40 commits/día. Se construyeron la mayoría de los **32 módulos del frontend**. Pero la velocidad expuso grietas profundas.

**Descubrimiento paulatino de esta fase:** Al integrar tarifas con reservas, los datos no coincidían: el mapper del frontend esperaba `basePrice` pero el backend entregaba `base_price`. Una sesión de debugging de 3 horas reveló la causa raíz: no había contrato de API. Al agregar el portal de RRHH, el sistema de roles no contemplaba `maintenance`. Durante pruebas, un huésped saltó de "pendiente" a "completada" sin confirmar.

---

### 🔴 Error 3.1 — Mappers y DTOs Desincronizados

**Evidencia forense:**

| Commit | Conflicto |
|--------|-----------|
| `fc626d5` | fix(reservations): mapper, DTO, modelo — `basePrice` vs `base_price` |
| `ddcaf34` | fix(availability,billing): mapper, DTO, modelo y folio |
| `d42a5d0` | fix(rates): mapper, DTO, modelo y pagina de tarifas |
| `a767420` | fix(rates,reservations,rooms): API rates, mapper de reservas y room table |
| `d6b4d74` | fix(billing,expenses,hotel-detail): servicios y capa de datos |
| `f82aa6f` | fix(hr,policies): mapper, DTO y modelo de RRHH y politicas |

**Concepto de clase violado:** `C8` — Dos mecanismos distintos para el mismo dato (frontend camelCase, backend snake_case) se desincronizan. Y `C2` — no se probó la intersección entre módulos.

**Veredicto:** 🔴 **Crítico.** El error más documentado del proyecto (6+ commits de fix). Horas de debugging que se habrían evitado con Contract-First Development.

---

### 🔴 Error 3.2 — Roles y Permisos Agregados Tardíamente

**Evidencia forense:**  
- `cd76489`: `"feat(auth): rol maintenance añadido"` — rol agregado cuando el sistema ya estaba construido
- `27459bc`: `"Add HR employee portal and maintenance role access"`
- `068cad0`: `"fix(server): instay, kpi, dashboard, auth y seguridad"`
- `118294a`: `"fix(server): billing, expenses y permisos de rutas"`

**Concepto de clase violado:** `C2` (parcialmente) y preocupación transversal de RBAC — Si bien C2 aplica principalmente a colisiones de datos entre módulos, el principio se extiende aquí: la matriz de acceso es un "contrato" entre los módulos de autenticación y cada feature. No diseñarla desde el inicio con el cliente fuerza a reabrir guards, middlewares y rutas ya probados — el mismo patrón de "corregir intersecciones tardíamente" que C2 describe.

**Veredicto:** 🔴 **Crítico.** Refactorización en cascada de guards (Angular), middlewares (FastAPI) y rutas (ambos).

---

### 🔴 Error 3.3 — State Machine con Transiciones No Validadas

**Evidencia forense:**  
- `92543c3`: `"fix(server): checkin, checkout, transiciones y cleanup"`
- `e5b7128`: `"fix(server): correcciones en checkinout, transiciones y creacion"`
- `af72f0e`: `"mantenimiento restaura múltiples estados bloqueados"`

La máquina de estados (`pendiente → confirmada → en_curso → completada → facturada`) permitía transiciones inválidas. Dos módulos (`checkin` y `reservations`) modificaban el estado sin una matriz compartida.

**Concepto de clase violado:** `C2` — Con impacto financiero real para el cliente. Un huésped que salta de "pendiente" a "completada" sin confirmar es una pérdida de dinero.

**Veredicto:** 🔴 **Crítico.** Se implementó validación estricta en backend (`state_machine.md`).

---

### 🔴 Error 3.4 — CORS Mal Configurado

**Evidencia forense:** `test_cors.py` en `server/tests/`. Commits iterativos ajustando `Access-Control-Allow-Origin`, `Allow-Methods`, `Allow-Headers`.

**Concepto de clase violado:** `C6` — Con frontend (:4200), backend (:8000) y Airflow (:8080) en orígenes distintos, CORS debe configurarse una vez y correctamente.

**Veredicto:** 🟡 **Medio.** Se implementó `proxy.conf.json` (dev) + `nginx.conf` (prod).

---

## 7. ÉPOCA 4: `ta06` FASE III — PULIDO Y ESTÁNDARES

> **~209 commits, ~1,300 → 1,723 archivos, 1 julio → 12 julio 2026 | 4 errores descubiertos**

### 7.1 De la Funcionalidad a la Calidad

Con 1,300+ archivos y 32 módulos, el proyecto entró en estabilización. **Descubrimiento paulatino:** Al intentar implementar dark mode, se descubrió que cambiar el theme requería editar cientos de archivos. Durante pruebas de estrés, se detectaron desconexiones SSE sin reconexión. Una auditoría de seguridad reveló ausencia total de trazabilidad.

---

### 🔴 Error 4.1 — Colores Hardcodeados en SCSS

**Evidencia forense — ANTES:**
```scss
color: #dc2626;       background: #16a34a;
border-color: #3b82f6; color: #9ca3af;
box-shadow: 0 0 0 3px rgba(20, 99, 255, 0.1);
background: rgba(239, 68, 68, 0.08);
```
**Evidencia forense — DESPUÉS (migración en curso, visible en git diff):**
```scss
color: var(--danger);  background: var(--success);
border-color: var(--accent); color: var(--muted-text);
box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 10%, transparent);
background: color-mix(in srgb, var(--danger) 8%, transparent);
```

**Concepto de clase violado:** `C8` — Sin tokens semánticos, 400+ ocurrencias de colores crudos son 400+ puntos de fallo al cambiar el theme. Es el equivalente visual a no tener DTOs en la capa de datos.

**Veredicto:** 🔴 **Crítico.** Migración masiva en curso: availability (9 partials), billing (11), check-outs (4), housekeeping, reservations, hotel-compare. ~15 partials restantes en progreso.

---

### 🔴 Error 4.2 — Templates Legacy Rediseñados Múltiples Veces

**Evidencia forense:**  
- `455caea`: `"completa rediseño del reception calendar"`
- Múltiples refactors de `hotel-detail` (templates rehechos 2-3 veces)

**Concepto de clase violado:** `C1` — Un componente que requiere rediseño completo 2-3 veces revela que el modelo mental del negocio no estaba claro al inicio.

**Veredicto:** 🟡 **Medio.** La ola de SCSS partials actual corrige este patrón.

---

### 🔴 Error 4.3 — SSE sin Estrategia de Reconexión

**Evidencia forense:**  
- `5292c11`: `"feat(in-stay,server): sessions SSE y modulos de instay"`
- `7f7f0ba`: `"Add DND toggle SSE notifications"`

**Concepto de clase violado:** `C3` (parcialmente) — SSE sin reconexión robusta no es un problema de scope/alcance, sino una decisión técnica de implementación. Sin embargo, en un sistema operativo hotelero real donde el estado de habitación y DND cambian constantemente, una implementación frágil de tiempo real sí afecta el cumplimiento del alcance operativo (el sistema no refleja el estado real del hotel).

**Veredicto:** 🟡 **Medio.** Sistema actual: SSE + polling. Requerirá migración a WebSockets.

---

### 🔴 Error 4.4 — Auditoría Implementada Tardíamente (commit 700+)

**Evidencia forense:**  
- `db4755d`: `"Implementar sistema de auditoría y actualizar documentación"` (8 julio)
- `059aa53`: `"Implement Transactional Outbox pattern for data consistency"`

**Concepto de clase violado:** `C2` (parcialmente) y `C5` — C2 aplica en tanto la auditoría es el "otro módulo" que debió conocer cada operación desde el inicio. C5 aplica porque el patrón Transactional Outbox (commit `059aa53`) tuvo que implementarse tardíamente para garantizar idempotencia entre la operación de negocio y el evento de auditoría.

**Veredicto:** 🔴 **Crítico.** El patrón Transactional Outbox garantiza atomicidad operación+auditoría, pero el vacío histórico de 700 commits sin auditoría persiste.

---

## 8. RESUMEN CRONOLÓGICO

```
MAYO 27 – MAYO 28, 2026
├── main (1 commit, 278 archivos) — ARQUITECTURA SSR
│   ├── Error 0.1: SSR acoplado [C6] → REINICIO TOTAL
│   ├── Error 0.2: Sin DTOs ni repositorios [C4]
│   └── Error 0.3: Subdirectorio anidado [C1]
│
MAYO 27 – JUNIO 9, 2026
├── ga03-integraciones (39 commits, 576 archivos) — HÍBRIDO SSR+SPA
│   ├── Error 1.1: Jinja2 residual [C6] → REINICIO TOTAL (99.8% descartado)
│   ├── Error 1.2: Angular NgModules [C1]
│   ├── Error 1.3: Estructura caótica [C1, C8] → 19 commits de reubica
│   └── Error 1.4: Sin tests [C2]
│
JUNIO 9 – JUNIO 20, 2026
├── ta06 Fase I (~250 commits, 160→800 archivos) — RECONSTRUCCIÓN
│   ├── Error 2.1: God files [C1] → descomposición masiva
│   ├── Error 2.2: Airflow 2→3 [C5] → ~55 commits de migración
│   └── Error 2.3: Conexiones DB no centralizadas [C4]
│
JUNIO 21 – JUNIO 30, 2026
├── ta06 Fase II (~326 commits, 800→1,300 archivos) — EXPLOSIÓN FEATURES
│   ├── Error 3.1: DTOs desincronizados [C2, C8] → 6+ commits de fix
│   ├── Error 3.2: Roles tardíos [C2] → cascada de refactors
│   ├── Error 3.3: State machine rota [C2] → estados bloqueados
│   └── Error 3.4: CORS iterativo [C6]
│
JULIO 1 – JULIO 12, 2026
└── ta06 Fase III (~209 commits, 1,300→1,723 archivos) — PULIDO
    ├── Error 4.1: Colores hardcodeados [C8] → migración a CSS variables
    ├── Error 4.2: Templates rehechos [C1]
    ├── Error 4.3: SSE frágil [C3]
    └── Error 4.4: Auditoría tardía [C2] → Transactional Outbox
```

---

## 9. TABLA DE CORRESPONDENCIA: 18 ERRORES → 8 CONCEPTOS DE CLASE → DECISIONES

> **Todos los conceptos provienen de: Construcción de Software (6to semestre)** — ETL, arquitectura, modelo de negocios, Airflow, Python, objetivos operativos.

| # | Error | Concepto violado | Decisión tomada |
|---|-------|-----------------|-----------------|
| 0.1 | SSR acoplado (backend generaba HTML) | **C6** — Separación de capas ETL→API→Frontend | Eliminar SSR; SPA pura + API pura |
| 0.2 | Sin repositorios ni DTOs | **C1, C4** — Arquitectura de datos como especificación + conocer motor documental | Implementar repositorios + DTOs + mappers |
| 0.3 | Subdirectorio anidado | **C1** — Spec-Driven: estructura como especificación | Estructura plana: `frontend/`, `server/`, `infra/` |
| 1.1 | Jinja2 persistente (SSR residual) | **C6** — Separación de capas: frontend 100% independiente | Eliminar Jinja2; Nginx sirve estáticos |
| 1.2 | Angular NgModules obsoleto | **C1** — Componentes autosuficientes por dominio | Angular Standalone + `bootstrapApplication` |
| 1.3 | Estructura caótica | **C1, C8** — Convenciones documentadas + consistencia | 19 commits de reubica; estándar desde día 0 |
| 1.4 | Sin plan de pruebas | **C2** (parcial) — Fallos en intersecciones no detectados hasta producción | Suite pytest + Jasmine/Karma desde fases tempranas |
| 2.1 | God files monolíticos | **C1** — Responsabilidad única por módulo | Descomposición: 4-6 submódulos por god file |
| 2.2 | Airflow 2→3 mal planificado | **C5** — Idempotencia y versionado de infraestructura | Pinear dependencias; planificar migraciones |
| 2.3 | Conexiones DB no centralizadas | **C4** — Pool compartido para MongoDB | `server/src/database/` como Singleton |
| 3.1 | Mappers/DTOs desincronizados | **C2, C8** — Contrato de API + dos formatos para el mismo dato (camelCase/snake_case) | Contract-First; generar tipos desde OpenAPI |
| 3.2 | Roles agregados tardíamente | **C2** (parcial) — Patrón de "corregir intersecciones tardíamente" aplicado a RBAC | RBAC completo antes de implementar endpoints |
| 3.3 | State machine sin validación | **C2** — Checkin↔Reservations modificando el mismo estado sin coordinación | Validación estricta en backend (`state_machine.md`) |
| 3.4 | CORS mal configurado | **C6** — Reverse proxy unificado; separación de orígenes en desarrollo vs producción | `proxy.conf.json` (dev) + `nginx.conf` (prod) |
| 4.1 | Colores hardcodeados (400+ ocurrencias) | **C8** — Tokens semánticos = contrato visual (equivalente a DTOs en la capa de presentación) | Variables CSS + `color-mix()`; theme desde un archivo |
| 4.2 | Templates rehechos 2-3 veces | **C1** — Componentes diseñados desde el modelo mental del negocio | SCSS partials; componente = unidad de negocio |
| 4.3 | SSE sin reconexión robusta | **C3** (parcial) — Decisión técnica que afecta el cumplimiento del alcance operativo | SSE + polling; planificada migración a WebSockets |
| 4.4 | Auditoría tras 700 commits | **C2, C5** — Auditoría como "módulo que debió conocer cada operación" + Outbox para idempotencia | Transactional Outbox (`059aa53`) |

---

## 10. MATRIZ DE IMPACTO: QUÉ CONCEPTO CAUSÓ QUÉ CAMBIO

| # | Concepto | ¿Causó cambio de rama? | ¿Causó cambio interno en ta06? | Errores relacionados | Gravedad |
|---|----------|----------------------|------------------------------|---------------------|----------|
| **C1** | Spec-Driven Development | ✅ Contribuyó (estructura por dominio) | ✅ Reubica, specs, descomposición god files | 0.3, 1.2, 1.3, 2.1, 4.2 | 🔴 Alta |
| **C2** | Casos de Uso Completos | ❌ No directamente | ✅ State machine, mapper fixes, Outbox, RBAC, tests | 1.4, 3.1, 3.2, 3.3, 4.4 | 🔴 Alta |
| **C3** | Alcance Operativo Acotado | ❌ No | ✅ Housekeeping simplificado, reviews removidos, SSE→WS | 4.3 | 🟡 Media |
| **C4** | Conocer Motor de BD | ❌ No | ✅ ETL incremental mode, pool centralizado | 0.2, 2.3 | 🟡 Media |
| **C5** | Idempotencia de Migraciones | ❌ No | ✅ Modo incremental ETL, scripts con nombres | 2.2 | 🟡 Media |
| **C6** | Config Build vs Runtime | ✅ **SÍ — causa principal del pivote SSR→SPA** | ✅ Dockerfile, nginx, proxy CORS | 0.1, 1.1, 3.4 | 🔴 Alta |
| **C7** | Fragilidad de Parser | ❌ No | ❌ No verificado | — | 🟢 Baja |
| **C8** | Consistencia de Convenciones | ❌ No directamente | ✅ **El más impacto interno**: 6+ fixes mapper/DTO, migración SCSS | 1.3, 3.1, 4.1 | 🔴 Alta |

### Los 3 conceptos que MÁS impactaron:

1. **C8 — Consistencia de Convenciones** (6+ commits de fix, migración SCSS de 400+ ocurrencias). Dos mecanismos de ID (UUID vs ObjectId), camelCase vs snake_case, mappers no estandarizados.

2. **C2 — Casos de Uso Completos** (estados bloqueados, transiciones inválidas, Transactional Outbox implementado 700 commits tarde, RBAC agregado tardíamente).

3. **C6 — Configuración Build vs Runtime / Separación de Capas** (**causó 2 reinicios completos**: main→ga03 y ga03→ta06). El error más caro del proyecto.

---

## 11. CONCLUSIÓN

### 11.1 La Regla de los Tres Intentos

HotelData necesitó **tres intentos** para alcanzar una arquitectura sólida:

1. **`main`** — Demostró que SSR era inviable para una plataforma enterprise que debía consumir datos de un pipeline ETL y exponerlos en una SPA reactiva
2. **`ga03`** — Demostró que mantener inercia del pasado (Jinja2, Angular Modules, estructura caótica) condena el proyecto a un reinicio inevitable
3. **`ta06`** — Demostró que empezar desde cero con la arquitectura correcta (SPA pura + API pura + ETL independiente) es más rápido que parchar una incorrecta

### 11.2 Los 5 Errores Más Caros

| # | Error | Costo | Concepto |
|---|-------|-------|----------|
| 1 | Arquitectura SSR en vez de capas separadas | **2 reinicios completos** (main + ga03 descartados) | C6 |
| 2 | Convenciones inconsistentes (camelCase/snake_case, UUID/ObjectId) | **6+ commits de fix + migración SCSS de 400+ ocurrencias** | C8 |
| 3 | Casos de uso sin probar intersecciones entre módulos | **Estados bloqueados, Trans. Outbox tardío, RBAC refactorizado** | C2 |
| 4 | Colores hardcodeados en 400+ lugares | **Migración masiva de ~30 archivos SCSS** | C8 |
| 5 | God files monolíticos (1,098 líneas) | **Descomposición de 4+ archivos masivos** | C1 |

### 11.3 Lo que Sí Funcionó

- **MongoDB** como destino del modelo dimensional derivado de Expedia (flexible para datos semiestructurados)
- **FastAPI** como backend API pura (rendimiento, OpenAPI autogenerado)
- **Angular Standalone** como frontend SPA (32 módulos de negocio con lazy loading granular)
- **Docker multi-contenedor** (frontend, backend, Airflow, MongoDB — cada uno en su contenedor)
- **Estructura de directorios estandarizada** (`frontend/`, `server/`, `infra/`, `dags/`, `scripts/`) — el legado más valioso de `ga03`

### 11.4 Lección Final

> **"Es más barato tirar código y empezar de nuevo con la arquitectura correcta que mantener código con la arquitectura equivocada."**

Los dos reinicios del proyecto no fueron fracasos — fueron **iteraciones de aprendizaje**. Cada reinicio eliminó una capa de errores:

- El primer reinicio eliminó el **SSR** (C6)  
- El segundo reinicio eliminó **Jinja2**, **Angular Modules** y la **estructura caótica** (C6, C1, C8)

El resultado final — `ta06-integrations` con **780 commits** y **1,723 archivos** — es un sistema empresarial que desde su primer día se construyó sobre principios sólidos: ETL independiente con Airflow, API REST pura con FastAPI, SPA con Angular Standalone, y 32 módulos organizados por dominio de negocio real. Los datasets de Expedia fluyen a través del pipeline hacia MongoDB, y desde allí se exponen al frontend mediante contratos de API bien definidos — el flujo que `main` y `ga03` intentaron construir pero solo `ta06` logró materializar.

---

> **Fin de la Bitácora V3 (Definitiva)**  
> *Documento generado a partir del análisis forense de 820 commits en 3 ramas, abarcando 47 días de desarrollo.*  
> *18 errores documentados, mapeados a 8 conceptos de clase, verificados contra evidencia concreta de commits y archivos.*  
> *HotelData — Construcción del Software, Tarea 10, Sexto Semestre.*

> [!NOTE] **PARA EL ESTUDIANTE:** Todos los conceptos provienen de **una sola materia: Construcción de Software** (6to semestre), que integra ETL, arquitectura, modelo de negocios, Airflow, Python, datasets masivos (Expedia), PocketBase como sistema de extracción inicial, ingeniería inversa para modelado dimensional (star schema: fact + dimensiones), y objetivos operativos/tácticos/estratégicos. El pipeline completo es: CSV/Expedia → PocketBase (v0.26.3, puerto 8090) → JSONL → Parquet → Airflow DAGs → MongoDB → FastAPI → Angular. El proyecto está actualmente en **nivel operativo**. Verifica que los 8 conceptos coincidan con el énfasis dado por el ingeniero en clase.

---

## APÉNDICE A: CONCEPTO C7 — FRAGILIDAD DEL PARSER INGENUO (NO APLICABLE)

> **Principio original:** *"Los fixtures de test partían el SQL de los schemas con un simple .split(';'), sin considerar que un ';' puede aparecer dentro de un comentario sin ser un separador de sentencias."*

**Por qué no aplica a HotelData:**

Este principio describe un problema específico de **parsers SQL** donde `.split(';')` rompe sentencias si hay punto y coma dentro de comentarios. El proyecto HotelData:

1. Usa **MongoDB** como base de datos principal — no ejecuta SQL dinámicamente en producción
2. El único archivo SQL (`docs/database/ga03_modelo_datos.sql`) es **documentación**, no código ejecutado
3. Los scripts que sí usan `.split()` (`cargar_reservas_hoteleras_03.py`, `validate_ga03_full_integrations.py`) parsean **CSVs o logs**, no SQL

**¿Hay un riesgo equivalente?** Sí — un parser ingenuo de CSV que use `.split(',')` sin manejar comas dentro de valores entrecomillados es vulnerable al mismo tipo de bug. Pero **no se encontró evidencia en commits** de que este riesgo se haya materializado y forzado un cambio de arquitectura o reinicio.

**Veredicto:** 🟢 **No aplicable al proyecto.** Este principio se incluye en la lista de 8 conceptos por requerimiento de la tarea, pero la evidencia forense no muestra que haya tenido impacto en las decisiones de rama ni en cambios internos.
