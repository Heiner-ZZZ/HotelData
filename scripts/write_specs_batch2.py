#!/usr/bin/env python3
"""Write detailed spec content to specs 028-050."""
import os

BASE = os.path.join(os.path.dirname(__file__), '..', '.specify', 'specs')

specs = {}

specs['028-reportes-revenue'] = """# Especificacion: Reportes de Revenue

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O26 (Consultar reportes de revenue y mercado), CU-E02 (Analizar conversion digital y CAC), CU-E05 (Analizar mercados visitantes), CU-E06 (Definir estrategia de revenue)

## 1. Objetivo

Consultar reportes y dashboards de revenue, conversion, mercados, top hoteles/destinos/paises basados en el modelo estrella.

## 2. Contexto

El modelo estrella almacena datos de busqueda y reserva en fact_hotel_reservations con 12 dimensiones. Los reportes agregan estos datos para mostrar KPIs.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Gerente de hotel | Consulta reportes operativos |
| Revenue manager | Analiza revenue y conversion |
| Marketing hotelero | Analiza mercados y campanas |
| Auditor de datos | Consulta calidad y tendencias |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar dashboard con eventos totales, reservas, clicks, revenue, precio promedio | Alta |
| RF-002 | El sistema debe mostrar top hoteles por revenue | Alta |
| RF-003 | El sistema debe mostrar top destinos por demanda | Alta |
| RF-004 | El sistema debe mostrar top paises visitantes por eventos | Alta |
| RF-005 | El sistema debe permitir filtrar por periodo (dia, semana, mes, trimestre) | Alta |
| RF-006 | El sistema debe calcular tasa de conversion y CTR | Alta |

## 5. Reglas de negocio

- Los KPIs se calculan agregando fact_hotel_reservations con $lookup a dimensiones
- Booking Conversion Rate = reservas / eventos x 100
- CTR = clicks / eventos x 100
- Los datos son de solo lectura

## 6. Entradas

GET /api/reports/revenue/summary?period=month&from=2026-01-01&to=2026-06-22

## 7. Salidas

```json
{
  "data": {
    "total_events": 150000,
    "total_clicks": 45000,
    "total_bookings": 12000,
    "total_revenue": 1800000.00,
    "avg_price": 150.00,
    "conversion_rate": 8.0,
    "ctr": 30.0,
    "top_hotels": [{ "prop_id": "HOTEL001", "revenue": 250000 }]
  }
}
```

## 8. Escenarios

### Escenario 1: Consultar dashboard de revenue
```gherkin
Dado que el revenue manager esta autenticado
Cuando consulta el dashboard de revenue mensual
Entonces ve eventos, reservas, conversion, revenue y precio promedio
Y puede ver top hoteles, destinos y paises
```

## 9. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Dashboard muestra KPIs correctos del modelo estrella |
| CA-002 | Filtros por periodo funcionan |
| CA-003 | Top hoteles/destinos/paises se muestran correctamente |

## 10. Dependencias

- Coleccion fact_hotel_reservations
- Dimensiones: dim_hotels, dim_destinations, dim_visitor_countries, dim_dates

## 11. Fuera de alcance

- Forecasting predictivo con ML
- Dashboard en tiempo real (streaming)
"""

specs['029-reportes-calidad'] = """# Especificacion: Reportes de Calidad de Datos

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O27 (Consultar reporte de calidad y registros rechazados), CU-E07 (Evaluar calidad de datos, pipeline Airflow)

## 1. Objetivo

Consultar reportes de calidad de datos generados por cada ejecucion ETL, incluyendo registros procesados, rechazados y completitud.

## 2. Contexto

Cada ejecucion ETL produce un reporte de calidad en data_quality_reports. Los rechazos van a rejected_records con razon exacta.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Auditor de Datos | Revisa calidad y registros rechazados |
| Operador de datos | Monitorea ejecuciones ETL |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar lista de ejecuciones ETL con fecha, estado, duracion | Alta |
| RF-002 | El sistema debe mostrar detalle de calidad por ejecucion | Alta |
| RF-003 | El sistema debe listar registros rechazados con razon y raw_record | Alta |
| RF-004 | El sistema debe mostrar completitud por columna (% de nulls) | Alta |
| RF-005 | El sistema debe permitir exportar reporte a PDF/CSV | Media |

## 5. Reglas de negocio

- Cada ejecucion ETL produce exactamente un reporte de calidad
- Los registros rechazados incluyen raw_record completo y rejection_reason
- Las ejecuciones se registran en etl_executions

## 6. Escenarios

### Escenario 1: Consultar reporte de calidad
```gherkin
Dado que el auditor consulta la lista de ejecuciones
Cuando selecciona una ejecucion especifica
Entonces ve el detalle con total, aceptados, rechazados
Y la completitud por columna
```

## 7. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Lista de ejecuciones se muestra correctamente |
| CA-002 | Detalle de calidad por ejecucion funciona |
| CA-003 | Registros rechazados se listan con razon |
| CA-004 | Exportacion a PDF/CSV funciona |

## 8. Dependencias

- Coleccion etl_executions
- Coleccion data_quality_reports
- Coleccion rejected_records
- Modulo src/etl/validate.py

## 9. Fuera de alcance

- Alertas automaticas cuando la calidad baja de un umbral
- ML para deteccion de anomalias en calidad
"""

specs['030-usuarios-roles'] = """# Especificacion: Usuarios, Roles y Permisos

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T09 (Administrar usuarios, roles, permisos y navegacion por rol)

## 1. Objetivo

Administrar usuarios del sistema, roles, permisos y reglas de navegacion por rol (RBAC completo). 9 roles con permisos granulares.

## 2. Contexto

El sistema tiene 9 roles: super_admin, admin_sistema, cliente, recepcionista, hotel_partner, gerente_hotel, revenue_manager, marketing_hotelero, auditor_datos.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Super Admin | Administracion global del sistema |
| Admin Sistema | Gestion operativa de usuarios |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe listar usuarios con filtros por rol, estado activo/inactivo | Alta |
| RF-002 | El sistema debe permitir activar/desactivar usuarios | Alta |
| RF-003 | El sistema debe permitir cambiar el rol de un usuario | Alta |
| RF-004 | El sistema debe definir permisos por rol en route_permissions.py | Alta |
| RF-005 | El sistema debe proteger rutas con AuthGuard + RoleGuard | Alta |
| RF-006 | El sistema debe adaptar sidebar segun el rol del usuario | Alta |

## 5. Reglas de negocio

- 9 roles fijos con permisos predefinidos
- Un usuario tiene exactamente un rol
- Los permisos se definen en route_permissions.py
- Frontend: AuthGuard y RoleGuard protegen rutas

## 6. Escenarios

### Escenario 1: Cambiar rol de usuario
```gherkin
Dado que el admin selecciona un usuario hotel_partner
Cuando cambia su rol a gerente_hotel
Entonces el usuario accede a las rutas de gerente_hotel
```

### Escenario 2: Desactivar usuario
```gherkin
Dado que el admin desactiva un usuario
Cuando el usuario intenta iniciar sesion
Entonces el sistema rechaza el login
```

## 7. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | CRUD de usuarios funciona con filtros |
| CA-002 | Cambio de rol actualiza permisos inmediatamente |
| CA-003 | Usuario desactivado no puede iniciar sesion |
| CA-004 | Guards de Angular protegen rutas correctamente |

## 8. Dependencias

- Colecciones: users, roles, permissions, role_permissions
- Modulo: src/app/security/permissions.py, route_permissions.py
- Frontend: auth.guard.ts, role.guard.ts, sidebar-nav.ts

## 9. Fuera de alcance

- Roles personalizados (solo 9 fijos)
- Permisos granulares por recurso (solo por ruta)
"""

specs['031-contratos-api'] = """# Especificacion: Contratos API

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T02 (Gestionar contratos API, endpoints y documentacion OpenAPI)

## 1. Objetivo

Gestionar contratos API, endpoints JSON documentados con OpenAPI y validacion frontend-backend.

## 2. Contexto

FastAPI genera documentacion OpenAPI automaticamente en /docs. Los contratos se validan con scripts.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Admin sistema | Gestiona documentacion y contratos |
| Desarrollador | Consulta documentacion OpenAPI |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe exponer OpenAPI en /docs con todos los endpoints | Alta |
| RF-002 | El sistema debe tener scripts de validacion de contrato frontend-backend | Alta |
| RF-003 | El sistema debe exponer endpoint de health check | Alta |
| RF-004 | El sistema debe usar Pydantic models para validacion | Alta |

## 5. Escenarios

### Escenario 1: Validar contratos frontend-backend
```gherkin
Dado que se ejecuta el script de validacion de contratos
Cuando encuentra discrepancias
Entonces reporta las rutas faltantes o incorrectas
```

## 6. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | OpenAPI en /docs muestra todos los endpoints |
| CA-002 | Health check responde correctamente |
| CA-003 | Scripts de validacion no reportan errores |

## 7. Dependencias

- FastAPI (OpenAPI automatico)
- Scripts: validate_frontend_backend_contract.py, validate_angular_routes_contract.py

## 8. Fuera de alcance

- API keys para partners externos
- Rate limiting
"""

specs['032-monitoreo-servicios'] = """# Especificacion: Monitoreo de Servicios

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T11 (Monitorear servicios), CU-E04 (Monitorear disponibilidad global)

## 1. Objetivo

Monitorear el estado de los servicios del sistema: backend FastAPI, Redis, MongoDB, Airflow, frontend Angular.

## 2. Contexto

Docker Compose con 6 servicios. Cada servicio tiene health checks. El backend expone endpoints de health check.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Super Admin | Monitorea estado global |
| Admin Sistema | Diagnostica problemas de servicios |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe exponer endpoint GET /health | Alta |
| RF-002 | El sistema debe verificar conexion a MongoDB | Alta |
| RF-003 | El sistema debe verificar estado de Redis | Alta |
| RF-004 | El sistema debe exponer un panel de monitoreo basico | Media |

## 5. Reglas de negocio

- Cada servicio se verifica individualmente
- MongoDB: db.command('ping')
- Redis: redis_client.ping()

## 6. Salidas

```json
{
  "status": "ok",
  "services": {
    "mongodb": { "status": "ok", "response_time_ms": 5 },
    "redis": { "status": "ok", "response_time_ms": 2 }
  }
}
```

## 7. Escenarios

### Escenario 1: Consultar health check
```gherkin
Dado que el admin consulta GET /health
Cuando todos los servicios funcionan
Entonces el sistema responde con status ok
```

## 8. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | /health responde con estado de todos los servicios |
| CA-002 | MongoDB ping funciona |
| CA-003 | Redis ping funciona |

## 9. Dependencias

- Modulo: src/app/modules/health/routes.py
- MongoDB, Redis, PocketBase

## 10. Fuera de alcance

- Alertas automaticas (email, Slack)
- Historial de uptime
"""

specs['033-pipeline-etl'] = """# Especificacion: Pipeline ETL

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T12 (Ejecutar y validar pipeline Airflow sobre 600000 registros), CU-E07 (Evaluar calidad de datos)

## 1. Objetivo

Ejecutar el pipeline ETL orquestado por Airflow que extrae datos desde PocketBase, transforma a dimensiones y hechos, y carga en MongoDB.

## 2. Contexto

Pipeline GA03 procesa ~600k registros. Usa Airflow con PythonOperator. 14 tareas, chunk 50k, batch 5k.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Operador de datos | Ejecuta y monitorea pipeline |
| Auditor de Datos | Revisa calidad post-ejecucion |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Airflow debe ejecutar DAG hoteldata_ga03_etl con 14 tareas | Alta |
| RF-002 | El DAG debe usar solo PythonOperator | Alta |
| RF-003 | El pipeline debe extraer datos desde PocketBase | Alta |
| RF-004 | El pipeline debe transformar a dimensiones (upsert) y hechos (batch insert) | Alta |
| RF-005 | El pipeline debe generar reporte de calidad por ejecucion | Alta |
| RF-006 | El pipeline debe registrar rechazos en rejected_records | Alta |

## 5. Reglas de negocio

- Solo PythonOperator (no BashOperator)
- Chunk size: 50,000 filas, batch insert: 5,000 documentos
- Dimensiones primero (upsert), hechos despues (batch insert)

## 6. Flujo del DAG

extract_from_pocketbase validate_schema convert_to_jsonl convert_to_parquet build_dim_* (8 tareas) build_fact load_to_mongodb generate_quality_report

## 7. Escenarios

### Escenario 1: Ejecutar pipeline exitosamente
```gherkin
Dado que Airflow inicia el DAG hoteldata_ga03_etl
Cuando se ejecutan las 14 tareas
Entonces los datos se cargan en MongoDB
Y se genera el reporte de calidad
```

## 8. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | DAG se ejecuta con 14 tareas PythonOperator |
| CA-002 | Datos se cargan en MongoDB correctamente |
| CA-003 | Reporte de calidad se genera por ejecucion |
| CA-004 | test_dag_boundaries.py pasa |


## 9. Dependencias

- DAG: server/dags/hoteldata_ga03_etl.py
- Modulos: src/etl/tasks.py, ta02_dimensions.py, ta02_fact.py, transform_clean.py, validate.py
- PocketBase (fuente), MongoDB (destino)

## 10. Fuera de alcance

- Streaming en tiempo real (solo batch)
"""

specs['034-balanced-scorecard'] = """# Especificacion: Balanced Scorecard

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-E01 (Consultar Balanced Scorecard), CU-E08 (Generar reporte gerencial consolidado)

## 1. Objetivo

Consultar el Balanced Scorecard organizado en 4 perspectivas (Financiera, Cliente, Procesos Internos, Aprendizaje/Tecnologia) con KPIs y semaforos.

## 2. Contexto

El BSC conecta los objetivos estrategicos con KPIs medibles desde el modelo estrella.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Gerente general | Toma decisiones estrategicas |
| Super Admin | Supervisa KPIs globales |

## 4. KPIs por perspectiva

### Financiera
| KPI | Formula | Meta |
|-----|---------|------|
| Revenue bruto | SUM(price_usd WHERE reserva_bool=true) | +15% por ciclo |
| Precio promedio | AVG(price_usd) | Subir por segmento |

### Cliente
| KPI | Formula | Meta |
|-----|---------|------|
| Tasa de conversion | reservas / eventos x 100 | Mejora trimestral |
| CTR | clicks / eventos x 100 | >30% |
| Rating promedio resenas | AVG(rating) | >4.0 |

### Procesos Internos
| KPI | Formula | Meta |
|-----|---------|------|
| Ejecuciones ETL exitosas | COUNT(status=success) / total | >95% |
| Tiempo promedio ETL | AVG(duration) | <60 min |

### Aprendizaje/Tecnologia
| KPI | Formula | Meta |
|-----|---------|------|
| Cobertura integraciones | endpoints documentados / total | 100% |

## 5. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar BSC con 4 perspectivas y sus KPIs | Alta |
| RF-002 | Cada KPI debe tener indicador visual (semaforo) | Alta |
| RF-003 | El sistema debe mostrar tendencia del KPI | Alta |
| RF-004 | El sistema debe permitir exportar reporte gerencial | Media |

## 6. Escenarios

### Escenario 1: Consultar BSC
```gherkin
Dado que el gerente general consulta el BSC
Cuando ve las 4 perspectivas
Entonces cada perspectiva muestra sus KPIs con semaforo y tendencia
```

## 7. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | BSC muestra 4 perspectivas con KPIs |
| CA-002 | Semaforos se calculan segun metas |
| CA-003 | Exportacion de reporte funciona |

## 8. Dependencias

- Colecciones: fact_hotel_reservations, dim_*, etl_executions, data_quality_reports
"""

specs['035-analisis-mercados'] = """# Especificacion: Analisis de Mercados

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-E05 (Analizar mercados visitantes, destinos, canales y hoteles con mayor rendimiento)

## 1. Objetivo

Analizar mercados visitantes, destinos, canales y hoteles con mayor rendimiento usando las dimensiones del modelo estrella.

## 2. Contexto

Las dimensiones permiten segmentar por pais visitante, destino, canal y propiedad.

## 3. KPIs por dimension

| Dimension | KPI | Formula |
|-----------|-----|---------|
| dim_visitor_countries | Top paises por eventos | COUNT(eventos) GROUP BY pais |
| dim_visitor_countries | Conversion por pais | reservas / eventos x 100 |
| dim_destinations | Top destinos por demanda | COUNT(busquedas) GROUP BY destino |
| dim_sites | Distribucion por canal | COUNT(eventos) GROUP BY site_name |
| dim_hotels | Hoteles con mayor revenue | SUM(price_usd) GROUP BY prop_id |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar top paises por eventos y conversion | Alta |
| RF-002 | El sistema debe mostrar top destinos por demanda y revenue | Alta |
| RF-003 | El sistema debe mostrar distribucion por canal | Alta |
| RF-004 | El sistema debe mostrar hoteles con mayor rendimiento | Alta |

## 5. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Top paises se muestra con eventos y conversion |
| CA-002 | Top destinos con demanda y revenue |
| CA-003 | Distribucion por canal correcta |

## 6. Dependencias

- Colecciones: fact_hotel_reservations, dim_visitor_countries, dim_destinations, dim_sites, dim_hotels
"""

specs['036-estrategia-revenue'] = """# Especificacion: Estrategia de Revenue

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-E06 (Definir estrategia de revenue, campanas, pricing y proyeccion de demanda)

## 1. Objetivo

Definir estrategia de revenue, campanas y pricing mediante forecasting y analisis de promociones.

## 2. Actores

| Actor | Descripcion |
|-------|-------------|
| Revenue manager | Define estrategia de precios y promociones |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar tendencias de precio promedio por destino y temporada | Alta |
| RF-002 | El sistema debe mostrar efectividad de promociones | Alta |
| RF-003 | El sistema debe permitir proyectar demanda | Media |
| RF-004 | El sistema debe mostrar revenue por canal y segmento | Alta |

## 4. Escenarios

### Escenario 1: Analizar efectividad de promociones
```gherkin
Dado que el revenue manager consulta efectividad
Cuando compara revenue con promocion vs sin promocion
Entonces ve la diferencia en conversion
```

## 5. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Tendencias de precio se muestran correctamente |
| CA-002 | Efectividad de promociones se compara correctamente |
| CA-003 | Proyeccion de demanda usa datos historicos |

## 6. Dependencias

- Colecciones: fact_hotel_reservations, dim_promotions, dim_dates
"""

specs['037-integraciones-api'] = """# Especificacion: Integraciones API

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-E03 (Evaluar ingresos, consumo y madurez de integraciones API)

## 1. Objetivo

Evaluar el consumo de APIs del sistema y la madurez de integraciones con partners externos.

## 2. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe documentar todos los endpoints en OpenAPI (/docs) | Alta |
| RF-002 | El sistema debe exponer health checks de API | Alta |
| RF-003 | El sistema debe registrar consumo de API por endpoint en logs | Media |

## 3. Escenarios

### Escenario 1: Evaluar madurez de integraciones
```gherkin
Dado que el admin consulta la seccion de integraciones
Entonces el sistema muestra lista de endpoints disponibles
Y su estado de validacion
```

## 4. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Documentacion OpenAPI completa en /docs |
| CA-002 | Health check endpoint funcional |
| CA-003 | Logs de consumo de API registrados |

## 5. Dependencias

- Modulos: todos los routers de FastAPI
- Scripts: server/scripts/validate_*.py
"""

specs['038-etl-ingesta'] = """# Especificacion: ETL - Ingesta de Datos

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T12 (Ejecutar y validar pipeline Airflow)

## 1. Objetivo

Extraer datos desde PocketBase y CSV, validar esquema, y convertir a JSONL + Parquet.

## 2. Contexto

El pipeline ingiere datos desde PocketBase y los transforma a formato intermedio antes de cargar a MongoDB.

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Extraer datos desde PocketBase via API | Alta |
| RF-002 | Extraer datos desde CSV local | Alta |
| RF-003 | Validar esquema minimo de columnas requeridas | Alta |
| RF-004 | Convertir a JSONL (staging) | Alta |
| RF-005 | Convertir a Parquet (processed) | Alta |
| RF-006 | Procesar en chunks de 50k filas | Alta |

## 4. Flujo de datos

PocketBase - JSONL - Parquet - Dimensiones (upsert) - Fact (batch insert) - MongoDB

## 5. Dependencias

- server/src/etl/tasks.py
- server/src/etl/transform_clean.py
- PocketBase como fuente de datos
"""

specs['039-etl-dimensiones'] = """# Especificacion: ETL - Transformacion de Dimensiones

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T12 (Ejecutar y validar pipeline Airflow)

## 1. Objetivo

Transformar datos a 12 dimensiones del modelo estrella con upsert.

## 2. Dimensiones

| Dimension | Key Field | Coleccion |
|-----------|-----------|-----------|
| dim_hotels | prop_id | dim_hotels |
| dim_destinations | srch_destination_id | dim_destinations |
| dim_visitor_countries | visitor_location_country_id | dim_visitor_countries |
| dim_sites | site_id | dim_sites |
| dim_dates | date_key (YYYYMMDD) | dim_dates |
| dim_promotions | promotion_flag | dim_promotions |
| dim_click_status | click_bool | dim_click_status |
| dim_reservation_status | reserva_bool | dim_reservation_status |
| dim_occupancy_profile | occupancy_profile_id | dim_occupancy_profile |
| dim_stay_length_category | stay_length_category_id | dim_stay_length_category |
| dim_booking_window_category | booking_window_category_id | dim_booking_window_category |
| dim_price_category | price_category_id | dim_price_category |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Construir y cargar las 12 dimensiones con upsert | Alta |
| RF-002 | No duplicar registros en operaciones upsert | Alta |

## 4. Dependencias

- server/src/etl/ta02_dimensions.py
- Datos Parquet del paso de ingesta
"""

specs['040-etl-fact-tables'] = """# Especificacion: ETL - Fact Tables

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T12 (Ejecutar y validar pipeline Airflow)

## 1. Objetivo

Transformar datos a fact tables con batch insert, validacion de calidad y rejected_records.

## 2. Fact Tables

| Fact Table | Grain | Coleccion |
|------------|-------|-----------|
| fact_hotel_reservations | 1 evento de busqueda | fact_hotel_reservations |
| fact_hotel_events | Evento legacy TAF01 | fact_hotel_events |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Cargar fact_hotel_reservations con batch insert de 5k documentos | Alta |
| RF-002 | Validar campos obligatorios: srch_id, date_key, prop_id, price_usd | Alta |
| RF-003 | Rechazar price_usd < 0, occupancy invalida, srch_id duplicados | Alta |
| RF-004 | Reportar conteos de insertados vs rechazados | Alta |

## 4. Dependencias

- server/src/etl/ta02_fact.py
- server/src/etl/validate.py
- Datos Parquet y dimensiones cargadas previamente
"""

specs['041-modelo-estrella'] = """# Especificacion: Modelo Estrella

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: Todos los CU analiticos

## 1. Objetivo

Diseno del modelo estrella con 12 dimensiones y 5 fact tables.

## 2. Estructura

### Fact Tables (5)
fact_hotel_reservations, fact_hotel_events, data_quality_reports, etl_executions, rejected_records

### Dimensiones (12)
dim_hotels, dim_destinations, dim_visitor_countries, dim_sites, dim_dates, dim_promotions, dim_click_status, dim_reservation_status, dim_occupancy_profile, dim_stay_length_category, dim_booking_window_category, dim_price_category

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Mantener 12 dimensiones con upsert y key fields | Alta |
| RF-002 | Mantener fact_hotel_reservations como fact table principal | Alta |
| RF-003 | Asegurar integridad referencial | Alta |

## 4. Dependencias

- Colecciones: 12 dim_*, fact_hotel_reservations, fact_hotel_events
- Modulos: src/etl/ta02_dimensions.py, src/etl/ta02_fact.py
"""

specs['042-seguridad-incidentes'] = """# Especificacion: Seguridad e Incidentes

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O01, CU-T09 (Arquitectura de seguridad, perimetro, activos, plan de incidentes)

## 1. Objetivo

Definir la arquitectura de seguridad del sistema: perimetro, activos protegidos, plan de incidentes educacional.

## 2. Contexto

Proyecto educacional sin datos reales de huespedes. La postura de seguridad previene exposicion accidental.

## 3. Perimetro de seguridad

Internet (solo frontend Angular) - Nginx (proxy, TLS) - FastAPI (auth, RBAC) - MongoDB (red interna Docker)

## 4. Activos protegidos

| Activo | Proteccion |
|--------|-----------|
| Credenciales | bcrypt + sesiones TTL 8h |
| Sesiones | Hash SHA-256 en DB, cookie httponly |
| .env | .gitignore + env_file Docker |

## 5. Fuera de alcance (seguridad enterprise)

Rate limiting, CSRF tokens, PCI DSS, cifrado en reposo, hardening de contenedores
"""

specs['043-frontend-auth'] = """# Especificacion: Frontend - Autenticacion

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O01, CU-O28, CU-O29 (Login, logout, cambio de contrasena y perfil)

## 1. Objetivo

Componentes frontend de autenticacion: login page, guards, interceptors, layouts por rol.

## 2. Componentes

| Componente | Ruta | Descripcion |
|------------|------|-------------|
| LoginPage | /auth/login | Formulario de inicio de sesion |
| AuthGuard | - | Protege rutas que requieren autenticacion |
| RoleGuard | - | Protege rutas segun rol del usuario |
| AuthInterceptor | - | Adjunta cookie de sesion a requests |
| AccessNav | - | Navegacion adaptativa por rol |
| SidebarNav | - | Sidebar con modulos segun rol |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | LoginPage con formulario de email + contrasena | Alta |
| RF-002 | AuthGuard redirige a /auth/login si no hay sesion | Alta |
| RF-003 | RoleGuard redirige a /403 si el rol no tiene permiso | Alta |
| RF-004 | AuthInterceptor envia cookie en cada request | Alta |
| RF-005 | Sidebar/access-nav se adapta segun el rol | Alta |

## 4. Dependencias

- frontend/src/app/features/auth/
- frontend/src/app/core/guards/
- frontend/src/app/core/interceptors/
"""

specs['044-frontend-partner'] = """# Especificacion: Frontend - Gestion Hotelera (Partner)

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O12 al CU-O21 (Partner: rooms, inventory, rates, policies, content)

## 1. Objetivo

UI de gestion hotelera: propiedades, habitaciones, inventario, tarifas, politicas, contenido.

## 2. Componentes

| Componente | Ruta | CU asociado |
|------------|------|-------------|
| PropertyListPage | /management/properties | CU-O12 |
| PropertyEditPage | /management/properties/:id/edit | CU-O12 |
| RoomTypesPage | /management/rooms | CU-O14 |
| InventoryCalendar | /management/availability | CU-O15, CU-O16 |
| RatePlansPage | /management/rates | CU-O17, CU-O18 |
| PoliciesPage | /management/policies | CU-O20 |
| ContentPage | /management/content | CU-O21 |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | PropertyListPage con tabla de propiedades asignadas | Alta |
| RF-002 | PropertyEditPage con formulario de edicion de perfil | Alta |
| RF-003 | RoomTypesPage con CRUD de tipos de habitacion | Alta |
| RF-004 | InventoryCalendar con vista mensual | Alta |
| RF-005 | RatePlansPage con tabla de planes tarifarios | Alta |
| RF-006 | PoliciesPage con formulario de politicas | Alta |
| RF-007 | ContentPage con editor de descripcion y amenities | Alta |

## 4. Dependencias

- frontend/src/app/features/partner/
- partner.routes.ts
"""

specs['045-frontend-cliente'] = """# Especificacion: Frontend - Experiencia Cliente

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O02 al CU-O07 (Busqueda, filtros, detalle, reserva, mis reservas, cancelacion)

## 1. Objetivo

UI de cliente: busqueda de hoteles, filtros, comparacion, detalle, reserva y cancelacion.

## 2. Componentes

| Componente | Ruta | CU asociado |
|------------|------|-------------|
| HotelSearchPage | /hotels/search | CU-O02 |
| HotelDetailPage | /hotels/:id | CU-O04 |
| ComparePage | /hotels/compare | CU-O03 |
| BookingForm | /reservations/new | CU-O05 |
| MyReservationsPage | /reservations | CU-O06 |
| CancelDialog | - | CU-O07 |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | HotelSearchPage con filtros (precio, rating, amenities, destino) | Alta |
| RF-002 | HotelDetailPage con galeria, tarifas, resenas | Alta |
| RF-003 | ComparePage con tabla lado a lado de hasta 3 hoteles | Alta |
| RF-004 | BookingForm con seleccion de tipo habitacion | Alta |
| RF-005 | MyReservationsPage con lista de reservas y estados | Alta |
| RF-006 | CancelDialog con confirmacion | Alta |

## 4. Dependencias

- frontend/src/app/features/booking/
"""

specs['046-frontend-admin'] = """# Especificacion: Frontend - Administracion

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T09, CU-T10, CU-T11 (Usuarios, roles, auditoria, monitoreo, permisos)

## 1. Objetivo

UI de administracion: gestion de usuarios y roles, panel de auditoria, monitoreo de servicios.

## 2. Componentes

| Componente | Ruta | CU asociado |
|------------|------|-------------|
| UsersPage | /system/users | CU-T09 |
| RolesPage | /system/permissions | CU-T09 |
| AuditPage | /system/audit | CU-T10 |
| MonitoringPage | /system/monitoring | CU-T11 |
| OwnershipListPage | /ownership/users | CU-T09 |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | UsersPage con tabla de usuarios, activar/desactivar, cambiar rol | Alta |
| RF-002 | RolesPage con matriz de permisos por rol | Alta |
| RF-003 | AuditPage con tabla de actividad filtrable | Alta |
| RF-004 | MonitoringPage con health checks de servicios | Media |

## 4. Dependencias

- frontend/src/app/features/system-admin/
- system-admin.routes.ts
"""

specs['047-frontend-facturacion'] = """# Especificacion: Frontend - Facturacion

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O24, CU-O25 (Facturacion y pagos)

## 1. Objetivo

UI de facturacion: listado/detalle de facturas y pagos, creacion de factura y registro de pago.

## 2. Componentes

| Componente | Ruta | CU asociado |
|------------|------|-------------|
| InvoicesListPage | /billing/invoices | CU-O24 |
| InvoiceDetailPage | /billing/invoices/:id | CU-O24 |
| PaymentsListPage | /billing/payments | CU-O25 |
| PaymentDetailPage | /billing/payments/:id | CU-O25 |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | InvoicesListPage con tabla de facturas por booking y estado | Alta |
| RF-002 | InvoiceDetailPage con detalle de factura | Alta |
| RF-003 | PaymentsListPage con tabla de pagos | Alta |
| RF-004 | Crear factura desde detalle de reserva | Alta |
| RF-005 | Registrar pago simulado desde detalle de factura | Alta |

## 4. Dependencias

- frontend/src/app/features/billing/
- modules/billing/routes.py
"""

specs['048-frontend-resenas'] = """# Especificacion: Frontend - Resenas

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O22, CU-O23 (Registro y moderacion de resenas)

## 1. Objetivo

UI de resenas: listado, detalle, moderacion, respuesta del hotel.

## 2. Componentes

| Componente | Ruta | CU asociado |
|------------|------|-------------|
| ReviewForm | /reviews/new | CU-O22 |
| ReviewListPage | /reviews | CU-O22 |
| ModeratePage | /reviews/moderate | CU-O23 |
| ReviewDetailPage | /reviews/:id | CU-O23 |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | ReviewForm con rating 1-5, titulo, comentario | Alta |
| RF-002 | ReviewListPage visible en detalle de hotel | Alta |
| RF-003 | ModeratePage con tabla de resenas pendientes | Alta |
| RF-004 | Botones de aprobar/rechazar con confirmacion | Alta |
| RF-005 | Formulario de respuesta del hotel en resena aprobada | Alta |

## 4. Dependencias

- frontend/src/app/features/reviews/
- modules/reviews/routes.py
"""

specs['049-infra-docker'] = """# Especificacion: Infraestructura Docker

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T11, CU-E04 (Monitorear servicios, disponibilidad global)

## 1. Objetivo

Desplegar y mantener el sistema con Docker Compose: 6 servicios con health checks.

## 2. Servicios

| Servicio | Imagen | Puerto | Proposito |
|----------|--------|--------|-----------|
| mongo | mongo:7.0 | 27017 | Base de datos |
| redis | redis:7.4 | 6379 | Cache |
| pocketbase | pocketbase:0.22 | 8090 | Fuente ETL |
| server | custom (python:3.12-slim) | 8000 | FastAPI |
| airflow | custom (apache/airflow:3.2.2) | 8080 | Orquestador ETL |
| frontend | custom (nginx:alpine) | 4200:80 | Angular SPA |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | docker-compose.yml con 6 servicios y health checks | Alta |
| RF-002 | Versiones pinneadas para reproducibilidad | Alta |
| RF-003 | Red compartida entre servicios | Alta |
| RF-004 | Volumenes persistentes (mongo_data, redis_data, pb_data) | Alta |

## 4. Dependencias

- infra/docker-compose.yml
- frontend/Dockerfile
- infra/Dockerfile
- infra/docker/airflow3.Dockerfile
"""

specs['050-configuracion-entornos'] = """# Especificacion: Configuracion de Entornos

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: Todos (configuracion global del sistema)

## 1. Objetivo

Configuracion global del sistema: settings.py, .env, CORS, chunk/batch sizes, paths.

## 2. Variables de configuracion

| Variable | Default | Descripcion |
|----------|---------|-------------|
| MONGODB_URL | mongodb://mongo:27017 | Conexion MongoDB |
| REDIS_URL | redis://redis:6379 | Conexion Redis |
| POCKETBASE_URL | http://pocketbase:8090 | Conexion PocketBase |
| SESSION_TTL_HOURS | 8 | Duracion de sesion |
| CORS_ORIGINS | http://localhost:4200 | Origenes CORS |
| CHUNK_SIZE | 50000 | Filas por chunk ETL |
| BATCH_SIZE | 5000 | Documentos por batch insert |
| DATA_DIR | data/ | Directorio de datos |

## 3. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | settings.py carga correctamente las variables de .env |
| CA-002 | CORS configurado para el origen del frontend |
| CA-003 | Chunk y batch sizes configurados correctamente |

## 4. Dependencias

- server/config/settings.py
- server/config/.env.example
- server/config/redis_settings.py
"""

# Write all spec files
written = 0
errors = 0
for folder, content in specs.items():
    filepath = os.path.join(BASE, folder, 'spec.md')
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content.lstrip('\n'))
        written += 1
        print(f'OK: {folder}')
    except Exception as e:
        errors += 1
        print(f'ERROR: {folder}: {e}')

print(f'\nTotal: {written} written, {errors} errors')
