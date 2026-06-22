# Especificación General: HotelData 

**Versión**: 1.0 | **Estado**: Draft | **Última actualización**: 2026-06-21

## 1. Objetivo

HotelData es una plataforma híbrida de gestión hotelera y analítica para grupos multi-propiedad. Su propósito es proveer un sistema unificado donde los hoteleros gestionan su operación diaria (inventario de habitaciones, tarifas, reservas, check-in/out, contenido de propiedad) y simultáneamente obtienen una fuente única de verdad para analítica de reservas, ingresos, ocupación y comportamiento de búsqueda a nivel de portafolio.

## 2. Contexto

La industria hotelera opera con 30 a 70 sistemas diferentes por grupo (PMS, CRS, Channel Manager, RMS, POS, CRM, BI, mantenimiento, finanzas). Cada sistema tiene su propio esquema, rate codes y definiciones de segmento. El problema central no es la falta de datos — es que los datos no hablan el mismo idioma. HotelData resuelve esto proporcionando una interfaz unificada para operación diaria y un pipeline ETL que traduce datos de múltiples fuentes a un esquema estrella consistente.

## 3. Actores del sistema

| Actor | CU asociados | Descripción |
|-------|-------------|-------------|
| Cliente / Viajero | CU-O02 al CU-O07, CU-O22, CU-O28, CU-O29 | Busca hoteles, filtra, compara, solicita reservas, consulta historial, cancela, registra reseñas, recibe comprobantes |
| Hotel Partner | CU-O12, CU-O14, CU-O20, CU-T03, CU-T04, CU-T07 | Administra propiedades, perfiles, habitaciones, disponibilidad, políticas, tarifas |
| Gerente de hotel | CU-O08 al CU-O11, CU-O15, CU-O16, CU-O24, CU-O25 | Supervisa reservas, check-in/out, disponibilidad, operación diaria |
| Revenue Manager | CU-O17 al CU-O19, CU-O26, CU-T01, CU-T06 | Configura planes tarifarios, promociones, cupones, analiza revenue |
| Marketing hotelero | CU-O21, CU-O23, CU-T01, CU-T08, CU-T13 | Gestiona campañas, reseñas, contenido, imágenes, amenities |
| Super Admin / Admin sistema | CU-O28, CU-O29, CU-T02, CU-T09, CU-T11 | Administra usuarios, roles, permisos, monitoreo, configuración global |
| Operador de datos | CU-O27, CU-T11, CU-T12 | Ejecuta pipeline ETL, revisa cargas, calidad de datos, reportes |
| Auditor de datos | CU-O13, CU-O27, CU-T10 | Consulta auditoría, sesiones, cambios de perfil, trazabilidad |
| Sistema FastAPI / Airflow | CU-O24, CU-O25, CU-T12 | Ejecuta validaciones, ETL, métricas, reportes, auditoría |

## 4. Requisitos funcionales

### RF-001: Gestión de autenticación
El sistema debe permitir que cualquier usuario inicie sesión con credenciales (email + contraseña), cierre sesión, y administre su cuenta y contraseña.
- **CU relacionados**: CU-O01, CU-O28, CU-O29

### RF-002: Búsqueda y experiencia cliente
El sistema debe permitir que los clientes busquen hoteles, filtren por precio/destino/capacidad, comparen opciones, vean detalle y soliciten reservas.
- **CU relacionados**: CU-O02, CU-O03, CU-O04, CU-O05

### RF-003: Gestión de reservas
El sistema debe permitir crear, consultar y cancelar reservas tanto por clientes como por gerentes de hotel, con trazabilidad completa de estados.
- **CU relacionados**: CU-O06, CU-O07, CU-O08, CU-O09, CU-O10, CU-O11

### RF-004: Gestión hotelera (Partner)
El sistema debe permitir a hoteles partner gestionar tipos de habitación, inventario, tarifas, políticas, amenities, imágenes y contenido de propiedad.
- **CU relacionados**: CU-O12 al CU-O21, CU-T03 al CU-T08

### RF-005: Reseñas y reputación
El sistema debe permitir registrar reseñas de huéspedes, moderar contenido y responder con trazabilidad, alimentando métricas de satisfacción.
- **CU relacionados**: CU-O22, CU-O23, CU-T13

### RF-006: Facturación y pagos
El sistema debe generar comprobantes/facturas asociados a reservas y registrar pagos con estados y trazabilidad.
- **CU relacionados**: CU-O24, CU-O25

### RF-007: Reportes y analítica
El sistema debe exponer dashboards y reportes de revenue, conversión, calidad de datos, Balanced Scorecard y análisis de mercados.
- **CU relacionados**: CU-O26, CU-O27, CU-E01, CU-E02, CU-E05, CU-E06, CU-E08

### RF-008: Administración del sistema
El sistema debe permitir gestionar usuarios, roles, permisos, contratos API, monitoreo de servicios y evaluación de integraciones.
- **CU relacionados**: CU-T02, CU-T09, CU-T10, CU-T11, CU-E03, CU-E04

### RF-009: Pipeline ETL
El sistema debe ejecutar pipelines ETL que extraigan datos desde PocketBase, los transformen a un modelo estrella y los carguen en MongoDB con reportes de calidad.
- **CU relacionados**: CU-T12, CU-E07, CU-O27

### RF-010: Modelo estrella (Star Schema)
El sistema debe mantener 12 dimensiones y 5 fact tables con integridad referencial y soporte para consultas analíticas.

## 5. Requisitos no funcionales

| ID | Requisito | Descripción | CU relacionado |
|---|-----------|-------------|---------------|
| RNF-001 | Seguridad | Autenticación JWT, sesiones con TTL 8h, bcrypt para contraseñas, RBAC con 9 roles | CU-O01, CU-T09 |
| RNF-002 | Rendimiento API | Respuestas JSON en menos de 500ms para consultas operativas | Todos los CU |
| RNF-003 | Rendimiento ETL | Pipeline debe procesar 600k registros en menos de 30 minutos | CU-T12 |
| RNF-004 | Disponibilidad | 6 servicios Docker con health checks y arranque reproducible | CU-T11, CU-E04 |
| RNF-005 | Trazabilidad | Toda operación crítica registrada en colecciones de auditoría | CU-T10, CU-O13 |
| RNF-006 | Calidad de datos | Cada ejecución ETL produce reporte de calidad, 0 descartes silenciosos | CU-E07, CU-O27 |
| RNF-007 | Usabilidad | UI Angular con Signals, navegación por rol, lazy loading | Todos los CU |
| RNF-008 | Portabilidad | Docker Compose con 6 servicios, config reproducible vía .env | CU-E04 |

## 6. Reglas de negocio

| ID | Regla | CU relacionado |
|----|-------|---------------|
| RN-001 | Solo usuarios autenticados pueden acceder a rutas protegidas | CU-O01 |
| RN-002 | Cada propiedad tiene prop_id técnico inmutable | CU-T03 |
| RN-003 | manual_override evita que ETL sobrescriba nombres editados manualmente | CU-T03 |
| RN-004 | Una reserva sigue estados: pending → confirmed → checked_in → checked_out → cancelled | CU-O05 al CU-O11 |
| RN-005 | No se puede check-in sin reserva válida confirmada | CU-O10 |
| RN-006 | Un estudiante no puede reseñar sin haber tenido una reserva | CU-O22 |
| RN-007 | Las reseñas pasan por moderación antes de ser públicas | CU-O23 |
| RN-008 | Los pagos son simulados, sin integración bancaria real (proyecto educacional) | CU-O25 |
| RN-009 | El pipeline ETL nunca debe importar src.app (separación de capas) | CU-T12 |
| RN-010 | Las contraseñas nunca se almacenan en texto plano | CU-O01, CU-O29 |

## 7. Entradas del sistema

| Categoría | Datos de entrada | Origen |
|-----------|-----------------|--------|
| Credenciales | email, password | Formulario login |
| Búsqueda | destino, fecha entrada/salida, adultos, niños, habitaciones | Formulario búsqueda |
| Reserva | hotel, tipo habitación, fechas, huéspedes | Formulario reserva |
| Inventario | fecha, room_type, total_disponible, blocked | Formulario partner |
| Tarifas | fecha, rate_plan_id, price | Formulario revenue |
| Contenido | descripciones, imágenes, políticas, amenities | Formulario partner |
| Reseña | rating, comentario, booking_id | Formulario cliente |
| Factura | booking_id, método pago | Sistema / Gerente |
| ETL | CSV desde PocketBase | Pipeline Airflow |

## 8. Salidas del sistema

| Categoría | Salida | Formato |
|-----------|--------|---------|
| Autenticación | Sesión iniciada / error credenciales | Cookie + JSON |
| Búsqueda | Lista de hoteles con filtros | JSON / HTML |
| Reserva | Confirmación / error | JSON / HTML |
| Reportes | Dashboard, revenue, calidad | JSON / HTML |
| ETL | Reporte de calidad, registros rechazados | JSON |
| Auditoría | Historial de cambios por entidad | JSON / HTML |

## 9. Escenarios principales

### Escenario 1: Flujo completo de cliente
Dado que existe un cliente registrado con sesión activa
Cuando busca hoteles por destino y fecha, selecciona un hotel, ve detalle, y solicita una reserva
Entonces el sistema crea la reserva en estado pending, registra el evento en booking_orders y booking_status_history, y muestra confirmación al cliente.

### Escenario 2: Flujo completo de partner
Dado que existe un hotel partner autenticado
Cuando accede al panel de gestión, configura tipos de habitación, inventario por fecha y tarifas
Entonces el sistema guarda los datos en room_types, room_inventory_calendar y hotel_rate_calendar respectivamente, y queda visible para búsqueda de clientes.

### Escenario 3: Pipeline ETL completo
Dado que el operador de datos ejecuta el pipeline GA03
Cuando Airflow orquesta extracción desde PocketBase, transformación a dimensiones y hechos, y carga en MongoDB
Entonces el sistema produce data_quality_reports, etl_executions, y rejected_records con 0 descartes silenciosos.

## 10. Criterios de aceptación

| ID | Criterio | Verificación |
|----|----------|-------------|
| CA-001 | Los 29 CU operativos (CU-O01 a CU-O29) tienen endpoints funcionales | pytest por cada CU |
| CA-002 | Los 13 CU tácticos (CU-T01 a CU-T13) tienen módulos implementados | pytest por cada CU |
| CA-003 | Los 8 CU estratégicos (CU-E01 a CU-E08) tienen dashboards o reportes | Verificación visual |
| CA-004 | El pipeline ETL procesa 600k registros sin errores | Reporte calidad |
| CA-005 | La matriz de trazabilidad vincula cada tarea a su CU | Review gate |
| CA-006 | Compilación TypeScript sin errores (`tsc --noEmit`) | CI |
| CA-007 | Tests pasan (`pytest -q`) | CI |

## 11. Restricciones

- Sin integración bancaria real — pagos simulados, sin PCI DSS
- Sin despliegue cloud — entorno Docker local
- Sin datos reales de huéspedes — solo datos sintéticos
- Sin BashOperator en DAGs de Airflow — solo PythonOperator
- Sin MongoDB Aggregation Pipeline como ETL principal
- Las contraseñas usan bcrypt, sin encriptación reversible

## 12. Dependencias

| Dependencia | Versión | Propósito |
|-------------|---------|-----------|
| Python | 3.12 | Runtime |
| FastAPI | 0.110+ | Web framework |
| MongoDB | 7.0 | Base de datos única |
| Redis | 7.4 | Caché opcional |
| Apache Airflow | 3.2.2 | Orquestador ETL |
| Angular | 21 | Frontend standalone |
| PocketBase | 0.22.0 | Fuente de datos ETL |

## 13. Fuera de alcance

- Integración con OTAs reales (Booking.com, Expedia)
- Pasarela de pagos real (Stripe, PayPal)
- Despliegue cloud (AWS, GCP, Azure)
- Aplicación móvil nativa
- Machine Learning predictivo implementado (solo documentado en TAF06)
- Deep Learning (OCR, clasificación imágenes, análisis sentimiento)
- Seguridad enterprise (rate limiting, CSRF, cifrado en reposo)
