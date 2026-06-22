# TA07 — Documento de Especificaciones del Sistema HotelData

**Asignatura**: Construcción del Software — Sexto semestre
**Sistema**: HotelData Hub — Plataforma de gestión hotelera y analítica
**Versión del documento**: 1.0 | **Fecha**: 2026-06-21
**Base**: TAF06 — Estrategia y Visión Arquitectónica

---

# 1. CONSTITUCIÓN DEL PROYECTO

## 1.1 La Empresa

HotelData es una plataforma web de gestión y analítica hotelera orientada a clientes, hoteles partner, gerentes, revenue managers, marketing hotelero, super administración, operadores y auditores de datos. Su propuesta combina una aplicación Angular, servicios FastAPI, base MongoDB, Redis, Docker y Airflow para sostener una operación hotelera digital con análisis de datos masivos.

Actualmente el sistema trabaja con 600 000 registros hoteleros procesados y organizados mediante colecciones de hechos y dimensiones. Esta base permite estudiar eventos de búsqueda, reservas, clicks, precios, promociones, destinos, países visitantes, canales, propiedades, tarifas y calidad de datos.

| Aspecto | Descripción |
|---------|-------------|
| **Tecnología principal** | Angular, FastAPI, MongoDB, Redis, Docker, Airflow |
| **Qué hace** | Gestiona búsqueda, reservas, propiedades, habitaciones, disponibilidad, tarifas, políticas, amenities, reseñas, facturación/comprobantes, reportes y gobierno de datos |
| **A quién sirve** | Clientes/viajeros, hoteles partner, gerentes, revenue managers, marketing hotelero, super administración, operadores y auditores de datos |
| **Seguridad** | JWT, roles, permisos, rutas segmentadas y navegación por rol |
| **Problema que resuelve** | Reduce dispersión operativa, mejora conversión digital, centraliza datos y permite decisiones de mercado basadas en BI |
| **Modelo de datos** | Fact-Dim, dashboards, reportes y trazabilidad |
| **Alcance actual** | Plataforma operativa y analítica con módulos de cliente, management, sistema, pipeline, auditoría, reseñas y facturación/comprobantes. 600 000 registros, endpoints JSON, validaciones y documentación técnica |

## 1.2 Misión

Brindar una plataforma digital confiable para gestionar reservas, propiedades hoteleras, datos operativos y analíticos, facilitando la adquisición automatizada de clientes, la administración hotelera, la integración con ecosistemas externos y la toma de decisiones basada en datos.

## 1.3 Visión

Ser una plataforma hotelera digital de referencia para mercados internacionales, reconocida por su capacidad de escalar comercialmente, integrarse mediante APIs, mantener alta disponibilidad y convertir datos hoteleros masivos en ventaja competitiva para hoteles y partners.

## 1.4 Objetivos del Proyecto

### Objetivo General

Implementar un sistema de gestión hotelera que cubra el ciclo operativo completo: desde la búsqueda y reserva del cliente hasta la administración de propiedades, tarifas, reseñas, facturación y reportes, todo sobre una arquitectura modular y escalable.

### Objetivos Específicos

| ID | Objetivo Específico | Alcance |
|----|---------------------|---------|
| OE1 | Implementar autenticación segura con JWT, sesiones y RBAC de 9 roles | Sistema y seguridad |
| OE2 | Desarrollar el módulo de búsqueda y experiencia del cliente con filtros, detalle y comparación | Experiencia cliente |
| OE3 | Implementar el ciclo completo de reservas: solicitud, confirmación, check-in, check-out y cancelación | Core de reservas |
| OE4 | Desarrollar la gestión hotelera: tipos de habitación, inventario, tarifas, políticas, amenities e imágenes | Gestión hotelera |
| OE5 | Implementar el módulo de reseñas con registro, moderación y respuesta | Reputación online |
| OE6 | Desarrollar facturación y pagos asociados a reservas con trazabilidad | Respaldo documental |
| OE7 | Implementar reportes operativos de revenue, calidad de datos y mercado | Analítica y reportes |
| OE8 | Desarrollar el módulo de usuarios, roles, permisos y monitoreo del sistema | Administración del sistema |

---

# 2. RELACIÓN ORGANIZACIONAL

## 2.1 Niveles Organizacionales de HotelData

HotelData se estructura en tres niveles organizacionales que conectan la estrategia de negocio con la ejecución operativa diaria dentro del sistema.

| Nivel | Responsables | Qué define | Horizonte |
|-------|-------------|-----------|-----------|
| **Estratégico** | Gerencia, dueños, super administración | Expansión internacional, modelo de ingresos, alianzas, APIs, ventaja competitiva y metas globales | Largo plazo |
| **Táctico** | Revenue manager, marketing hotelero, admin sistema, gerente hotel, partner | Campañas, tarifas, integraciones, dashboards, roles, disponibilidad, reportes y gestión operativa | Mediano plazo |
| **Operativo** | Cliente, recepcionista, gerente hotel, auditor datos, sistema FastAPI/Airflow | Búsquedas, reservas, login JWT, check-in/out, cambios de perfil, reseñas, facturación, ETL y auditoría | Corto plazo |

## 2.2 Objetivos Estratégicos (OE)

| Código | Objetivo Estratégico |
|--------|---------------------|
| **OE1** | Penetrar mercados hoteleros digitales nacionales e internacionales mediante una plataforma web de búsqueda, comparación, reputación, reserva y respaldo documental que convierta eventos de navegación en oportunidades reales de captación de clientes |
| **OE2** | Escalar comercialmente HotelData mediante servicios API, módulos de gestión hotelera y capacidades reutilizables que permitan operar propiedades, preparar integraciones externas y reducir la dependencia de procesos manuales aislados |
| **OE3** | Asegurar expansión continua y disponibilidad técnica de HotelData mediante una arquitectura portable basada en Docker, FastAPI, Angular, MongoDB, Redis y Airflow que permita operar, validar y escalar servicios sin depender de configuraciones manuales dispersas |
| **OE4** | Consolidar inteligencia de negocio hotelera centralizada mediante MongoDB Fact-Dim, dashboards, reportes, BI, segmentación, modelos predictivos y control de calidad para transformar datos de búsqueda y reserva en decisiones estratégicas |
| **OE5** | Optimizar eficiencia operativa hotelera mediante monitoreo de estado de habitaciones, housekeeping, mantenimiento preventivo y gestión geoespacial de destinos que reduzca tiempos muertos entre reservas y mejore la experiencia del huésped |

## 2.3 Objetivos Tácticos (OT)

| Código | Objetivo Táctico | OE asociado |
|--------|------------------|-------------|
| **OT1.1** | Automatizar captación digital internacional mediante búsqueda, reserva, campañas y analítica de embudo | OE1 |
| **OT1.2** | Fortalecer reputación, confianza del huésped, reseñas, comprobantes y comunicación digital | OE1 |
| **OT2.1** | Estandarizar servicios por API, contratos JSON, seguridad JWT y documentación OpenAPI | OE2 |
| **OT2.2** | Integrar módulos comerciales y operativos: propiedades, habitaciones, tarifas, políticas, amenities y contenido | OE2 |
| **OT3.1** | Mantener infraestructura portable y escalable con Docker, Redis, MongoDB, Angular y FastAPI | OE3 |
| **OT3.2** | Automatizar procesamiento de datos, gobierno, ETL/ELT, calidad, auditoría y trazabilidad | OE3 |
| **OT4.1** | Consolidar analítica hotelera global mediante dashboards y reportes de management | OE4 |
| **OT4.2** | Aplicar BI, IA, modelos predictivos, segmentación, forecasting y detección de anomalías | OE4 |
| **OT2.3** | Enriquecer catálogo geoespacial de destinos con mapa interactivo y edición de metadata de nombres y coordenadas | OE2 |
| **OT3.3** | Automatizar gestión de limpieza, rotación, mantenimiento y cargos adicionales de habitaciones | OE3 |
| **OT5.1** | Monitorear eficiencia operativa mediante indicadores de limpieza, mantenimiento, ocupación y cargos adicionales | OE5 |

## 2.4 Objetivos Operativos (OO)

| Código | Objetivo Operativo | OT asociado |
|--------|-------------------|-------------|
| **OO1.1.1** | Registrar eventos de búsqueda y reserva digital con país, destino, canal, hotel, fecha y usuario | OT1.1 |
| **OO1.1.2** | Medir conversión de búsqueda, detalle, click, reserva, abandono y revenue por segmento | OT1.1 |
| **OO1.1.3** | Gestionar campañas promocionales multicanal (email, SMS, push) con segmentación de mercado | OT1.1 |
| **OO1.1.4** | Atender consultas de clientes mediante asistente virtual (chatbot IA) con escalamiento a humano | OT1.1 |
| **OO1.1.5** | Gestionar up-selling y ancillaries durante la estancia (upgrade de habitación, late check-out, extras) | OT1.1 |
| **OO1.2.1** | Registrar reseñas de estancia y respuestas del hotel con moderación y trazabilidad | OT1.2 |
| **OO1.2.2** | Generar comprobantes/facturación, registro de pago y cargos adicionales asociados a la reserva | OT1.2 |
| **OO1.2.3** | Enviar notificaciones transaccionales al huésped (confirmación de reserva, recordatorio check-in, factura) | OT1.2 |
| **OO2.1.1** | Exponer endpoints JSON para hoteles, reservas, management, sistema, auth y reportes | OT2.1 |
| **OO2.1.2** | Validar JWT, sesión, permisos, rol y navegación por cada endpoint sensible | OT2.1 |
| **OO2.2.1** | Administrar perfil comercial de hotel con nombres visibles manuales y prop_id estable | OT2.2 |
| **OO2.2.2** | Conectar habitaciones, tarifas, disponibilidad, políticas, amenities e imágenes | OT2.2 |
| **OO3.1.1** | Ejecutar servicios principales con Docker y configuración reproducible | OT3.1 |
| **OO3.1.2** | Monitorear Redis, backend, contratos, health checks y estado de servicios | OT3.1 |
| **OO3.2.1** | Ejecutar pipeline Airflow para cargar, validar y actualizar 600 000 registros incrementales | OT3.2 |
| **OO3.2.2** | Registrar auditoría funcional, sesiones, cambios, historial y calidad de datos | OT3.2 |
| **OO4.1.1** | Consultar dashboard ejecutivo con eventos, reservas, revenue, precio medio y calidad | OT4.1 |
| **OO4.1.2** | Analizar mercados, destinos, canales, países visitantes y hoteles con mayor rendimiento | OT4.1 |
| **OO4.2.1** | Proyectar demanda, revenue, conversión, ocupación y campañas por mercado | OT4.2 |
| **OO4.2.2** | Detectar anomalías, registros rechazados, caídas de conversión e inconsistencias | OT4.2 |
| **OO2.3.1** | Editar metadata de destinos (nombre visible, coordenadas geográficas, país, ciudad, descripción) | OT2.3 |
| **OO2.3.2** | Editar nombre visible de hotel (manual_override sobre hoteles con ID numérico) | OT2.3 |
| **OO2.3.3** | Visualizar destinos y hoteles en mapa mundial interactivo con geolocalización | OT2.3 |
| **OO2.3.4** | Gestionar contenidos multimedia con geolocalización (fotos, videos vinculados a coordenadas) | OT2.3 |
| **OO3.3.1** | Consultar estado actual, limpieza y disponibilidad de cada habitación individual | OT3.3 |
| **OO3.3.2** | Gestionar rotación de limpieza y asignación de tareas de housekeeping | OT3.3 |
| **OO3.3.3** | Programar y registrar mantenimiento preventivo de habitaciones e instalaciones | OT3.3 |
| **OO3.3.5** | Gestionar alertas operativas internas al staff (housekeeping, mantenimiento, recepción) | OT3.3 |
| **OO5.1.1** | Monitorear eficiencia operativa: tiempo de rotación, cumplimiento de mantenimiento, ocupación real vs disponible, cargos extra, efectividad de up-selling | OT5.1 |

## 2.5 Jerarquía Completa OE → OT → OO

```
OE1: Penetrar mercados hoteleros digitales
  ├── OT1.1: Automatizar captación digital internacional
  │      ├── OO1.1.1: Registrar eventos de búsqueda y reserva
  │   ├── OO1.1.2: Medir conversión del embudo digital
  │   ├── OO1.1.3: Gestionar campañas promocionales multicanal
  │   ├── OO1.1.4: Atender consultas con chatbot IA
  │   └── OO1.1.5: Gestionar up-selling y ancillaries
  └── OT1.2: Fortalecer reputación del huésped
      ├── OO1.2.1: Registrar reseñas de estancia
      ├── OO1.2.2: Generar comprobantes/facturación y cargos
      └── OO1.2.3: Enviar notificaciones transaccionales

OE2: Escalar comercialmente mediante APIs y módulos
  ├── OT2.1: Estandarizar servicios por API
  │   ├── OO2.1.1: Exponer endpoints JSON
  │   └── OO2.1.2: Validar JWT y roles por endpoint
  └── OT2.2: Integrar módulos comerciales y operativos
      ├── OO2.2.1: Administrar perfil comercial de hotel
      └── OO2.2.2: Conectar habitaciones, tarifas, disponibilidad

OE3: Asegurar disponibilidad técnica
  ├── OT3.1: Mantener infraestructura portable
  │   ├── OO3.1.1: Ejecutar servicios con Docker
  │   └── OO3.1.2: Monitorear Redis, backend, health checks
  └── OT3.2: Automatizar procesamiento y gobierno de datos
      ├── OO3.2.1: Ejecutar pipeline ETL con Airflow
      └── OO3.2.2: Registrar auditoría y trazabilidad

OE4: Consolidar inteligencia de negocio hotelera
  ├── OT4.1: Consolidar analítica hotelera global
  │   ├── OO4.1.1: Consultar dashboard ejecutivo
  │   └── OO4.1.2: Analizar mercados y destinos
  └── OT4.2: Aplicar BI, IA y modelos predictivos
      ├── OO4.2.1: Proyectar demanda y revenue
      └── OO4.2.2: Detectar anomalías y problemas de calidad

OE2: Escalar comercialmente mediante APIs y módulos
  └── OT2.3: Enriquecer catálogo geoespacial de destinos
      ├── OO2.3.1: Editar metadata de destinos
      ├── OO2.3.2: Editar nombre visible de hotel
      ├── OO2.3.3: Visualizar destinos en mapa interactivo
      └── OO2.3.4: Gestionar contenidos multimedia con geolocalización

OE3: Asegurar disponibilidad técnica
  └── OT3.3: Automatizar gestión de habitaciones
      ├── OO3.3.1: Consultar estado y disponibilidad de habitaciones
      ├── OO3.3.2: Gestionar limpieza, rotación y tareas housekeeping
      ├── OO3.3.3: Programar y registrar mantenimiento preventivo
      ├── OO3.3.4: Registrar cargos adicionales (absorbido en facturación)
      └── OO3.3.5: Gestionar alertas operativas internas al staff

OE5: Optimizar eficiencia operativa hotelera
  └── OT5.1: Monitorear eficiencia operativa
      └── OO5.1.1: Monitorear eficiencia operativa y efectividad de up-selling
```

---

# 3. DEPARTAMENTOS

## 3.1 Estructura Departamental de HotelData

La operación de HotelData se organiza en 6 departamentos que cubren todas las áreas funcionales del negocio hotelero digital. Cada departamento agrupa procesos, casos de uso y responsables específicos.

### Departamento 1: Comercial / Experiencia Cliente

| Elemento | Descripción |
|----------|-------------|
| **Responsable** | Gerente general / Marketing |
| **Función** | Gestionar la experiencia del cliente desde la búsqueda hasta la reserva, maximizando la conversión y la satisfacción del viajero |
| **Procesos** | Búsqueda de hoteles, filtros comerciales, comparación de alternativas, visualización de detalle, solicitud de reserva, consulta de historial, cancelación |
| **Sistemas que usa** | Módulo de hoteles (búsqueda), módulo de reservas (solicitud), frontend Angular |
| **CU asociados** | CU-O02, CU-O03, CU-O04, CU-O05, CU-O06, CU-O07 |
| **KPIs** | Tasa de conversión, click rate, tiempo medio de reserva, revenue por cliente |

### Departamento 2: Revenue Management

| Elemento | Descripción |
|----------|-------------|
| **Responsable** | Revenue Manager |
| **Función** | Configurar y optimizar tarifas, planes tarifarios, promociones y cupones para maximizar el ingreso por habitación disponible |
| **Procesos** | Creación de planes tarifarios, configuración de tarifas por fecha, creación de promociones y cupones, análisis de revenue |
| **Sistemas que usa** | Módulo revenue (tarifas, promociones), rate_plans, hotel_rate_calendar |
| **CU asociados** | CU-O17, CU-O18, CU-O19, CU-O26, CU-O34, CU-O36 |
| **KPIs** | ADR (Average Daily Rate), RevPAR, revenue bruto, precio promedio, ocupación, ingresos por up-selling |

### Departamento 3: Marketing Hotelero

| Elemento | Descripción |
|----------|-------------|
| **Responsable** | Marketing hotelero |
| **Función** | Gestionar la reputación online, contenido comercial, imágenes, amenities y campañas de promoción para atraer y retener huéspedes |
| **Procesos** | Gestión de reseñas, moderación y respuesta, actualización de contenido, imágenes, amenities, edición de nombre comercial |
| **Sistemas que usa** | Módulo de reseñas, módulo partner (contenido, imágenes), frontend Angular |
| **CU asociados** | CU-O12, CU-O21, CU-O22, CU-O23 |
| **KPIs** | Puntuación promedio de reseñas, tasa de reseñas respondidas, completitud de perfil |

### Departamento 4: Operaciones Hoteleras

| Elemento | Descripción |
|----------|-------------|
| **Responsable** | Recepcionista / Gerente de hotel / Hotel partner |
| **Función** | Ejecutar la operación diaria del hotel: atención al huésped en front desk, check-in/out, reservas manuales, facturación, gestión de tipos de habitación, inventario, disponibilidad y políticas |
| **Procesos** | Check-in, check-out, reservas manuales, facturación, pagos, consulta de solicitudes, creación de tipos de habitación, actualización de inventario, bloqueos, gestión de políticas |
| **Sistemas que usa** | Módulo partner (rooms, availability, policies), módulo reservas (check-in/out), módulo billing (facturas, pagos) |
| **CU asociados** | CU-O08 (Recepcionista), CU-O09 (Gerente), CU-O10 (Recepcionista), CU-O11 (Recepcionista), CU-O14, CU-O15 (Gerente), CU-O16 (Gerente), CU-O20, CU-O24 (Recepcionista), CU-O25 (Recepcionista), CU-O30, CU-O33 |
| **KPIs** | Ocupación, días de inventario configurado, check-ins/outs por día, tiempo de estancia media, cargos adicionales promedio |

### Departamento 5: Administración / Sistemas

| Elemento | Descripción |
|----------|-------------|
| **Responsable** | Super Admin |
| **Función** | Administrar usuarios, roles, permisos, autenticación, monitoreo de servicios, contratos API, configuración global del sistema y auditoría |
| **Procesos** | Gestión de usuarios, roles y permisos, autenticación JWT, monitoreo de servicios, gestión de contratos API, auditoría, navegación por rol |
| **Sistemas que usa** | Módulo admin (usuarios, roles, permisos), módulo auth (login, sesiones), módulo settings, módulo audit |
| **CU asociados** | CU-O01, CU-O13, CU-O23, CU-O27, CU-O28, CU-O29 |
| **KPIs** | Usuarios con rol, accesos no autorizados, tiempo de actividad del sistema, sesiones activas |

### Departamento 6: Datos / Analítica

| Elemento | Descripción |
|----------|-------------|
| **Responsable** | Auditor de Datos |
| **Función** | Ejecutar y validar pipelines ETL, monitorear calidad de datos, auditar trazabilidad del sistema, generar reportes de revenue y calidad |
| **Procesos** | Ejecución de pipeline ETL, validación de calidad, consulta de reportes, consulta de auditoría, análisis de mercados, consulta de historial de cambios |
| **Sistemas que usa** | Módulo ETL (Airflow), dashboard, reportes, calidad, auditoría, módulo partner (historial) |
| **CU asociados** | CU-O13, CU-O26, CU-O27, CU-O31, CU-O37 |
| **KPIs** | Registros procesados, registros rechazados, cobertura de auditoría, calidad del dataset, tiempo de ejecución ETL |

### Departamento 7: Operaciones de Infraestructura Hotelera

| Elemento | Descripción |
|----------|-------------|
| **Responsable** | Gerente de hotel / Housekeeping / Mantenimiento |
| **Función** | Gestionar el estado físico y operativo de las habitaciones: limpieza, rotación, mantenimiento preventivo y cargos adicionales |
| **Procesos** | Consulta de estado de habitaciones, asignación de limpieza, rotación post-checkout, mantenimiento programado, registro de cargos extras |
| **Sistemas que usa** | Módulo housekeeping (room_status, tareas), módulo maintenance (programación), módulo billing (cargos adicionales) |
| **CU asociados** | CU-O30, CU-O33 |
| **KPIs** | Tiempo de rotación de habitaciones, cumplimiento de limpieza, cumplimiento de mantenimiento, cargos adicionales por reserva, alertas operativas |

---

# 4. PAQUETES DEL SISTEMA

## 4.1 Mapa de Paquetes

El sistema HotelData se organiza en 11 paquetes funcionales que agrupan los módulos, colecciones y casos de uso relacionados.

| # | Paquete | Descripción | Módulo backend | Colecciones principales |
|---|---------|-------------|----------------|------------------------|
| 1 | **Autenticación y Seguridad** | Gestión de identidad, sesiones, roles y permisos de acceso | auth, admin (usuarios/roles) | users, user_sessions, user_activity_logs, roles, permissions, role_permissions |
| 2 | **Búsqueda y Experiencia Cliente** | Motor de búsqueda hotelera, filtros, comparación y detalle de propiedad | hotels | dim_hotels, hotels, locations, contacts, facilities, attractions |
| 3 | **Core de Reservas** | Ciclo de vida completo de la reserva: solicitud, confirmación, check-in, check-out, cancelación | reservations | booking_orders, booking_guests, booking_status_history, manual_reservations |
| 4 | **Gestión Hotelera (Partner Central)** | Administración de propiedades, habitaciones, inventario, tarifas, políticas, contenido e imágenes | partner (rooms, rates, content, policies, amenities, hotels) | room_types, hotel_rooms, room_inventory_calendar, rate_plans, hotel_rate_calendar, hotel_policies, hotel_content_pages, hotel_images, hotel_profile_changes |
| 5 | **Promociones y Revenue** | Campañas promocionales, cupones, descuentos y análisis de ingresos | revenue | promotion_campaigns, coupon_codes, rate_plans, hotel_rate_calendar |
| 6 | **Reseñas y Reputación** | Registro, moderación y respuesta de reseñas de huéspedes | reviews | reviews, fact_reviews |
| 7 | **Facturación y Pagos** | Generación de comprobantes, facturas y registro de pagos | billing | reservation_invoices, reservation_payments, fact_invoices, fact_payments |
| 8 | **Reportes y Analítica** | Dashboards ejecutivos, reportes de revenue, calidad de datos y análisis de mercado | revenue (reportes), dashboard, quality, audit | data_quality_reports, etl_executions, fact_hotel_reservations, dim_* |
| 9 | **Mapa y Geo-localización** | Visualización de destinos y hoteles en mapa mundial interactivo con Leaflet.js, selección de ubicación por coordenadas | map | destinations_enriched, hotel_locations_geo |
| 10 | **Housekeeping y Mantenimiento** | Gestión de estado de habitaciones, limpieza, rotación, mantenimiento preventivo, alertas operativas y cargos adicionales | housekeeping, maintenance | room_status_log, housekeeping_tasks, maintenance_schedule, maintenance_tasks, additional_charges |
| 11 | **Notificaciones y Comunicación** | Envío de notificaciones transaccionales (email, SMS, push) al huésped y alertas operativas internas al staff | notifications | notification_templates, notification_queue, notification_logs, notification_preferences |

## 4.2 Diagrama de Paquetes y Dependencias

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND ANGULAR (SPA)                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │   Auth   │ │  Search  │ │   Book   │ │Management│ │  Admin   │ │ Reports  ││
│  │   UI     │ │    UI    │ │    UI    │ │    UI    │ │    UI    │ │    UI    ││
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘│
└───────┼────────────┼────────────┼────────────┼────────────┼────────────┼───────┘
        │            │            │            │            │            │
        ▼            ▼            ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                                      │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ PAQUETE 1    │  │ PAQUETE 2    │  │ PAQUETE 3    │  │ PAQUETE 4    │   │
│  │ Auth/Seg     │  │ Busqueda     │  │ Reservas     │  │ Partner      │   │
│  │ ─────────    │  │ ─────────    │  │ ─────────    │  │ ─────────    │   │
│  │ auth/        │  │ hotels/      │  │ reservations/│  │ partner/     │   │
│  │ admin/       │  │              │  │              │  │   rooms/     │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │   rates/     │   │
│         │                │                  │          │   content/   │   │
│         │                │                  │          │   policies/  │   │
│         │                │                  │          └──────┬───────┘   │
│         │                │                  │                 │           │
│  ┌──────┴───────┐  ┌────┴───────┐  ┌───────┴──────┐  ┌──────┴───────┐   │
│  │ PAQUETE 5    │  │ PAQUETE 6  │  │ PAQUETE 7   │  │ PAQUETE 8   │   │
│  │ Revenue      │  │ Reseñas    │  │ Facturación │  │ Reportes    │   │
│  │ ─────────    │  │ ─────────  │  │ ─────────── │  │ ─────────   │   │
│  │ revenue/     │  │ reviews/   │  │ billing/    │  │ dashboard/  │   │
│  │ promotions/  │  │            │  │             │  │ quality/    │   │
│  └──────┬───────┘  └────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
└─────────┼────────────────┼────────────────┼────────────────┼────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             MONGODB (hoteldata_hub)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │  Auth    │ │  Hotels  │ │ Bookings │ │ Partner  │ │ Reviews  │ │  Facts   ││
│  │ users    │ │ dim_hotels││ booking_  │ │ room_    │ │ reviews  │ │ fact_    ││
│  │ sessions │ │ hotels   │ │ orders   │ │ types    │ │ fact_    │ │ hotel_   ││
│  │ roles    │ │ locations│ │ guests   │ │ inventory│ │ reviews  │ │ reserv.  ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. MATRIZ NIVEL → DEPARTAMENTO → PAQUETE → CASO DE USO

## 5.1 Matriz Completa de la Parte Operativa (CU-O01 a CU-O37) + Tácticos (T14-T17) + Estratégico (E09-E10)

La siguiente matriz relaciona los niveles organizacionales, departamentos funcionales, paquetes del sistema y casos de uso operativos de HotelData.

| Código CU | Nivel | Departamento | Paquete | Nombre del Caso de Uso | Actor Principal |
|-----------|-------|-------------|---------|----------------------|-----------------|
| CU-O01 | Operativo | Administración/Sistemas | Autenticación y Seguridad | Iniciar sesión con autenticación JWT y rol | Todos los usuarios |
| CU-O02 | Operativo | Comercial/Cliente | Búsqueda y Experiencia Cliente | Buscar hoteles | Cliente |
| CU-O03 | Operativo | Comercial/Cliente | Búsqueda y Experiencia Cliente | Filtrar y comparar hoteles | Cliente |
| CU-O04 | Operativo | Comercial/Cliente | Búsqueda y Experiencia Cliente | Ver detalle de hotel | Cliente |
| CU-O05 | Operativo | Comercial/Cliente | Core de Reservas | Solicitar reserva | Cliente |
| CU-O06 | Operativo | Comercial/Cliente | Core de Reservas | Consultar mis reservas | Cliente |
| CU-O07 | Operativo | Comercial/Cliente | Core de Reservas | Cancelar reserva según política | Cliente |
| CU-O08 | Operativo | Operaciones Hoteleras | Core de Reservas | Registrar reserva manual | Recepcionista |
| CU-O09 | Operativo | Operaciones Hoteleras | Core de Reservas | Consultar solicitudes de reserva | Gerente de hotel |
| CU-O10 | Operativo | Operaciones Hoteleras | Core de Reservas | Completar check-in | Recepcionista |
| CU-O11 | Operativo | Operaciones Hoteleras | Core de Reservas | Completar check-out | Recepcionista |
| CU-O12 | Operativo | Marketing Hotelero | Gestión Hotelera (Partner Central) | Editar nombre comercial del hotel | Marketing / Partner |
| CU-O13 | Operativo | Administración/Sistemas | Gestión Hotelera (Partner Central) | Consultar historial de cambios de propiedad | Auditor de Datos / Partner |
| CU-O14 | Operativo | Operaciones Hoteleras | Gestión Hotelera (Partner Central) | Crear tipo de habitación | Hotel partner |
| CU-O15 | Operativo | Operaciones Hoteleras | Gestión Hotelera (Partner Central) | Actualizar inventario por fecha | Gerente de hotel |
| CU-O16 | Operativo | Operaciones Hoteleras | Gestión Hotelera (Partner Central) | Registrar bloqueo de disponibilidad | Gerente de hotel |
| CU-O17 | Operativo | Revenue Management | Promociones y Revenue | Crear plan tarifario | Revenue manager |
| CU-O18 | Operativo | Revenue Management | Promociones y Revenue | Configurar tarifa por fecha | Revenue manager |
| CU-O19 | Operativo | Revenue Management | Promociones y Revenue | Crear promoción y cupón | Marketing / Revenue |
| CU-O20 | Operativo | Operaciones Hoteleras | Gestión Hotelera (Partner Central) | Editar política hotelera | Hotel partner |
| CU-O21 | Operativo | Marketing Hotelero | Gestión Hotelera (Partner Central) | Actualizar amenities, imágenes y contenido | Marketing hotelero |
| CU-O22 | Operativo | Marketing Hotelero | Reseñas y Reputación | Registrar reseña de estancia | Cliente |
| CU-O23 | Operativo | Marketing Hotelero | Reseñas y Reputación | Moderar y responder reseña | Marketing / Admin |
| CU-O24 | Operativo | Operaciones Hoteleras | Facturación y Pagos | Generar comprobante o factura de reserva | Sistema / Recepcionista |
| CU-O25 | Operativo | Operaciones Hoteleras | Facturación y Pagos | Registrar pago asociado a reserva | Recepcionista |
| CU-O26 | Operativo | Revenue Management | Reportes y Analítica | Consultar reportes de revenue y mercado | Gerente / Revenue |
| CU-O27 | Operativo | Datos/Analítica | Reportes y Analítica | Consultar reporte de calidad y registros rechazados | Auditor de Datos |
| CU-O28 | Operativo | Administración/Sistemas | Autenticación y Seguridad | Administrar cuenta, sesión y cierre seguro | Todos los usuarios |
| CU-O29 | Operativo | Administración/Sistemas | Autenticación y Seguridad | Cambiar contraseña y actualizar perfil de usuario | Todos los usuarios |
| CU-O30 | Operativo | Operaciones Hoteleras | Housekeeping y Mantenimiento | Gestionar disponibilidad y estado de habitaciones | Recepcionista / Gerente |
| CU-O31 | Operativo | Datos/Analítica | Mapa y Geo-localización | Gestionar geolocalización y metadata de contenido | Auditor de Datos / Marketing |
| CU-O32 | Operativo | Comercial/Cliente | Notificaciones y Comunicación | Gestionar notificaciones transaccionales al huésped | Sistema |
| CU-O33 | Operativo | Operaciones Hoteleras | Housekeeping y Mantenimiento | Gestionar alertas operativas internas al staff | Sistema / Recepcionista |
| CU-O34 | Operativo | Revenue Management | Promociones y Revenue | Gestionar campañas promocionales multicanal | Marketing / Revenue |
| CU-O35 | Operativo | Comercial/Cliente | Búsqueda y Experiencia Cliente | Atender cliente mediante asistente virtual (chatbot) | Cliente |
| CU-O36 | Operativo | Revenue Management | Promociones y Revenue | Gestionar up-selling y ancillaries durante la estancia | Recepcionista / Revenue |
| CU-O37 | Operativo | Marketing Hotelero | Mapa y Geo-localización | Gestionar contenidos multimedia con geolocalización | Marketing hotelero |
| CU-T14 | Táctico | Operaciones Hoteleras | Housekeeping y Mantenimiento | Gestionar rotación, limpieza y tareas de housekeeping | Gerente de hotel |
| CU-T15 | Táctico | Operaciones Hoteleras | Housekeeping y Mantenimiento | Programar mantenimiento preventivo y correctivo de habitaciones | Gerente de hotel |
| CU-T16 | Táctico | Administración/Sistemas | Notificaciones y Comunicación | Configurar canales y plantillas de notificación | Super Admin |
| CU-T17 | Táctico | Comercial/Cliente | Búsqueda y Experiencia Cliente | Configurar base de conocimiento del chatbot | Marketing / Super Admin |
| CU-E09 | Estratégico | Operaciones Hoteleras | Housekeeping y Mantenimiento | Monitorear eficiencia operativa del hotel | Gerente general / Super Admin |
| CU-E10 | Estratégico | Revenue Management | Promociones y Revenue | Gestionar ingresos por up-selling y ancillaries | Gerente general / Revenue |

## 5.2 Matriz Estratégica → Táctica → Operativa → Caso de Uso

| OE | OT | OO | CU Operativo |
|----|----|----|-------------|
| OE1: Penetrar mercados hoteleros digitales | OT1.1: Automatizar captación digital | OO1.1.1: Registrar eventos de búsqueda y reserva | CU-O02, CU-O03, CU-O04, CU-O05 |
| OE1 | OT1.1 | OO1.1.2: Medir conversión del embudo digital | CU-O26 |
| OE1 | OT1.1 | OO1.1.3: Gestionar campañas promocionales multicanal | CU-O34 |
| OE1 | OT1.1 | OO1.1.4: Atender consultas con chatbot IA | CU-O35 |
| OE1 | OT1.1 | OO1.1.5: Gestionar up-selling y ancillaries | CU-O36 |
| OE1 | OT1.2: Fortalecer reputación del huésped | OO1.2.1: Registrar reseñas de estancia | CU-O22, CU-O23 |
| OE1 | OT1.2 | OO1.2.2: Generar comprobantes/facturación y cargos adicionales | CU-O24, CU-O25 |
| OE1 | OT1.2 | OO1.2.3: Enviar notificaciones transaccionales | CU-O32 |
| OE2: Escalar comercialmente | OT2.1: Estandarizar servicios por API | OO2.1.1: Exponer endpoints JSON | (todos los CU) |
| OE2 | OT2.1 | OO2.1.2: Validar JWT y roles por endpoint | CU-O01, CU-O28 |
| OE2 | OT2.2: Integrar módulos comerciales | OO2.2.1: Administrar perfil comercial de hotel | CU-O12 |
| OE2 | OT2.2 | OO2.2.2: Conectar habitaciones, tarifas, disponibilidad | CU-O14, CU-O15, CU-O16, CU-O17, CU-O18, CU-O20 |
| OE3: Asegurar disponibilidad técnica | OT3.1: Mantener infraestructura portable | OO3.1.1: Ejecutar servicios con Docker | (infraestructura) |
| OE3 | OT3.1 | OO3.1.2: Monitorear servicios | (monitoreo) |
| OE3 | OT3.2: Automatizar gobierno de datos | OO3.2.1: Ejecutar pipeline ETL | CU-O27 |
| OE3 | OT3.2 | OO3.2.2: Registrar auditoría | CU-O13, CU-O28 |
| OE4: Consolidar inteligencia de negocio | OT4.1: Consolidar analítica global | OO4.1.1: Consultar dashboard ejecutivo | CU-O26 |
| OE4 | OT4.1 | OO4.1.2: Analizar mercados | CU-O26 |
| OE4 | OT4.2: Aplicar BI y ML | OO4.2.1: Proyectar demanda y revenue | CU-O26 |
| OE4 | OT4.2 | OO4.2.2: Detectar anomalías | CU-O27 |
| OE2 | OT2.3: Enriquecer catálogo geoespacial | OO2.3.1: Editar metadata de destinos | CU-O31 |
| OE2 | OT2.3 | OO2.3.2: Editar nombre visible de hotel | CU-O31 |
| OE2 | OT2.3 | OO2.3.3: Visualizar destinos en mapa interactivo | CU-O31 |
| OE2 | OT2.3 | OO2.3.4: Gestionar contenidos multimedia con geolocalización | CU-O37 |
| OE3 | OT3.3: Automatizar gestión de habitaciones | OO3.3.1: Consultar estado y disponibilidad de habitaciones | CU-O30 |
| OE3 | OT3.3 | OO3.3.2: Gestionar limpieza, rotación y housekeeping | CU-T14 |
| OE3 | OT3.3 | OO3.3.3: Programar mantenimiento preventivo y correctivo | CU-T15 |
| OE3 | OT3.3 | OO3.3.4: Registrar cargos adicionales (absorbido en facturación) | CU-O24 |
| OE3 | OT3.3 | OO3.3.5: Gestionar alertas operativas internas al staff | CU-O33 |
| OE1 | OT1.2 | (táctico T16) | CU-T16 |
| OE1 | OT1.1 | (táctico T17) | CU-T17 |
| OE1/OE4 | OT1.1/OT4.1 | (estratégico E10) | CU-E10 |
| OE5 | OT5.1: Monitorear eficiencia operativa | OO5.1.1: Monitorear eficiencia y up-selling | CU-E09, CU-E10 |

---

# 6. ESPECIFICACIÓN DETALLADA DE CASOS DE USO OPERATIVOS

## 6.1 Estructura de la Especificación

Cada caso de uso operativo se especifica con la siguiente estructura:

| Sección | Descripción |
|---------|-------------|
| **Código** | Identificador único del caso de uso |
| **Nombre** | Nombre descriptivo del caso de uso |
| **Objetivo** | Propósito del caso de uso en el negocio hotelero |
| **Actor Principal** | Usuario que ejecuta el caso de uso |
| **Actores Secundarios** | Otros sistemas o usuarios involucrados |
| **Disparador** | Evento que inicia el caso de uso |
| **Precondiciones** | Condiciones que deben cumplirse antes de ejecutar |
| **Flujo Principal** | Secuencia normal de pasos exitosos |
| **Flujos Alternos** | Variaciones del flujo principal (errores, excepciones) |
| **Reglas de Negocio** | Reglas del dominio hotelero que aplican |
| **Entradas** | Datos que recibe el sistema |
| **Salidas** | Resultados que produce el sistema |
| **Postcondiciones** | Estado del sistema después de ejecutar |
| **Restricciones** | Limitaciones técnicas o de negocio |
| **Colecciones MongoDB** | Colecciones involucradas |
| **Endpoints** | Rutas de API expuestas |
| **Código implementado** | Archivos fuente del módulo |

---

## 6.2 CU-O01: Iniciar Sesión con Autenticación JWT y Rol

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O01 |
| **Nombre** | Iniciar sesión con autenticación JWT y rol |
| **Objetivo** | Permitir que cualquier usuario registrado acceda al sistema mediante credenciales (email + contraseña), validando su identidad, verificando el estado de su cuenta y estableciendo una sesión segura con redirección según su rol |
| **Actor Principal** | Todos los usuarios del sistema (cliente, recepcionista, hotel partner, gerente, revenue manager, marketing, super admin, auditor de datos) |
| **Actores Secundarios** | Sistema (generación de token, registro de auditoría) |
| **Disparador** | El usuario accede a la página de login e ingresa sus credenciales |
| **Precondiciones** | 1. El usuario debe estar registrado en la colección `users` con `is_active = true`. 2. El usuario no debe tener una sesión activa previa (si la tiene, se invalidará automáticamente). 3. El sistema debe estar operativo con conexión a MongoDB. |
| **Flujo Principal** | **Paso 1:** El usuario navega a `GET /auth/login` y visualiza el formulario de inicio de sesión.<br>**Paso 2:** El usuario ingresa su email y contraseña en el formulario y hace clic en "Iniciar sesión".<br>**Paso 3:** El sistema recibe las credenciales vía `POST /auth/login` (formulario HTML) o `POST /api/auth/login` (JSON API).<br>**Paso 4:** El sistema busca el documento del usuario en la colección `users` usando el email proporcionado.<br>**Paso 5:** Si el usuario existe, el sistema verifica la contraseña usando `passlib[bcrypt].verify(password, user.password_hash)`.<br>**Paso 6:** Si la contraseña es correcta, el sistema verifica que `user.is_active == true`.<br>**Paso 7:** Si la cuenta está activa, el sistema genera un token de sesión de 48 bytes usando `secrets.token_urlsafe(48)`.<br>**Paso 8:** El sistema calcula el hash SHA-256 del token y almacena `{token_hash, user_id, role, created_at, expires_at: now + 8h}` en la colección `user_sessions`.<br>**Paso 9:** El sistema establece una cookie HTTP llamada `hoteldata_session` con el token plano, flags: `httponly, samesite=lax, max-age=28800`.<br>**Paso 10:** El sistema registra el evento en `user_activity_logs` con tipo "login", user_id, email, rol y timestamp.<br>**Paso 11:** El sistema redirige al usuario a su página de inicio según su rol (definido en `navigation.py`). |
| **Flujos Alternos** | **FA-01: Credenciales inválidas**<br>En el paso 5 o 6, si el email no existe o la contraseña no coincide, el sistema responde con "Credenciales inválidas" sin especificar cuál campo falló. No se establece cookie. Se registra el intento fallido en `user_activity_logs`.<br><br>**FA-02: Cuenta inactiva**<br>En el paso 6, si `user.is_active == false`, el sistema responde con "Cuenta desactivada. Contacte al administrador." No se establece cookie. Se registra el intento en activity logs.<br><br>**FA-03: Error interno del servidor**<br>Si ocurre un error no controlado (conexión a BD, excepción en hashing), el sistema responde HTTP 500 y registra el error en logs del servidor. |
| **Reglas de Negocio** | **RN-O01-01:** El mensaje de error para credenciales inválidas debe ser genérico: "Credenciales inválidas". No debe revelar si el email no existe o la contraseña es incorrecta (medida de seguridad contra enumeración de usuarios).<br>**RN-O01-02:** Una cuenta desactivada no puede iniciar sesión bajo ninguna circunstancia.<br>**RN-O01-03:** Cada usuario solo puede tener una sesión activa a la vez. Si el usuario ya tiene una sesión activa y hace login, la sesión anterior se invalida automáticamente.<br>**RN-O01-04:** La sesión expira después de 8 horas de inactividad. El TTL index de MongoDB elimina automáticamente los documentos expirados. |
| **Entradas** | `email`: string (formato email válido) — Correo electrónico del usuario.<br>`password`: string (mín. 8 caracteres) — Contraseña del usuario. |
| **Salidas** | **Caso exitoso:** Cookie `hoteldata_session` + redirección HTTP a la homepage del rol.<br>**Credenciales inválidas:** HTTP 200 (HTML) / HTTP 401 (JSON) + mensaje "Credenciales inválidas".<br>**Cuenta inactiva:** HTTP 200 (HTML) / HTTP 403 (JSON) + mensaje "Cuenta desactivada. Contacte al administrador."<br>**Error interno:** HTTP 500. |
| **Postcondiciones** | 1. Existe un documento en `user_sessions` con el hash del token, user_id, rol y fecha de expiración.<br>2. El navegador del usuario tiene una cookie httponly con el token de sesión.<br>3. Queda registrado en `user_activity_logs` un evento de login exitoso (o fallido).<br>4. Si existía una sesión previa del mismo usuario, queda invalidada. |
| **Restricciones** | 1. Las contraseñas se almacenan exclusivamente con bcrypt (passlib). Nunca en texto plano ni con hash reversible.<br>2. El token de sesión tiene exactamente 48 bytes generados con `secrets.token_urlsafe()`.<br>3. El hash almacenado en DB es SHA-256 del token. El token plano solo existe en la cookie del navegador.<br>4. La cookie tiene flag httponly (no accesible desde JavaScript) para mitigar XSS.<br>5. La cookie tiene flag samesite=lax para mitigar CSRF.<br>6. La sesión expira a las 8 horas configuradas en `settings.SESSION_TTL_HOURS`. |
| **Colecciones MongoDB** | `users` (lectura: email, password_hash, is_active, primary_role)<br>`user_sessions` (escritura: token_hash, user_id, role, created_at, expires_at)<br>`user_activity_logs` (escritura: tipo, user_id, email, rol, timestamp, éxito/fallo) |
| **Endpoints** | `GET /auth/login` — Formulario HTML de login.<br>`POST /auth/login` — Procesa login desde formulario HTML.<br>`POST /api/auth/login` — Login vía API JSON.<br>`GET /api/auth/me` — Consulta sesión actual. |
| **Código implementado** | `server/src/app/modules/auth/routes.py` — Rutas de login.<br>`server/src/app/security/session.py` — `create_session()`, `verify_password()`.<br>`server/src/app/security/dependencies.py` — `require_login()`, `get_current_user()`.<br>`server/src/app/security/navigation.py` — Redirección por rol. |

---

## 6.3 CU-O02: Buscar Hoteles

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O02 |
| **Nombre** | Buscar hoteles |
| **Objetivo** | Permitir que el cliente busque hoteles disponibles ingresando destino, fechas y número de huéspedes, obteniendo una lista de propiedades con precios, ratings e imágenes |
| **Actor Principal** | Cliente / Viajero |
| **Actores Secundarios** | Sistema (consulta a MongoDB, cálculo de disponibilidad) |
| **Disparador** | El cliente accede a la página de búsqueda e ingresa los parámetros de su viaje |
| **Precondiciones** | 1. El sistema debe tener datos de hoteles cargados en `dim_hotels` y colecciones maestras.<br>2. Los hoteles deben tener tipos de habitación configurados en `room_types`.<br>3. Los hoteles deben tener inventario disponible en `room_inventory_calendar`. |
| **Flujo Principal** | **Paso 1:** El cliente navega a la página de búsqueda (`GET /hotels/search`).<br>**Paso 2:** El cliente ingresa el destino (ciudad o nombre), fechas de entrada y salida, número de adultos, niños y habitaciones.<br>**Paso 3:** El sistema recibe los parámetros y consulta `dim_hotels` filtrando por destino coincidente.<br>**Paso 4:** El sistema cruza los resultados con `room_inventory_calendar` para verificar disponibilidad en las fechas solicitadas.<br>**Paso 5:** Para cada hotel con disponibilidad, el sistema obtiene el precio mínimo desde `hotel_rate_calendar`.<br>**Paso 6:** El sistema devuelve una lista JSON (o HTML renderizada) con: prop_id, nombre, precio mínimo, rating, imagen principal, ubicación.<br>**Paso 7:** El cliente visualiza los resultados y puede interactuar (filtrar, ver detalle, comparar). |
| **Flujos Alternos** | **FA-01: Sin resultados**<br>Si no hay hoteles que coincidan con el destino o fechas, el sistema muestra un mensaje "No se encontraron hoteles para los criterios seleccionados" y sugiere modificar fechas o destino.<br><br>**FA-02: Destino parcial**<br>Si el destino no coincide exactamente, el sistema busca coincidencias parciales en el nombre del hotel o ciudad cercana. |
| **Reglas de Negocio** | **RN-O02-01:** Solo se muestran hoteles con al menos un tipo de habitación disponible en todas las noches solicitadas.<br>**RN-O02-02:** El precio mostrado es el precio mínimo por noche entre todos los tipos de habitación disponibles.<br>**RN-O02-03:** Los resultados se ordenan por precio ascendente por defecto. |
| **Entradas** | `destino`: string — Ciudad o nombre del destino.<br>`check_in`: date — Fecha de entrada.<br>`check_out`: date — Fecha de salida.<br>`adultos`: int (1-10) — Número de adultos.<br>`ninos`: int (0-10) — Número de niños.<br>`habitaciones`: int (1-5) — Número de habitaciones. |
| **Salidas** | Lista de hoteles con: `prop_id`, `hotel_name`, `precio_minimo`, `rating`, `review_score`, `imagen_url`, `direccion`, `destino`. |
| **Postcondiciones** | El cliente visualiza una lista de hoteles disponibles. No se modifica ningún dato en la base de datos. |
| **Restricciones** | 1. La búsqueda usa datos de `dim_hotels` (enriquecidos) más colecciones maestras (`hotels`, `locations`).<br>2. No se realiza búsqueda por coordenadas geográficas ni mapa interactivo. |
| **Colecciones MongoDB** | `dim_hotels` (lectura), `hotels` (lectura), `locations` (lectura), `room_inventory_calendar` (lectura), `hotel_rate_calendar` (lectura) |
| **Endpoints** | `GET /hotels/search` — Página de búsqueda HTML.<br>`GET /api/hotels/search` — API de búsqueda JSON. |
| **Código implementado** | `server/src/app/modules/hotels/` — Rutas y servicios de búsqueda. |

---

## 6.4 CU-O03: Filtrar y Comparar Hoteles

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O03 |
| **Nombre** | Filtrar y comparar hoteles |
| **Objetivo** | Permitir que el cliente refine los resultados de búsqueda mediante filtros (precio, rating, amenities) y compare hasta 3 hoteles lado a lado para tomar una decisión informada |
| **Actor Principal** | Cliente / Viajero |
| **Actores Secundarios** | Sistema |
| **Disparador** | El cliente ha realizado una búsqueda y desea refinar los resultados o comparar opciones |
| **Precondiciones** | 1. El cliente debe haber ejecutado una búsqueda (CU-O02) con resultados.<br>2. Debe haber al menos 2 hoteles en los resultados para poder comparar. |
| **Flujo Principal** | **Paso 1:** El cliente visualiza los resultados de búsqueda.<br>**Paso 2:** El cliente aplica filtros: rango de precio mínimo y máximo, calificación mínima (1-5 estrellas), amenities requeridas (WiFi, piscina, desayuno).<br>**Paso 3:** El sistema actualiza la lista de resultados aplicando los filtros seleccionados.<br>**Paso 4:** El cliente selecciona 2 o 3 hoteles y hace clic en "Comparar".<br>**Paso 5:** El sistema navega a `GET /hotels/compare?ids=prop1,prop2,prop3`.<br>**Paso 6:** El sistema muestra una vista lado a lado con: nombre, imágenes, precio, rating, amenities, políticas, descripción.<br>**Paso 7:** El cliente analiza la comparación y decide si ver detalle de uno o volver a resultados. |
| **Flujos Alternos** | **FA-01: Filtro sin resultados**<br>Si después de aplicar filtros no quedan hoteles, el sistema muestra "Ningún hotel coincide con los filtros seleccionados" y permite limpiar filtros.<br><br>**FA-02: Comparación con 1 hotel**<br>Si el cliente selecciona solo 1 hotel para comparar, el sistema redirige directamente al detalle del hotel (CU-O04). |
| **Reglas de Negocio** | **RN-O03-01:** Los filtros de precio y rating se aplican sobre los datos de `dim_hotels`.<br>**RN-O03-02:** La comparación muestra máximo 3 hoteles simultáneamente.<br>**RN-O03-03:** Los amenities se obtienen desde `hotel_content_pages` y `hotel_quality`. |
| **Entradas** | `precio_min`: float — Precio mínimo por noche.<br>`precio_max`: float — Precio máximo por noche.<br>`rating_min`: int (1-5) — Calificación mínima.<br>`amenities[]`: string[] — Lista de amenities requeridos.<br>`compare_ids[]`: string[] — IDs de hoteles a comparar. |
| **Salidas** | Lista filtrada de hoteles (misma estructura que CU-O02).<br>Vista comparativa lado a lado con datos detallados de hasta 3 hoteles. |
| **Postcondiciones** | El cliente visualiza resultados filtrados o comparativa. No se modifica la base de datos. |
| **Restricciones** | 1. Los filtros se aplican en el frontend y backend (doble validación).<br>2. La comparación es solo visual — no afecta disponibilidad ni precios. |
| **Colecciones MongoDB** | `dim_hotels`, `hotel_content_pages`, `hotel_images`, `hotel_quality` |
| **Endpoints** | `GET /api/hotels/search?precio_min=X&precio_max=Y&rating_min=Z`<br>`GET /hotels/compare?ids=id1,id2,id3` |
| **Código implementado** | `frontend/src/app/features/hotel-search/` — FilterSidebar, HotelCard.<br>`server/src/app/modules/hotels/` — Rutas de búsqueda y comparación. |

---

## 6.5 CU-O04: Ver Detalle de Hotel

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O04 |
| **Nombre** | Ver detalle de hotel |
| **Objetivo** | Mostrar al cliente la información completa de una propiedad hotelera: galería de imágenes, descripción, amenities, políticas, tarifas por tipo de habitación con disponibilidad, reseñas de huéspedes y ubicación |
| **Actor Principal** | Cliente / Viajero |
| **Actores Secundarios** | Sistema |
| **Disparador** | El cliente hace clic en un hotel desde los resultados de búsqueda o comparación |
| **Precondiciones** | 1. El hotel debe existir en `dim_hotels` y tener datos cargados.<br>2. El hotel debe tener al menos un tipo de habitación con tarifa configurada. |
| **Flujo Principal** | **Paso 1:** El cliente navega a `GET /hotels/{prop_id}`.<br>**Paso 2:** El sistema consulta `dim_hotels` para obtener datos básicos del hotel.<br>**Paso 3:** El sistema consulta `hotel_images` para obtener la galería de imágenes.<br>**Paso 4:** El sistema consulta `hotel_content_pages` para descripción, highlights, amenities.<br>**Paso 5:** El sistema consulta `hotel_policies` para políticas de cancelación, check-in/out, mascotas, niños.<br>**Paso 6:** El sistema consulta `room_types` + `hotel_rate_calendar` para mostrar tarifas por tipo de habitación y fechas.<br>**Paso 7:** El sistema consulta `reviews` para mostrar reseñas recientes con puntuación promedio.<br>**Paso 8:** El sistema renderiza la página de detalle con toda la información.<br>**Paso 9:** El cliente visualiza el detalle y puede proceder a reservar (CU-O05). |
| **Flujos Alternos** | **FA-01: Hotel sin imágenes**<br>Si el hotel no tiene imágenes cargadas, se muestra una imagen por defecto.<br><br>**FA-02: Hotel sin reseñas**<br>Si no hay reseñas, se muestra "Aún no hay reseñas para este hotel".<br><br>**FA-03: Hotel sin tarifas configuradas**<br>Si el hotel no tiene tarifas para las fechas consultadas, se muestra "Consultar disponibilidad". |
| **Reglas de Negocio** | **RN-O04-01:** Las tarifas mostradas son por noche e incluyen impuestos si están configurados.<br>**RN-O04-02:** Las reseñas se muestran ordenadas por fecha descendente, máximo 10 inicialmente.<br>**RN-O04-03:** Las políticas de cancelación se muestran según lo configurado en `hotel_policies`. |
| **Entradas** | `prop_id`: string — Identificador único de la propiedad hotelera. |
| **Salidas** | Página de detalle con: nombre, descripción, galería de imágenes, rating, dirección, amenities, políticas, tarifas por tipo de habitación, reseñas, mapa de ubicación. |
| **Postcondiciones** | El cliente visualiza la información completa del hotel. No se modifica la base de datos. |
| **Restricciones** | 1. Las imágenes se sirven desde MongoDB (no CDN externo).<br>2. Las tarifas mostradas son las configuradas por el revenue manager. |
| **Colecciones MongoDB** | `dim_hotels`, `hotel_content_pages`, `hotel_images`, `hotel_policies`, `room_types`, `hotel_rate_calendar`, `reviews`, `fact_reviews` |
| **Endpoints** | `GET /hotels/{prop_id}` — Página de detalle HTML.<br>`GET /api/hotels/{prop_id}` — API de detalle JSON. |
| **Código implementado** | `server/src/app/modules/hotels/` — Rutas de detalle.<br>`frontend/src/app/features/hotel-detail/` — HotelDetailPage. |

---

## 6.6 CU-O05: Solicitar Reserva

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O05 |
| **Nombre** | Solicitar reserva |
| **Objetivo** | Permitir que el cliente solicite una reserva seleccionando tipo de habitación, fechas, datos de huéspedes, creando una orden de reserva en estado "pending" con trazabilidad completa |
| **Actor Principal** | Cliente / Viajero |
| **Actores Secundarios** | Sistema (creación de booking_order, booking_guests, booking_status_history) |
| **Disparador** | El cliente, desde la página de detalle del hotel, hace clic en "Reservar" para un tipo de habitación y fechas específicas |
| **Precondiciones** | 1. El cliente debe estar autenticado con sesión activa.<br>2. El tipo de habitación seleccionado debe tener disponibilidad en las fechas solicitadas.<br>3. El hotel debe tener tarifas configuradas para las fechas solicitadas. |
| **Flujo Principal** | **Paso 1:** El cliente selecciona tipo de habitación, fechas y cantidad desde la página de detalle del hotel.<br>**Paso 2:** El sistema muestra un resumen de la reserva con: hotel, tipo habitación, fechas, total estimado y políticas de cancelación.<br>**Paso 3:** El cliente ingresa los datos de los huéspedes (nombre completo, email, teléfono) en el formulario de reserva.<br>**Paso 4:** El cliente confirma la reserva haciendo clic en "Solicitar reserva".<br>**Paso 5:** El sistema recibe los datos vía `POST /api/reservations` (o `POST /reservations/new` desde formulario HTML).<br>**Paso 6:** El sistema valida que el tipo de habitación tenga disponibilidad en todas las noches solicitadas consultando `room_inventory_calendar`.<br>**Paso 7:** El sistema calcula el total: suma de tarifas por noche desde `hotel_rate_calendar`.<br>**Paso 8:** El sistema crea un documento en `booking_orders` con estado "pending", incluyendo: prop_id, room_type_id, check_in, check_out, adultos, niños, total, user_id.<br>**Paso 9:** El sistema crea documentos en `booking_guests` para cada huésped asociado a la reserva.<br>**Paso 10:** El sistema registra el cambio de estado en `booking_status_history` con estado "created" y timestamp.<br>**Paso 11:** El sistema responde con confirmación y el ID de la reserva. |
| **Flujos Alternos** | **FA-01: Sin disponibilidad**<br>En el paso 6, si no hay suficiente inventario en alguna de las noches, el sistema muestra "La habitación seleccionada no está disponible para todas las fechas solicitadas" y sugiere fechas alternativas.<br><br>**FA-02: Usuario no autenticado**<br>Si el usuario no ha iniciado sesión, el sistema redirige al login (CU-O01) y luego regresa al flujo de reserva.<br><br>**FA-03: Error de validación**<br>Si los datos del huésped son inválidos (email mal formado, campos obligatorios vacíos), el sistema muestra los errores de validación y no crea la reserva. |
| **Reglas de Negocio** | **RN-O05-01:** Una reserva se crea siempre en estado "pending". Requiere confirmación del gerente del hotel para pasar a "confirmed".<br>**RN-O05-02:** El inventario no se descuenta hasta que la reserva pasa a estado "confirmed".<br>**RN-O05-03:** El precio total se calcula al momento de la solicitud y no varía después.<br>**RN-O05-04:** Una reserva debe tener al menos un huésped asociado. |
| **Entradas** | `prop_id`: string — ID del hotel.<br>`room_type_id`: string — ID del tipo de habitación.<br>`check_in`: date — Fecha de entrada.<br>`check_out`: date — Fecha de salida.<br>`adultos`: int — Número de adultos.<br>`ninos`: int — Número de niños.<br>`guests[]`: array — Lista de huéspedes con nombre, email, teléfono. |
| **Salidas** | **Caso exitoso:** JSON con `booking_id`, estado "pending", total, mensaje de confirmación.<br>**Sin disponibilidad:** Mensaje de error + sugerencia de fechas.<br>**Error de validación:** Lista de errores campo por campo. |
| **Postcondiciones** | 1. Existe un documento en `booking_orders` con estado "pending".<br>2. Existen documentos en `booking_guests` asociados al booking_id.<br>3. Existe un registro en `booking_status_history` con estado inicial "created".<br>4. El cliente puede consultar la reserva en "Mis reservas" (CU-O06). |
| **Restricciones** | 1. No se realiza cobro en línea al momento de la reserva (solo facturación post-estancia).<br>2. check_out debe ser posterior a check_in.<br>3. No se puede reservar con más de 365 días de anticipación. |
| **Colecciones MongoDB** | `booking_orders` (escritura), `booking_guests` (escritura), `booking_status_history` (escritura), `room_inventory_calendar` (lectura), `hotel_rate_calendar` (lectura) |
| **Endpoints** | `GET /reservations/new` — Formulario de nueva reserva HTML.<br>`POST /reservations/new` — Crear reserva desde formulario HTML.<br>`POST /api/reservations` — Crear reserva vía API JSON. |
| **Código implementado** | `server/src/app/modules/reservations/` — Rutas y servicios (`lifecycle.py`, `validation.py`).<br>`frontend/src/app/features/reservations/` — ReservationNewPage. |

---

## 6.7 CU-O06: Consultar Mis Reservas

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O06 |
| **Nombre** | Consultar mis reservas |
| **Objetivo** | Permitir que el cliente (y el gerente de hotel) consulten el listado de reservas con estado, fechas, hotel, monto y acciones disponibles |
| **Actor Principal** | Cliente / Viajero (consulta sus propias reservas). Gerente de hotel (consulta reservas de su propiedad) |
| **Actores Secundarios** | Sistema |
| **Disparador** | El cliente navega a "Mis reservas" desde el menú de usuario. El gerente navega a "Reservas" desde el panel de gestión |
| **Precondiciones** | 1. El usuario debe estar autenticado.<br>2. Deben existir reservas asociadas al usuario (cliente) o a su propiedad (gerente). |
| **Flujo Principal** | **Paso 1:** El usuario navega a la sección de reservas (`GET /reservations` para cliente, `GET /management/reservations` para gerente).<br>**Paso 2:** El sistema identifica el rol del usuario desde la sesión.<br>**Paso 3:** Si es cliente, el sistema consulta `booking_orders` filtrando por `user_id` del usuario autenticado.<br>**Paso 4:** Si es gerente, el sistema consulta `booking_orders` filtrando por `prop_id` de sus propiedades asignadas.<br>**Paso 5:** El sistema obtiene datos del hotel desde `dim_hotels` para cada reserva.<br>**Paso 6:** El sistema devuelve una lista con: booking_id, hotel, fechas, tipo habitación, estado, monto total, fecha de creación.<br>**Paso 7:** Cada reserva muestra acciones según su estado: "Ver detalle", "Cancelar" (si está pending/confirmed), "Completar check-in" (si es confirmed y la fecha es hoy, solo gerente). |
| **Flujos Alternos** | **FA-01: Sin reservas**<br>Si el usuario no tiene reservas, se muestra "No tienes reservas registradas" con un enlace para buscar hoteles.<br><br>**FA-02: Reserva no encontrada**<br>Si se accede directamente a una reserva que no pertenece al usuario, el sistema responde HTTP 403. |
| **Reglas de Negocio** | **RN-O06-01:** Un cliente solo puede ver sus propias reservas (filtro por user_id).<br>**RN-O06-02:** Un gerente puede ver todas las reservas de sus propiedades asignadas.<br>**RN-O06-03:** Las reservas se muestran ordenadas por fecha de creación descendente (más recientes primero). |
| **Entradas** | Sesión del usuario autenticado (cookie `hoteldata_session`). |
| **Salidas** | Lista de reservas con: booking_id, hotel_name, check_in, check_out, room_type, estado, total, created_at, acciones disponibles. |
| **Postcondiciones** | El usuario visualiza su listado de reservas. No se modifica la base de datos. |
| **Restricciones** | 1. El listado está paginado (20 items por página).<br>2. Las reservas canceladas se muestran con indicador visual (tachado o en gris). |
| **Colecciones MongoDB** | `booking_orders` (lectura), `booking_guests` (lectura), `booking_status_history` (lectura), `dim_hotels` (lectura) |
| **Endpoints** | `GET /reservations` — Listado HTML para cliente.<br>`GET /reservations/{booking_id}` — Detalle de reserva HTML.<br>`GET /api/reservations` — Listado API JSON.<br>`GET /api/reservations/{booking_id}` — Detalle API JSON. |
| **Código implementado** | `server/src/app/modules/reservations/` — Rutas y servicios (`queries.py`).<br>`frontend/src/app/features/reservations/` — ReservationsListPage, ReservationDetailPage. |

---

## 6.8 CU-O07: Cancelar Reserva Según Política

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O07 |
| **Nombre** | Cancelar reserva según política |
| **Objetivo** | Permitir que el cliente cancele una reserva existente validando las políticas de cancelación del hotel, registrando el cambio de estado con trazabilidad |
| **Actor Principal** | Cliente / Viajero (cancela su propia reserva). Gerente de hotel (cancela cualquier reserva de su propiedad) |
| **Actores Secundarios** | Sistema (validación de política, liberación de inventario) |
| **Disparador** | El usuario hace clic en "Cancelar reserva" desde el detalle o listado de reservas |
| **Precondiciones** | 1. La reserva debe existir en `booking_orders` con estado "pending" o "confirmed".<br>2. El usuario debe ser el dueño de la reserva (cliente) o gerente del hotel.<br>3. La reserva no debe haber sido cancelada previamente ni estar en estado "checked_out". |
| **Flujo Principal** | **Paso 1:** El usuario navega al detalle de la reserva y hace clic en "Cancelar reserva".<br>**Paso 2:** El sistema muestra un diálogo de confirmación con: hotel, fechas, monto, política de cancelación aplicable y posibles cargos.<br>**Paso 3:** El usuario confirma la cancelación.<br>**Paso 4:** El sistema envía la solicitud a `POST /api/reservations/{booking_id}/cancel` (o al formulario HTML equivalente).<br>**Paso 5:** El sistema consulta `hotel_policies` para determinar la política de cancelación del hotel (días de anticipación, porcentaje de cargo).<br>**Paso 6:** El sistema actualiza el estado de `booking_orders` a "cancelled".<br>**Paso 7:** El sistema registra el cambio en `booking_status_history` con estado anterior, estado nuevo ("cancelled"), usuario y timestamp.<br>**Paso 8:** Si la reserva estaba en estado "confirmed", el sistema libera el inventario en `room_inventory_calendar` para las fechas de la reserva.<br>**Paso 9:** El sistema registra la acción en `user_activity_logs`.<br>**Paso 10:** El sistema muestra mensaje de confirmación "Reserva cancelada exitosamente". |
| **Flujos Alternos** | **FA-01: Reserva no cancelable**<br>Si la política del hotel no permite cancelación (non-refundable) o la fecha de check-in es el mismo día, el sistema muestra "Esta reserva no puede ser cancelada según la política del hotel" y oculta el botón de cancelar.<br><br>**FA-02: Reserva ya cancelada**<br>Si la reserva ya fue cancelada previamente, el sistema muestra "Esta reserva ya fue cancelada" y no permite la acción.<br><br>**FA-03: Reserva en check-in/out**<br>Si la reserva está en estado "checked_in" o "checked_out", no se permite cancelación. Solo el gerente puede forzar una cancelación excepcional. |
| **Reglas de Negocio** | **RN-O07-01:** Una reserva solo puede cancelarse si está en estado "pending" o "confirmed".<br>**RN-O07-02:** La política de cancelación se obtiene del hotel (`hotel_policies.cancellation_policy`) y puede variar por hotel.<br>**RN-O07-03:** Si la reserva estaba "confirmed" y se cancela, el inventario debe liberarse automáticamente.<br>**RN-O07-04:** La cancelación queda registrada permanentemente en `booking_status_history` como evidencia de trazabilidad. |
| **Entradas** | `booking_id`: string — ID de la reserva a cancelar.<br>Razón (opcional): string — Motivo de la cancelación. |
| **Salidas** | **Caso exitoso:** Mensaje "Reserva cancelada exitosamente" + redirección al listado.<br>**No cancelable:** Mensaje "Esta reserva no puede ser cancelada según la política del hotel".<br>**Error:** Mensaje descriptivo del error. |
| **Postcondiciones** | 1. `booking_orders.estado = "cancelled"`.<br>2. `booking_status_history` tiene un nuevo registro con estado anterior → "cancelled".<br>3. Si estaba "confirmed", el inventario se liberó en `room_inventory_calendar`.<br>4. Queda registrado en `user_activity_logs`. |
| **Restricciones** | 1. No se procesan reembolsos (pagos simulados, sin integración bancaria real).<br>2. Una vez cancelada, la reserva no puede reactivarse. |
| **Colecciones MongoDB** | `booking_orders` (actualización), `booking_status_history` (escritura), `room_inventory_calendar` (actualización), `hotel_policies` (lectura), `user_activity_logs` (escritura) |
| **Endpoints** | `POST /reservations/{booking_id}/cancel` — Cancelar desde formulario HTML.<br>`POST /api/reservations/{booking_id}/cancel` — Cancelar vía API JSON. |
| **Código implementado** | `server/src/app/modules/reservations/` — Rutas de cancelación + servicios (`lifecycle.py`).<br>`frontend/src/app/features/reservations/` — ReservationDetailPage. |

---

## 6.9 CU-O08: Registrar Reserva Manual

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O08 |
| **Nombre** | Registrar reserva manual |
| **Objetivo** | Permitir que el recepcionista cree una reserva manualmente desde el panel de gestión para reservas telefónicas, walk-in (huésped sin reserva previa) o cortesía, creando la reserva directamente en estado "confirmed" |
| **Actor Principal** | Recepcionista |
| **Actores Secundarios** | Sistema, Hotel partner |
| **Disparador** | El recepcionista recibe una solicitud de reserva por teléfono o un huésped llega sin reserva (walk-in) |
| **Precondiciones** | 1. El recepcionista debe estar autenticado con rol `recepcionista` o `hotel_partner`.<br>2. El hotel debe tener tipos de habitación configurados en `room_types`.<br>3. Debe haber disponibilidad en `room_inventory_calendar` para las fechas solicitadas. |
| **Flujo Principal** | **Paso 1:** El recepcionista navega a `GET /partner/manual-reservations/new` desde el panel de gestión.<br>**Paso 2:** El sistema muestra un formulario con: selector de tipo de habitación, fechas, datos del huésped, tarifa aplicable.<br>**Paso 3:** El recepcionista selecciona tipo de habitación, ingresa fechas, datos del huésped y confirma.<br>**Paso 4:** El sistema crea `booking_orders` directamente con estado "confirmed" (saltando el estado "pending").<br>**Paso 5:** El sistema descuenta el inventario en `room_inventory_calendar` para las fechas reservadas.<br>**Paso 6:** El sistema crea `booking_guests` con los datos del huésped.<br>**Paso 7:** El sistema registra en `booking_status_history`: "manual_created" → "confirmed".<br>**Paso 8:** El sistema registra la acción en `user_activity_logs` con tipo "manual_reservation".<br>**Paso 9:** El sistema muestra confirmación con el ID de la reserva creada. |
| **Flujos Alternos** | **FA-01: Sin disponibilidad**<br>Si no hay inventario disponible, el sistema muestra las fechas alternativas con disponibilidad parcial.<br><br>**FA-02: Huésped ya registrado**<br>Si el email del huésped ya existe en `users`, el sistema precarga sus datos. |
| **Reglas de Negocio** | **RN-O08-01:** La reserva manual se crea en estado "confirmed" directamente, no "pending".<br>**RN-O08-02:** El inventario se descuenta inmediatamente al crear la reserva manual.<br>**RN-O08-03:** Las reservas manuales quedan registradas en la colección `manual_reservations` para trazabilidad. |
| **Entradas** | `prop_id`, `room_type_id`, `check_in`, `check_out`, `adultos`, `ninos`, `guest_name`, `guest_email`, `guest_phone`, `tarifa_aplicada` |
| **Salidas** | Confirmación con `booking_id` y estado "confirmed". |
| **Postcondiciones** | 1. `booking_orders` tiene un nuevo documento en estado "confirmed".<br>2. `room_inventory_calendar` refleja la ocupación.<br>3. `booking_guests` tiene los datos del huésped.<br>4. `manual_reservations` tiene el registro de origen manual. |
| **Restricciones** | Solo disponible para roles `recepcionista` y `hotel_partner`. |
| **Colecciones MongoDB** | `booking_orders` (escritura), `booking_guests` (escritura), `booking_status_history` (escritura), `room_inventory_calendar` (actualización), `manual_reservations` (escritura) |
| **Endpoints** | `GET /partner/manual-reservations/new` — Formulario HTML.<br>`POST /partner/manual-reservations/new` — Crear reserva manual. |
| **Código implementado** | `server/src/app/modules/reservations/` — Rutas de reserva manual + `lifecycle.py`. |

---

## 6.10 CU-O09: Consultar Solicitudes de Reserva

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O09 |
| **Nombre** | Consultar solicitudes de reserva |
| **Objetivo** | Permitir que el gerente de hotel consulte todas las solicitudes de reserva (en estado "pending") para su propiedad, y pueda confirmarlas o rechazarlas |
| **Actor Principal** | Gerente de hotel |
| **Actores Secundarios** | Sistema |
| **Disparador** | El gerente accede al panel de gestión y selecciona "Solicitudes de reserva" |
| **Precondiciones** | 1. El gerente debe estar autenticado con rol `gerente_hotel`.<br>2. Deben existir reservas en estado "pending" para sus propiedades. |
| **Flujo Principal** | **Paso 1:** El gerente navega a `GET /api/management/check-ins` o al panel de solicitudes.<br>**Paso 2:** El sistema consulta `booking_orders` con estado "pending" filtrado por `prop_id` del gerente.<br>**Paso 3:** El sistema muestra lista de solicitudes con: booking_id, nombre del huésped, fechas, tipo habitación, total, tiempo desde la solicitud.<br>**Paso 4:** El gerente puede hacer clic en una solicitud para ver detalle completo.<br>**Paso 5:** El gerente puede confirmar la reserva (cambia a "confirmed" y descuenta inventario) o rechazarla (cambia a "cancelled" con razón). |
| **Flujos Alternos** | **FA-01: Sin solicitudes pendientes**<br>El sistema muestra "No hay solicitudes de reserva pendientes".<br><br>**FA-02: Confirmar con conflicto de inventario**<br>Si entre la solicitud y la confirmación otro proceso ocupó el inventario, el sistema alerta al gerente. |
| **Reglas de Negocio** | **RN-O09-01:** Una solicitud en "pending" que no se confirma en 24 horas se cancela automáticamente.<br>**RN-O09-02:** Solo el gerente del hotel puede confirmar o rechazar solicitudes de su propiedad. |
| **Entradas** | Sesión del gerente autenticado. |
| **Salidas** | Lista de solicitudes pendientes con datos del huésped y resumen de la reserva. |
| **Postcondiciones** | Depende de la acción del gerente (confirmar o rechazar). |
| **Colecciones MongoDB** | `booking_orders`, `booking_guests`, `dim_hotels` |
| **Endpoints** | `GET /api/reservations?estado=pending` — Solicitudes pendientes API. |
| **Código implementado** | `server/src/app/modules/reservations/` — Queries + lifecycle. |

---

## 6.11 CU-O10: Completar Check-In

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O10 |
| **Nombre** | Completar check-in |
| **Objetivo** | Permitir que el recepcionista registre la llegada del huésped, cambiando el estado de la reserva de "confirmed" a "checked_in" y marcando la habitación como ocupada |
| **Actor Principal** | Recepcionista |
| **Actores Secundarios** | Sistema |
| **Disparador** | El huésped llega al hotel y el recepcionista procede a realizar el check-in |
| **Precondiciones** | 1. La reserva debe existir y estar en estado "confirmed".<br>2. La fecha de check-in debe ser igual o anterior a la fecha actual.<br>3. El recepcionista debe tener permisos sobre la propiedad. |
| **Flujo Principal** | **Paso 1:** El recepcionista navega a `GET /api/management/check-ins` para ver la lista de check-ins del día.<br>**Paso 2:** El sistema consulta `booking_orders` con estado "confirmed" y `check_in` = fecha actual, filtrado por `prop_id` del recepcionista.<br>**Paso 3:** El recepcionista encuentra la reserva del huésped y hace clic en "Completar check-in".<br>**Paso 4:** El sistema muestra los datos de la reserva y solicita confirmación.<br>**Paso 5:** El recepcionista confirma el check-in.<br>**Paso 6:** El sistema actualiza `booking_orders.estado` a "checked_in".<br>**Paso 7:** El sistema registra en `booking_status_history`: "confirmed" → "checked_in".<br>**Paso 8:** El sistema actualiza `room_inventory_calendar` marcando la habitación como ocupada.<br>**Paso 9:** El sistema registra la acción en `user_activity_logs`.<br>**Paso 10:** El sistema muestra confirmación. |
| **Flujos Alternos** | **FA-01: Huésped no se presenta (no-show)**<br>Si el huésped no llega, el recepcionista puede marcar la reserva como "no_show" después de las 24 horas del check-in.<br><br>**FA-02: Check-in anticipado**<br>Si el huésped llega antes de la fecha de check-in, el recepcionista puede modificar la fecha si hay disponibilidad. |
| **Reglas de Negocio** | **RN-O10-01:** Solo reservas en estado "confirmed" pueden hacer check-in.<br>**RN-O10-02:** El check-in solo puede completarse en la fecha de check-in o posterior.<br>**RN-O10-03:** Una vez en "checked_in", la reserva no puede cancelarse (solo por excepción del gerente). |
| **Entradas** | `booking_id`: string — ID de la reserva. |
| **Salidas** | Confirmación de check-in exitoso + actualización de estado. |
| **Postcondiciones** | 1. `booking_orders.estado = "checked_in"`.<br>2. `booking_status_history` registra el cambio.<br>3. `room_inventory_calendar` refleja ocupación. |
| **Restricciones** | Solo disponible para rol `recepcionista`. |
| **Colecciones MongoDB** | `booking_orders` (actualización), `booking_status_history` (escritura), `room_inventory_calendar` (actualización) |
| **Endpoints** | `GET /api/management/check-ins` — Lista de check-ins del día.<br>`POST /api/management/check-ins/{booking_id}/complete` — Completar check-in. |
| **Código implementado** | `server/src/app/modules/reservations/` — Rutas de check-in + `_checkinout.py`. |

---

## 6.12 CU-O11: Completar Check-Out

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O11 |
| **Nombre** | Completar check-out |
| **Objetivo** | Permitir que el recepcionista registre la salida del huésped, cambiando el estado de "checked_in" a "checked_out" y liberando la habitación para nuevas reservas |
| **Actor Principal** | Recepcionista |
| **Actores Secundarios** | Sistema |
| **Disparador** | El huésped finaliza su estancia y el recepcionista procede al check-out |
| **Precondiciones** | 1. La reserva debe estar en estado "checked_in".<br>2. La fecha de check-out debe ser igual o anterior a la fecha actual. |
| **Flujo Principal** | **Paso 1:** El recepcionista navega a `GET /api/management/check-outs` para ver la lista de check-outs del día.<br>**Paso 2:** El sistema consulta `booking_orders` con estado "checked_in" y `check_out` = fecha actual.<br>**Paso 3:** El recepcionista encuentra al huésped saliente y hace clic en "Completar check-out".<br>**Paso 4:** El sistema muestra resumen de la estancia y solicita confirmación.<br>**Paso 5:** El recepcionista confirma el check-out.<br>**Paso 6:** El sistema actualiza `booking_orders.estado` a "checked_out".<br>**Paso 7:** El sistema registra en `booking_status_history`: "checked_in" → "checked_out".<br>**Paso 8:** El sistema libera el inventario en `room_inventory_calendar` sumando las habitaciones ocupadas de vuelta al inventario disponible.<br>**Paso 9:** El sistema registra la acción en `user_activity_logs`.<br>**Paso 10:** El sistema muestra confirmación. |
| **Flujos Alternos** | **FA-01: Check-out tardío (late check-out)**<br>Si el huésped sale después del horario de check-out, el recepcionista puede aplicar un cargo adicional.<br><br>**FA-02: Check-out anticipado (early check-out)**<br>Si el huésped sale antes de la fecha prevista, el recepcionista registra el check-out en la fecha real y libera inventario desde esa fecha. |
| **Reglas de Negocio** | **RN-O11-01:** Solo reservas en estado "checked_in" pueden hacer check-out.<br>**RN-O11-02:** El check-out libera el inventario inmediatamente.<br>**RN-O11-03:** Un "checked_out" es el estado final del ciclo de vida de la reserva. |
| **Entradas** | `booking_id`: string — ID de la reserva. |
| **Salidas** | Confirmación de check-out exitoso. |
| **Postcondiciones** | 1. `booking_orders.estado = "checked_out"`.<br>2. `booking_status_history` registra el cambio.<br>3. `room_inventory_calendar` refleja disponibilidad liberada. |
| **Restricciones** | Solo disponible para rol `recepcionista`. |
| **Colecciones MongoDB** | `booking_orders` (actualización), `booking_status_history` (escritura), `room_inventory_calendar` (actualización) |
| **Endpoints** | `GET /api/management/check-outs` — Lista de check-outs del día.<br>`POST /api/management/check-outs/{booking_id}/complete` — Completar check-out. |
| **Código implementado** | `server/src/app/modules/reservations/` — Rutas de check-out + `_checkinout.py`. |

---

## 6.13 CU-O12: Editar Nombre Comercial del Hotel

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O12 |
| **Nombre** | Editar nombre comercial del hotel |
| **Objetivo** | Permitir que el hotel partner o marketing edite el nombre comercial visible del hotel (display_name, hotel_name, descripciones), preservando el prop_id técnico inmutable y activando manual_override para evitar sobrescritura del ETL |
| **Actor Principal** | Marketing hotelero, Hotel partner |
| **Actores Secundarios** | Sistema, ETL |
| **Disparador** | El usuario desea actualizar el nombre comercial de una propiedad para mejorar su presentación en buscadores y detalle |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `marketing_hotelero` o `hotel_partner`.<br>2. La propiedad debe existir en `dim_hotels` con un `prop_id` válido. |
| **Flujo Principal** | **Paso 1:** El usuario navega a la página de edición de perfil del hotel (`GET /partner/hotels/{prop_id}/edit` o `GET /api/management/properties/{prop_id}/edit`).<br>**Paso 2:** El sistema muestra el formulario con los campos editables: display_name, hotel_name, descripción corta, descripción larga.<br>**Paso 3:** El usuario modifica los campos deseados.<br>**Paso 4:** El usuario guarda los cambios.<br>**Paso 5:** El sistema valida que los campos no estén vacíos.<br>**Paso 6:** El sistema actualiza los campos en `dim_hotels`.<br>**Paso 7:** El sistema activa `manual_override = true` en los campos editados para evitar que el ETL los sobrescriba.<br>**Paso 8:** El sistema registra los cambios en `hotel_profile_changes` con: campo, valor_anterior, valor_nuevo, usuario, fecha.<br>**Paso 9:** El sistema registra la acción en `user_activity_logs`.<br>**Paso 10:** El sistema muestra confirmación. |
| **Flujos Alternos** | **FA-01: Intento de editar prop_id**<br>El sistema no permite editar `prop_id` (es la clave técnica inmutable de la propiedad). Si se intenta, el sistema rechaza el cambio.<br><br>**FA-02: Sin cambios detectados**<br>Si el usuario guarda sin hacer cambios, el sistema muestra "No se detectaron cambios para guardar". |
| **Reglas de Negocio** | **RN-O12-01:** El `prop_id` es la clave técnica inmutable de la propiedad y nunca debe cambiar.<br>**RN-O12-02:** `manual_override` impide que el ETL (GA03, TA02) sobrescriba el nombre editado manualmente.<br>**RN-O12-03:** Todos los cambios de perfil quedan registrados en `hotel_profile_changes` para trazabilidad. |
| **Entradas** | `prop_id`, `display_name`, `hotel_name`, `descripcion_corta`, `descripcion_larga` |
| **Salidas** | Confirmación de perfil actualizado. |
| **Postcondiciones** | 1. `dim_hotels` tiene los campos actualizados con `manual_override = true`.<br>2. `hotel_profile_changes` tiene un registro del cambio.<br>3. `user_activity_logs` tiene la auditoría. |
| **Restricciones** | El prop_id es inmutable. No se puede eliminar un override una vez activado. |
| **Colecciones MongoDB** | `dim_hotels` (actualización), `hotel_profile_changes` (escritura), `user_activity_logs` (escritura) |
| **Endpoints** | `GET /partner/hotels/{prop_id}/edit` — Formulario de edición HTML.<br>`PUT /api/management/properties/{prop_id}/profile` — API de actualización.<br>`GET /api/management/properties/{prop_id}/edit` — API con datos actuales. |
| **Código implementado** | `server/src/app/modules/partner/services/properties/` — Servicios de perfil.<br>`server/src/app/modules/partner/routes/hotels.py` — Rutas. |

---

## 6.14 CU-O13: Consultar Historial de Cambios de Propiedad

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O13 |
| **Nombre** | Consultar historial de cambios de propiedad |
| **Objetivo** | Permitir que el auditor de datos o el hotel partner consulte el historial completo de cambios realizados sobre el perfil de una propiedad, incluyendo qué campo cambió, valor anterior, valor nuevo, usuario responsable y fecha |
| **Actor Principal** | Auditor de Datos, Hotel partner |
| **Actores Secundarios** | Sistema |
| **Disparador** | El usuario necesita verificar quién realizó un cambio específico en el perfil de un hotel |
| **Precondiciones** | 1. El usuario debe estar autenticado (rol `auditor_datos` o `hotel_partner`).<br>2. La propiedad debe existir y tener cambios registrados en `hotel_profile_changes`. |
| **Flujo Principal** | **Paso 1:** El usuario navega a la sección de historial de cambios de una propiedad.<br>**Paso 2:** El sistema consulta `hotel_profile_changes` filtrado por `prop_id`.<br>**Paso 3:** El sistema devuelve una lista cronológica con: fecha, usuario, campo modificado, valor anterior, valor nuevo.<br>**Paso 4:** El usuario puede filtrar por campo, usuario o rango de fechas. |
| **Flujos Alternos** | **FA-01: Sin cambios registrados**<br>El sistema muestra "No hay cambios registrados para esta propiedad". |
| **Reglas de Negocio** | **RN-O13-01:** Todos los cambios críticos de perfil son registrados en `hotel_profile_changes`.<br>**RN-O13-02:** El historial es de solo lectura y no puede modificarse ni eliminarse. |
| **Entradas** | `prop_id`, filtros opcionales (fecha desde/hasta, usuario, campo). |
| **Salidas** | Lista cronológica de cambios con detalle completo. |
| **Postcondiciones** | El usuario visualiza el historial. No se modifica la base de datos. |
| **Colecciones MongoDB** | `hotel_profile_changes` (lectura) |
| **Endpoints** | `GET /api/management/properties/{prop_id}/profile` — Incluye historial.<br>Auditoría general: `GET /api/audit/activity`. |
| **Código implementado** | `server/src/app/modules/partner/services/properties/` — Consulta de perfil.<br>`server/src/app/modules/audit/` — Auditoría general. |

---

## 6.15 CU-O14: Crear Tipo de Habitación

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O14 |
| **Nombre** | Crear tipo de habitación |
| **Objetivo** | Permitir que el hotel partner defina los tipos de habitación de su propiedad (estándar, deluxe, suite, etc.) especificando nombre, capacidad, descripción y comodidades incluidas |
| **Actor Principal** | Hotel partner |
| **Actores Secundarios** | Sistema |
| **Disparador** | El hotel partner necesita configurar los tipos de habitación que ofrece su propiedad |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `hotel_partner`.<br>2. La propiedad debe existir en `dim_hotels`.<br>3. El tipo de habitación no debe existir previamente con el mismo nombre en la misma propiedad. |
| **Flujo Principal** | **Paso 1:** El usuario navega a la sección de tipos de habitación (`GET /partner/hotels/{prop_id}/rooms`).<br>**Paso 2:** El usuario hace clic en "Nuevo tipo de habitación".<br>**Paso 3:** El sistema muestra el formulario con: nombre, descripción, capacidad máxima (adultos, niños), cantidad de habitaciones físicas, comodidades.<br>**Paso 4:** El usuario completa los datos y guarda.<br>**Paso 5:** El sistema valida los datos (nombre no vacío, capacidad > 0).<br>**Paso 6:** El sistema crea el documento en `room_types` con: prop_id, room_type_id, nombre, capacidad, cantidad, comodidades.<br>**Paso 7:** El sistema crea las habitaciones físicas en `hotel_rooms` según la cantidad especificada.<br>**Paso 8:** El sistema muestra confirmación. |
| **Reglas de Negocio** | **RN-O14-01:** El nombre del tipo de habitación debe ser único por propiedad.<br>**RN-O14-02:** La capacidad máxima de adultos no puede exceder 10.<br>**RN-O14-03:** La cantidad de habitaciones físicas debe ser ≥ 1. |
| **Entradas** | `prop_id`, `nombre`, `descripcion`, `capacidad_adultos`, `capacidad_ninos`, `cantidad_habitaciones`, `comodidades[]` |
| **Salidas** | Confirmación con `room_type_id` asignado. |
| **Postcondiciones** | 1. `room_types` tiene un nuevo documento.<br>2. `hotel_rooms` tiene N nuevos documentos (uno por habitación física). |
| **Colecciones MongoDB** | `room_types` (escritura), `hotel_rooms` (escritura) |
| **Endpoints** | `GET /partner/hotels/{prop_id}/rooms/new` — Formulario HTML.<br>`POST /partner/hotels/{prop_id}/rooms/new` — Crear desde formulario.<br>`POST /api/management/rooms` — Crear vía API. |
| **Código implementado** | `server/src/app/modules/partner/services/rooms.py` — Servicios de room types.<br>`server/src/app/modules/partner/routes/rooms.py` — Rutas. |

---

## 6.16 CU-O15: Actualizar Inventario por Fecha

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O15 |
| **Nombre** | Actualizar inventario por fecha |
| **Objetivo** | Permitir que el gerente de hotel actualice el inventario diario de habitaciones disponible por fecha y tipo de habitación, con control de concurrencia mediante optimistic locking |
| **Actor Principal** | Gerente de hotel |
| **Actores Secundarios** | Sistema |
| **Disparador** | El gerente necesita ajustar la cantidad de habitaciones disponibles para una fecha específica |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `gerente_hotel` o `hotel_partner`.<br>2. Debe existir al menos un tipo de habitación para la propiedad (`room_types`). |
| **Flujo Principal** | **Paso 1:** El gerente navega a la página de inventario del hotel (`GET /partner/hotels/{prop_id}/inventory`).<br>**Paso 2:** El sistema muestra el calendario de inventario con: fecha, tipo de habitación, total disponible, bloqueado, reservado.<br>**Paso 3:** El gerente selecciona una fecha y un tipo de habitación, e ingresa los nuevos valores de inventario total y disponible.<br>**Paso 4:** El sistema recibe los datos vía `POST /api/management/availability`.<br>**Paso 5:** El sistema busca el documento existente en `room_inventory_calendar` con key `{prop_id}_{room_type_id}_{date}`.<br>**Paso 6:** Si el documento existe, el sistema verifica el campo `version` para optimistic locking.<br>**Paso 7:** Si la versión coincide, el sistema actualiza el inventario e incrementa `version`.<br>**Paso 8:** Si no existe, el sistema crea un nuevo documento con `version = 1`.<br>**Paso 9:** El sistema responde con confirmación. |
| **Flujos Alternos** | **FA-01: Conflicto de concurrencia**<br>Si otro usuario o proceso actualizó el mismo registro entre la lectura y la escritura (version mismatch), el sistema rechaza la actualización y muestra "El inventario fue modificado por otro usuario. Recargue e intente nuevamente."<br><br>**FA-02: Sin registro previo**<br>Si no existe un documento para la fecha/tipo de habitación, el sistema lo crea automáticamente. |
| **Reglas de Negocio** | **RN-O15-01:** El inventario disponible no puede exceder el inventario total.<br>**RN-O15-02:** El inventario disponible no puede ser negativo.<br>**RN-O15-03:** El inventario bloqueado + reservado no puede exceder el inventario total.<br>**RN-O15-04:** El control de concurrencia usa optimistic locking con campo `version`. |
| **Entradas** | `prop_id`, `room_type_id`, `fecha`, `total_disponible`, `disponible`, `bloqueado`, `expected_version` (opcional para actualización) |
| **Salidas** | Confirmación con nuevo `version`. |
| **Postcondiciones** | `room_inventory_calendar` tiene el documento actualizado con inventario correcto. |
| **Colecciones MongoDB** | `room_inventory_calendar` (actualización/creación) |
| **Endpoints** | `GET /partner/hotels/{prop_id}/inventory` — Vista de inventario HTML.<br>`POST /partner/hotels/{prop_id}/inventory` — Actualizar desde formulario.<br>`POST /api/management/availability` — Actualizar vía API. |
| **Código implementado** | `server/src/app/modules/partner/services/rooms.py` — `save_inventory_entry()` con optimistic locking.<br>`server/src/app/modules/partner/routes/availability.py` — Rutas. |

---

## 6.17 CU-O16: Registrar Bloqueo de Disponibilidad

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O16 |
| **Nombre** | Registrar bloqueo de disponibilidad |
| **Objetivo** | Permitir que el gerente de hotel bloquee rangos de fecha completos para ciertos tipos de habitación (mantenimiento, temporada baja, eventos privados), impidiendo reservas en esas fechas |
| **Actor Principal** | Gerente de hotel |
| **Actores Secundarios** | Sistema |
| **Disparador** | El gerente necesita bloquear disponibilidad para un rango de fechas por mantenimiento o cierre temporal |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `gerente_hotel` o `hotel_partner`.<br>2. Debe existir al menos un tipo de habitación para la propiedad. |
| **Flujo Principal** | **Paso 1:** El gerente navega a la sección de bloqueos de disponibilidad.<br>**Paso 2:** El sistema muestra un formulario para crear bloqueo: tipo de habitación, rango de fechas, motivo.<br>**Paso 3:** El gerente completa los datos y confirma.<br>**Paso 4:** El sistema crea un documento en `blackout_dates` con el rango.<br>**Paso 5:** El sistema actualiza `room_inventory_calendar` para cada fecha del rango, marcando el inventario como bloqueado.<br>**Paso 6:** El sistema registra la acción en `user_activity_logs`.<br>**Paso 7:** El sistema muestra confirmación. |
| **Reglas de Negocio** | **RN-O16-01:** Un bloqueo impide que se realicen nuevas reservas en esas fechas.<br>**RN-O16-02:** Las reservas existentes en el rango de fechas no se ven afectadas.<br>**RN-O16-03:** Un bloqueo puede ser parcial (solo algunos tipos de habitación) o total (toda la propiedad). |
| **Entradas** | `prop_id`, `room_type_id` (opcional, todos si no se especifica), `fecha_inicio`, `fecha_fin`, `motivo` |
| **Salidas** | Confirmación de bloqueo creado. |
| **Postcondiciones** | 1. `blackout_dates` tiene el registro del bloqueo.<br>2. `room_inventory_calendar` refleja el bloqueo en las fechas afectadas. |
| **Colecciones MongoDB** | `blackout_dates` (escritura), `room_inventory_calendar` (actualización), `room_availability_blocks` (escritura) |
| **Endpoints** | `POST /partner/hotels/{prop_id}/blackout-dates` — Crear bloqueo desde HTML.<br>`POST /api/management/availability/blackouts` — Crear bloqueo vía API. |
| **Código implementado** | `server/src/app/modules/partner/services/rooms.py` — Gestión de blackouts.<br>`server/src/app/modules/partner/routes/availability.py` — Rutas. |

---

## 6.18 CU-O17: Crear Plan Tarifario

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O17 |
| **Nombre** | Crear plan tarifario |
| **Objetivo** | Permitir que el revenue manager cree planes tarifarios (tarifa estándar, tarifa corporativa, tarifa de fin de semana, tarifa no reembolsable, etc.) con reglas de precio base, restricciones de estadía mínima y condiciones de cancelación |
| **Actor Principal** | Revenue manager |
| **Actores Secundarios** | Sistema |
| **Disparador** | El revenue manager necesita definir un nuevo plan de precios para los tipos de habitación de una propiedad |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `revenue_manager`.<br>2. Debe existir al menos un tipo de habitación en la propiedad. |
| **Flujo Principal** | **Paso 1:** El revenue manager navega a `GET /revenue/rate-plans/new` o a la sección de planes tarifarios.<br>**Paso 2:** El sistema muestra un formulario con: nombre del plan, descripción, tipo de habitación, precio base por noche, moneda, restricciones (estadía mínima, anticipación máxima), política de cancelación asociada.<br>**Paso 3:** El revenue manager completa los datos y guarda.<br>**Paso 4:** El sistema valida los datos (precio > 0, nombre único por propiedad).<br>**Paso 5:** El sistema crea el documento en `rate_plans` con: prop_id, rate_plan_id, nombre, room_type_id, precio_base, restricciones.<br>**Paso 6:** El sistema registra la acción en `user_activity_logs`.<br>**Paso 7:** El sistema muestra confirmación. |
| **Reglas de Negocio** | **RN-O17-01:** El nombre del plan tarifario debe ser único por propiedad.<br>**RN-O17-02:** El precio base por noche debe ser mayor que 0.<br>**RN-O17-03:** Un plan tarifario puede asociarse a uno o varios tipos de habitación.<br>**RN-O17-04:** Las reglas de tarifa (rate_rules) definen variaciones sobre el precio base. |
| **Entradas** | `prop_id`, `nombre`, `descripcion`, `room_type_id`, `precio_base`, `moneda`, `estadia_minima`, `anticipacion_maxima`, `politica_cancelacion` |
| **Salidas** | Confirmación con `rate_plan_id` asignado. |
| **Postcondiciones** | `rate_plans` tiene un nuevo documento con el plan tarifario. |
| **Colecciones MongoDB** | `rate_plans` (escritura), `rate_rules` (lectura), `user_activity_logs` (escritura) |
| **Endpoints** | `GET /revenue/rate-plans/new` — Formulario HTML.<br>`POST /revenue/rate-plans/new` — Crear desde HTML.<br>`POST /api/management/rates/plans` — Crear vía API. |
| **Código implementado** | `server/src/app/modules/revenue/services/rate_plans.py`.<br>`server/src/app/modules/partner/services/rates.py`. |

---

## 6.19 CU-O18: Configurar Tarifa por Fecha

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O18 |
| **Nombre** | Configurar tarifa por fecha |
| **Objetivo** | Permitir que el revenue manager configure precios específicos por fecha y plan tarifario en el calendario de tarifas, aplicando precios dinámicos según temporada, demanda o eventos especiales |
| **Actor Principal** | Revenue manager |
| **Actores Secundarios** | Sistema |
| **Disparador** | El revenue manager necesita ajustar el precio de un plan tarifario para una fecha o rango de fechas específico |
| **Precondiciones** | 1. Debe existir al menos un plan tarifario (`rate_plans`).<br>2. El usuario debe estar autenticado con rol `revenue_manager`. |
| **Flujo Principal** | **Paso 1:** El revenue manager navega al calendario de tarifas (`GET /revenue/hotel/{prop_id}/rates`).<br>**Paso 2:** El sistema muestra el calendario mensual con los precios actuales por día y plan tarifario.<br>**Paso 3:** El revenue manager selecciona una fecha o rango, elige un plan tarifario e ingresa el nuevo precio.<br>**Paso 4:** El sistema recibe los datos vía `POST /api/management/rates/calendar`.<br>**Paso 5:** El sistema crea o actualiza el documento en `hotel_rate_calendar` con: prop_id, rate_plan_id, fecha, precio, moneda.<br>**Paso 6:** El sistema muestra el calendario actualizado. |
| **Reglas de Negocio** | **RN-O18-01:** El precio por noche debe ser mayor que 0.<br>**RN-O18-02:** Un precio configurado en el calendario sobreescribe el precio base del plan para esa fecha.<br>**RN-O18-03:** Se pueden configurar precios diferentes por tipo de habitación y plan tarifario para la misma fecha. |
| **Entradas** | `prop_id`, `rate_plan_id`, `fecha` (o rango `fecha_inicio`-`fecha_fin`), `precio`, `moneda` |
| **Salidas** | Calendario de tarifas actualizado. |
| **Postcondiciones** | `hotel_rate_calendar` tiene el precio configurado para las fechas especificadas. |
| **Colecciones MongoDB** | `hotel_rate_calendar` (actualización/creación) |
| **Endpoints** | `GET /revenue/hotel/{prop_id}/rates` — Calendario HTML.<br>`POST /revenue/hotel/{prop_id}/rates` — Guardar desde HTML.<br>`POST /api/management/rates/calendar` — Guardar vía API. |
| **Código implementado** | `server/src/app/modules/revenue/services/hotel_rates.py`.<br>`server/src/app/modules/partner/services/rates.py`. |

---

## 6.20 CU-O19: Crear Promoción y Cupón

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O19 |
| **Nombre** | Crear promoción y cupón |
| **Objetivo** | Permitir que marketing o revenue manager cree campañas promocionales con descuento porcentual sobre las tarifas, generando códigos de cupón asociados para incentivar reservas en períodos de baja demanda |
| **Actor Principal** | Marketing hotelero, Revenue manager |
| **Actores Secundarios** | Sistema |
| **Disparador** | El equipo de marketing desea lanzar una promoción por temporada baja con código de descuento |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `marketing_hotelero` o `revenue_manager`.<br>2. Debe existir al menos un plan tarifario activo. |
| **Flujo Principal** | **Paso 1:** El usuario navega a `GET /revenue/promotions/new` o a la sección de promociones.<br>**Paso 2:** El sistema muestra formulario con: nombre de campaña, descripción, tipo de descuento (porcentaje o monto fijo), valor del descuento, fechas de vigencia, hoteles aplicables, tipos de habitación, código de cupón (auto-generado o manual), usos máximos.<br>**Paso 3:** El usuario completa los datos y guarda.<br>**Paso 4:** El sistema valida: descuento > 0 y ≤ 100% (si es porcentaje), vigencia correcta.<br>**Paso 5:** El sistema crea `promotion_campaigns` con los datos de la campaña.<br>**Paso 6:** El sistema crea `coupon_codes` con el código de cupón asociado, límite de usos y vigencia.<br>**Paso 7:** El sistema muestra confirmación con el código de cupón generado. |
| **Reglas de Negocio** | **RN-O19-01:** Un descuento porcentual no puede exceder 100%.<br>**RN-O19-02:** Un código de cupón puede tener un límite de usos máximos (si no se especifica, es ilimitado dentro de la vigencia).<br>**RN-O19-03:** Una promoción puede aplicarse a uno o varios hoteles y tipos de habitación.<br>**RN-O19-04:** El código de cupón debe ser único en el sistema. |
| **Entradas** | `nombre`, `descripcion`, `tipo_descuento` (porcentaje/monto_fijo), `valor_descuento`, `fecha_inicio`, `fecha_fin`, `hoteles[]`, `room_types[]`, `codigo_cupon`, `usos_maximos` |
| **Salidas** | Confirmación con ID de campaña y código de cupón generado. |
| **Postcondiciones** | 1. `promotion_campaigns` tiene la campaña registrada.<br>2. `coupon_codes` tiene el código de cupón asociado. |
| **Colecciones MongoDB** | `promotion_campaigns` (escritura), `coupon_codes` (escritura) |
| **Endpoints** | `GET /revenue/promotions/new` — Formulario HTML.<br>`POST /revenue/promotions/new` — Crear desde HTML.<br>`POST /api/management/rates/plans` — Las promociones se gestionan desde revenue module. |
| **Código implementado** | `server/src/app/modules/revenue/services/promotions.py`.<br>`server/src/app/modules/partner/services/rates.py`. |

---

## 6.21 CU-O20: Editar Política Hotelera

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O20 |
| **Nombre** | Editar política hotelera |
| **Objetivo** | Permitir que el hotel partner configure las políticas de la propiedad: horarios de check-in/check-out, política de cancelación, admisión de mascotas, política de niños y condiciones de uso |
| **Actor Principal** | Hotel partner |
| **Actores Secundarios** | Sistema |
| **Disparador** | El hotel partner necesita actualizar las políticas operativas de su propiedad |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `hotel_partner`.<br>2. La propiedad debe existir. |
| **Flujo Principal** | **Paso 1:** El usuario navega a `GET /partner/hotels/{prop_id}/policies`.<br>**Paso 2:** El sistema muestra el formulario de políticas con: check-in desde/hasta, check-out desde/hasta, política de cancelación (días de anticipación, cargos), política de mascotas (permitido, peso máximo, costo adicional), política de niños, condiciones generales.<br>**Paso 3:** El usuario modifica los campos y guarda.<br>**Paso 4:** El sistema actualiza el documento en `hotel_policies`.<br>**Paso 5:** El sistema registra los cambios en `hotel_content_changes`.<br>**Paso 6:** El sistema muestra confirmación. |
| **Reglas de Negocio** | **RN-O20-01:** El horario de check-out debe ser posterior al horario de check-in.<br>**RN-O20-02:** La política de cancelación debe especificar días de anticipación y porcentaje de cargo.<br>**RN-O20-03:** Si se permite mascotas, debe especificarse el peso máximo y costo adicional (si aplica). |
| **Entradas** | `prop_id`, `check_in_desde`, `check_in_hasta`, `check_out_desde`, `check_out_hasta`, `cancelacion_dias`, `cancelacion_cargo_pct`, `mascotas_permitidas`, `mascotas_peso_max`, `mascotas_costo`, `ninos_politica`, `condiciones_generales` |
| **Salidas** | Confirmación de políticas actualizadas. |
| **Postcondiciones** | `hotel_policies` tiene las políticas actualizadas. `hotel_content_changes` tiene el registro del cambio. |
| **Colecciones MongoDB** | `hotel_policies` (actualización), `hotel_content_changes` (escritura) |
| **Endpoints** | `GET /partner/hotels/{prop_id}/policies` — Formulario HTML.<br>`POST /partner/hotels/{prop_id}/policies` — Guardar desde HTML.<br>`PUT /api/management/policies` — Guardar vía API. |
| **Código implementado** | `server/src/app/modules/partner/services/content/save.py`.<br>`server/src/app/modules/partner/routes/policies.py`. |

---

## 6.22 CU-O21: Actualizar Amenities, Imágenes y Contenido

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O21 |
| **Nombre** | Actualizar amenities, imágenes y contenido |
| **Objetivo** | Permitir que el marketing hotelero administre el contenido comercial de la propiedad: galería de imágenes, lista de amenities (WiFi, piscina, gimnasio, restaurante), descripciones extendidas y highlights para mejorar la presentación ante clientes |
| **Actor Principal** | Marketing hotelero |
| **Actores Secundarios** | Sistema |
| **Disparador** | El equipo de marketing necesita actualizar las imágenes o amenities de una propiedad para mejorar su atractivo comercial |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `marketing_hotelero`.<br>2. La propiedad debe existir. |
| **Flujo Principal** | **Paso 1:** El usuario navega al gestor de contenido de la propiedad (`GET /partner/hotels/{prop_id}/content`).<br>**Paso 2:** El sistema muestra las secciones: Amenities (selección de catálogo), Descripciones (texto), Imágenes (galería).<br>**Paso 3:** El usuario marca/desmarca amenities del catálogo disponible, edita descripciones, sube/elimina imágenes.<br>**Paso 4:** El usuario guarda los cambios.<br>**Paso 5:** El sistema actualiza `hotel_content_pages` con descripciones y amenities.<br>**Paso 6:** El sistema actualiza `hotel_images` con las nuevas imágenes (almacena el archivo en MongoDB GridFS o como base64).<br>**Paso 7:** El sistema registra los cambios en `hotel_content_changes`.<br>**Paso 8:** El sistema muestra confirmación. |
| **Reglas de Negocio** | **RN-O21-01:** Las imágenes deben estar en formato JPEG o PNG, tamaño máximo 5MB cada una.<br>**RN-O21-02:** Las amenities se seleccionan de un catálogo predefinido (`system_catalogs`).<br>**RN-O21-03:** Cada propiedad debe tener al menos una imagen principal (portada). |
| **Entradas** | `prop_id`, `amenities[]`, `descripcion_corta`, `descripcion_larga`, `highlights[]`, `imagenes[]` (archivos) |
| **Salidas** | Confirmación de contenido actualizado. |
| **Postcondiciones** | `hotel_content_pages` actualizado. `hotel_images` actualizado. `hotel_content_changes` registra los cambios. |
| **Colecciones MongoDB** | `hotel_content_pages` (actualización), `hotel_images` (actualización), `hotel_content_changes` (escritura), `system_catalogs` (lectura) |
| **Endpoints** | `GET /partner/hotels/{prop_id}/content` — Gestor de contenido HTML.<br>`POST /partner/hotels/{prop_id}/content/edit` — Guardar contenido.<br>`POST /partner/hotels/{prop_id}/images` — Subir imagen.<br>`DELETE /api/management/properties/{prop_id}/images` — Eliminar imagen.<br>`PUT /api/management/properties/{prop_id}/content` — Guardar vía API.<br>`PUT /api/management/amenities` — Guardar amenities vía API. |
| **Código implementado** | `server/src/app/modules/partner/services/content/` — Save, images, amenities.<br>`server/src/app/modules/partner/routes/content.py` — Rutas de contenido.<br>`server/src/app/modules/partner/routes/amenities.py` — Rutas de amenities. |

---

## 6.23 CU-O22: Registrar Reseña de Estancia

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O22 |
| **Nombre** | Registrar reseña de estancia |
| **Objetivo** | Permitir que el cliente registre una reseña después de su estancia, con calificación general (1-5), calificaciones por categoría (limpieza, ubicación, servicio, confort), comentario escrito y fotos opcionales, con dual-write a la fact table analítica |
| **Actor Principal** | Cliente |
| **Actores Secundarios** | Sistema (moderación automática, dual-write a fact_reviews) |
| **Disparador** | El cliente ha completado su estancia (check-out realizado) y desea dejar una reseña |
| **Precondiciones** | 1. El cliente debe estar autenticado.<br>2. El cliente debe haber tenido una reserva en estado "checked_out" en la propiedad.<br>3. El cliente no debe haber registrado ya una reseña para esa misma reserva. |
| **Flujo Principal** | **Paso 1:** El cliente navega a la sección de reseñas desde el detalle del hotel o desde sus reservas completadas.<br>**Paso 2:** El sistema muestra un formulario con: calificación general (estrellas 1-5), calificaciones por categoría (limpieza, ubicación, servicio, confort), título del comentario, comentario detallado, fotos opcionales.<br>**Paso 3:** El cliente completa y envía la reseña.<br>**Paso 4:** El sistema recibe los datos vía `POST /api/reviews/`.<br>**Paso 5:** El sistema crea el documento en `reviews` con: prop_id, booking_id, user_id, calificaciones, comentario, fecha, estado "pending".<br>**Paso 6:** El sistema realiza el dual-write a `fact_reviews` con los mismos datos para alimentar métricas analíticas.<br>**Paso 7:** El sistema muestra "Reseña enviada. Gracias por tu opinión. Estará visible después de ser moderada." |
| **Flujos Alternos** | **FA-01: Reserva no completada**<br>Si el cliente intenta reseñar sin haber completado el check-out, el sistema muestra "Debes completar tu estancia antes de dejar una reseña".<br><br>**FA-02: Reseña duplicada**<br>Si el cliente ya reseñó esa reserva, el sistema muestra "Ya has dejado una reseña para esta reserva. Puedes editarla si lo deseas." |
| **Reglas de Negocio** | **RN-O22-01:** Solo clientes con reserva completada (checked_out) pueden reseñar.<br>**RN-O22-02:** Una reseña por reserva (no se pueden reseñar múltiples veces la misma estancia).<br>**RN-O22-03:** Las reseñas se crean en estado "pending" y deben ser moderadas (CU-O23) antes de ser públicas.<br>**RN-O22-04:** El dual-write a `fact_reviews` garantiza que las métricas de satisfacción estén disponibles para reportes. |
| **Entradas** | `prop_id`, `booking_id`, `calificacion_general` (1-5), `calificacion_limpieza`, `calificacion_ubicacion`, `calificacion_servicio`, `calificacion_confort`, `titulo`, `comentario`, `fotos[]` (opcional) |
| **Salidas** | Mensaje de confirmación: "Reseña enviada. Estará visible después de ser moderada." |
| **Postcondiciones** | 1. `reviews` tiene un nuevo documento en estado "pending".<br>2. `fact_reviews` tiene el registro para analítica.<br>3. La reseña no es visible al público hasta que sea moderada. |
| **Restricciones** | Las fotos deben ser JPEG/PNG, máximo 2MB cada una. |
| **Colecciones MongoDB** | `reviews` (escritura), `fact_reviews` (escritura) |
| **Endpoints** | `POST /api/reviews/` — Crear reseña vía API. |
| **Código implementado** | `server/src/app/modules/reviews/` — Rutas y servicios (`lifecycle.py`, `collections.py`). |

---

## 6.24 CU-O23: Moderar y Responder Reseña

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O23 |
| **Nombre** | Moderar y responder reseña |
| **Objetivo** | Permitir que marketing hotelero o super admin modere las reseñas recibidas (aprobar o rechazar), y responder a las reseñas aprobadas para gestionar la reputación online del hotel |
| **Actor Principal** | Marketing hotelero, Super Admin |
| **Actores Secundarios** | Sistema |
| **Disparador** | Hay reseñas pendientes de moderación o se necesita responder a una reseña existente |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `marketing_hotelero` o `super_admin`.<br>2. Debe existir al menos una reseña en estado "pending" o "approved" para moderar/responder. |
| **Flujo Principal** | **Paso 1:** El moderador navega al panel de reseñas (`GET /management/reviews` en frontend).<br>**Paso 2:** El sistema muestra lista de reseñas con filtros: pendientes, aprobadas, rechazadas.<br>**Paso 3:** El moderador selecciona una reseña pendiente y hace clic en "Moderar".<br>**Paso 4:** El sistema muestra el detalle de la reseña con opciones: "Aprobar" o "Rechazar" (con motivo de rechazo).<br>**Paso 5:** Si el moderador aprueba, el sistema cambia el estado a "approved" en `reviews` y actualiza `fact_reviews`.<br>**Paso 6:** Si el moderador rechaza, el sistema cambia el estado a "rejected" con el motivo.<br>**Paso 7:** Para reseñas aprobadas, el moderador puede escribir una respuesta pública.<br>**Paso 8:** El sistema envía la respuesta a `PATCH /api/reviews/{review_id}/respond`.<br>**Paso 9:** El sistema guarda la respuesta en el documento de la reseña con fecha y usuario.<br>**Paso 10:** El sistema registra la acción en `user_activity_logs`. |
| **Flujos Alternos** | **FA-01: Moderación automática**<br>Las reseñas con calificación ≥ 4 se aprueban automáticamente. Las reseñas con calificación ≤ 2 requieren moderación manual.<br><br>**FA-02: Reapertura de reseña rechazada**<br>Un administrador puede reabrir una reseña rechazada para revisión adicional. |
| **Reglas de Negocio** | **RN-O23-01:** Las reseñas deben ser moderadas antes de hacerse públicas.<br>**RN-O23-02:** Una reseña aprobada no puede eliminarse (solo desactivarse como "hidden").<br>**RN-O23-03:** Una reseña rechazada no es visible para el público ni para el cliente que la escribió.<br>**RN-O23-04:** La respuesta a una reseña queda visible públicamente junto con la reseña. |
| **Entradas** | `review_id`, `accion` (approve/reject), `motivo_rechazo` (si aplica), `respuesta_texto` (si aplica) |
| **Salidas** | Confirmación de moderación o respuesta. |
| **Postcondiciones** | 1. La reseña cambia a estado "approved" o "rejected" con motivo.<br>2. Si se respondió, la respuesta queda visible.<br>3. `fact_reviews` se actualiza si cambió el estado de moderación. |
| **Colecciones MongoDB** | `reviews` (actualización), `fact_reviews` (actualización) |
| **Endpoints** | `PATCH /api/reviews/{review_id}/moderate` — Moderar reseña.<br>`PATCH /api/reviews/{review_id}/respond` — Responder reseña.<br>`GET /api/reviews/` — Listar reseñas con filtros. |
| **Código implementado** | `server/src/app/modules/reviews/` — Rutas de moderación y respuesta.<br>`frontend/src/app/features/reviews/` — ReviewDetailPage (moderate/respond). |

---

## 6.25 CU-O24: Generar Comprobante o Factura de Reserva

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O24 |
| **Nombre** | Generar comprobante o factura de reserva |
| **Objetivo** | Generar un comprobante o factura asociada a una reserva confirmada o finalizada, con desglose de cargos (habitación, impuestos, cargos adicionales), estado de pago y número de factura único, con dual-write a fact_invoices |
| **Actor Principal** | Sistema (generación automática), Recepcionista (generación manual) |
| **Actores Secundarios** | Sistema |
| **Disparador** | La reserva cambia a estado "checked_out" (generación automática) o el recepcionista solicita generar una factura |
| **Precondiciones** | 1. La reserva debe existir en estado "confirmed", "checked_in" o "checked_out".<br>2. No debe existir ya una factura para la misma reserva (a menos que sea rectificativa). |
| **Flujo Principal** | **Paso 1:** El sistema (o el recepcionista) inicia la generación del comprobante.<br>**Paso 2:** El sistema consulta `booking_orders` para obtener datos de la reserva: hotel, fechas, tipo habitación, huéspedes.<br>**Paso 3:** El sistema calcula el total: suma de tarifas por noche + impuestos + cargos adicionales (si aplican).<br>**Paso 4:** El sistema genera un número de factura único.<br>**Paso 5:** El sistema crea el documento en `reservation_invoices` con: invoice_id, booking_id, prop_id, datos del hotel, datos del huésped, desglose, subtotal, impuestos, total, fecha emisión, estado "pending".<br>**Paso 6:** El sistema realiza dual-write a `fact_invoices` con los mismos datos para analítica.<br>**Paso 7:** El sistema muestra el comprobante generado. |
| **Reglas de Negocio** | **RN-O24-01:** Una reserva puede tener una o más facturas (si hay rectificaciones).<br>**RN-O24-02:** El número de factura debe ser único en el sistema.<br>**RN-O24-03:** La factura incluye: subtotal (habitación), impuestos, cargos adicionales, total.<br>**RN-O24-04:** El dual-write a `fact_invoices` garantiza disponibilidad para reportes financieros. |
| **Entradas** | `booking_id`: string — ID de la reserva. |
| **Salidas** | JSON con invoice_id, número de factura, desglose, total, estado. |
| **Postcondiciones** | 1. `reservation_invoices` tiene la factura generada.<br>2. `fact_invoices` tiene el registro analítico. |
| **Restricciones** | Los pagos son simulados, sin integración bancaria real (proyecto educacional). |
| **Colecciones MongoDB** | `reservation_invoices` (escritura), `fact_invoices` (escritura), `booking_orders` (lectura) |
| **Endpoints** | `POST /api/billing/invoices` — Crear factura.<br>`GET /api/billing/invoices` — Listar facturas.<br>`GET /api/billing/invoices/{invoice_id}` — Detalle de factura. |
| **Código implementado** | `server/src/app/modules/billing/` — Rutas y servicios (`lifecycle.py`, `collections.py`). |

---

## 6.26 CU-O25: Registrar Pago Asociado a Reserva

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O25 |
| **Nombre** | Registrar pago asociado a reserva |
| **Objetivo** | Registrar un pago asociado a una factura de reserva, especificando método de pago (efectivo, tarjeta, transferencia), monto, fecha y referencia externa, con dual-write a fact_payments |
| **Actor Principal** | Recepcionista |
| **Actores Secundarios** | Sistema |
| **Disparador** | El huésped realiza el pago de su factura al momento del check-out o durante su estancia |
| **Precondiciones** | 1. Debe existir una factura asociada a la reserva (`reservation_invoices`).<br>2. La factura no debe estar previamente pagada en su totalidad.<br>3. El usuario debe estar autenticado con rol `recepcionista`. |
| **Flujo Principal** | **Paso 1:** El recepcionista navega a la sección de pagos de la reserva o factura.<br>**Paso 2:** El sistema muestra el detalle de la factura y los pagos registrados.<br>**Paso 3:** El recepcionista ingresa el monto del pago, selecciona el método de pago (efectivo, tarjeta débito/crédito, transferencia), ingresa referencia externa (opcional).<br>**Paso 4:** El sistema recibe los datos vía `POST /api/billing/payments`.<br>**Paso 5:** El sistema crea el documento en `reservation_payments` con: payment_id, invoice_id, monto, método, referencia, fecha, usuario que registra.<br>**Paso 6:** El sistema actualiza el estado de la factura: si el total pagado = total factura, marca como "paid". Si es parcial, queda "partial".<br>**Paso 7:** El sistema realiza dual-write a `fact_payments` con los mismos datos.<br>**Paso 8:** El sistema registra la acción en `user_activity_logs`.<br>**Paso 9:** El sistema muestra confirmación. |
| **Flujos Alternos** | **FA-01: Pago parcial**<br>Si se registra un pago por menos del total de la factura, la factura queda como "partial" y permite pagos adicionales.<br><br>**FA-02: Reembolso**<br>Si se necesita anular un pago, el recepcionista puede registrar un reembolso. |
| **Reglas de Negocio** | **RN-O25-01:** El monto del pago debe ser mayor que 0.<br>**RN-O25-02:** La suma de pagos no puede exceder el total de la factura.<br>**RN-O25-03:** Los pagos son simulados (no hay integración real con pasarela de pagos).<br>**RN-O25-04:** El dual-write a `fact_payments` garantiza disponibilidad para reportes financieros. |
| **Entradas** | `invoice_id`, `monto`, `metodo_pago` (efectivo/tarjeta_debito/tarjeta_credito/transferencia), `referencia_externa` (opcional), `notas` (opcional) |
| **Salidas** | Confirmación con `payment_id` y estado actualizado de la factura. |
| **Postcondiciones** | 1. `reservation_payments` tiene el pago registrado.<br>2. `fact_payments` tiene el registro analítico.<br>3. `reservation_invoices.estado_pago` se actualiza (paid/partial). |
| **Restricciones** | Sin integración bancaria real. Todos los pagos son declarativos para el proyecto educacional. |
| **Colecciones MongoDB** | `reservation_payments` (escritura), `fact_payments` (escritura), `reservation_invoices` (actualización) |
| **Endpoints** | `POST /api/billing/payments` — Registrar pago.<br>`POST /api/billing/payments/{payment_id}/refund` — Reembolsar pago.<br>`GET /api/billing/payments` — Listar pagos.<br>`GET /api/billing/payments/{payment_id}` — Detalle de pago. |
| **Código implementado** | `server/src/app/modules/billing/` — Rutas y servicios (`lifecycle.py`). |

---

## 6.27 CU-O26: Consultar Reportes de Revenue y Mercado

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O26 |
| **Nombre** | Consultar reportes de revenue y mercado |
| **Objetivo** | Permitir que gerentes y revenue managers consulten dashboards y reportes con métricas clave de negocio: eventos totales, reservas, conversión, revenue bruto, precio promedio, top hoteles, top destinos, top países visitantes |
| **Actor Principal** | Gerente de hotel, Revenue manager |
| **Actores Secundarios** | Sistema (cálculo de agregaciones desde fact tables) |
| **Disparador** | El usuario necesita visualizar indicadores de rendimiento para tomar decisiones |
| **Precondiciones** | 1. Los datos deben estar cargados en `fact_hotel_reservations` y dimensiones.<br>2. El usuario debe estar autenticado con rol autorizado. |
| **Flujo Principal** | **Paso 1:** El usuario navega a la sección de reportes (`GET /analytics/revenue` o dashboard).<br>**Paso 2:** El sistema consulta `fact_hotel_reservations` con agregaciones sobre dimensiones.<br>**Paso 3:** El sistema calcula y muestra: eventos totales, reservas detectadas, click rate, revenue bruto, precio promedio, top 10 hoteles por revenue, top 10 destinos, top 10 países visitantes.<br>**Paso 4:** El usuario puede filtrar por rango de fechas, hotel, destino o canal.<br>**Paso 5:** El sistema actualiza los datos según los filtros seleccionados. |
| **Flujos Alternos** | **FA-01: Sin datos**<br>Si no hay datos cargados, el sistema muestra "No hay datos disponibles. Ejecute el pipeline ETL primero." |
| **Reglas de Negocio** | **RN-O26-01:** La tasa de conversión se calcula como reservas / eventos totales × 100.<br>**RN-O26-02:** El revenue bruto se calcula como suma de price_usd donde reserva_bool = true.<br>**RN-O26-03:** El precio promedio se calcula como AVG(price_usd) sobre todos los eventos. |
| **Entradas** | Filtros opcionales: `fecha_desde`, `fecha_hasta`, `prop_id`, `srch_destination_id`, `site_id` |
| **Salidas** | Dashboard con métricas agregadas, tablas y gráficos. |
| **Postcondiciones** | El usuario visualiza los reportes. No se modifican datos. |
| **Colecciones MongoDB** | `fact_hotel_reservations`, `dim_hotels`, `dim_destinations`, `dim_visitor_countries`, `dim_sites`, `dim_dates` |
| **Endpoints** | `GET /analytics/revenue` — Reporte de revenue HTML.<br>`GET /analytics/conversion` — Reporte de conversión HTML.<br>`GET /analytics/promotions` — Reporte de promociones HTML.<br>`GET /analytics/visitor-markets` — Reporte de mercados HTML.<br>`GET /api/management/reports` — API de reportes. |
| **Código implementado** | `server/src/app/modules/revenue/` — Rutas y servicios (`overview.py`, `markets.py`).<br>`server/src/app/features/dashboard/` — Dashboard general. |

---

## 6.28 CU-O27: Consultar Reporte de Calidad y Registros Rechazados

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O27 |
| **Nombre** | Consultar reporte de calidad y registros rechazados |
| **Objetivo** | Permitir que el auditor de datos consulte los reportes de calidad de cada ejecución ETL, incluyendo total de registros procesados, aceptados, rechazados, completitud de datos y detalle de cada registro rechazado con la razón exacta |
| **Actor Principal** | Auditor de Datos |
| **Actores Secundarios** | Sistema |
| **Disparador** | El auditor necesita verificar la calidad de la última ejecución ETL o investigar registros rechazados |
| **Precondiciones** | 1. Debe existir al menos una ejecución ETL registrada en `etl_executions`.<br>2. Debe existir al menos un reporte de calidad en `data_quality_reports`. |
| **Flujo Principal** | **Paso 1:** El auditor navega a la sección de calidad (`GET /quality` o `GET /api/etl-status/reports`).<br>**Paso 2:** El sistema muestra la lista de ejecuciones ETL con: execution_id, pipeline (TAF01/TA02/GA03), fecha, estado, duración, total registros.<br>**Paso 3:** El auditor selecciona una ejecución para ver su reporte de calidad.<br>**Paso 4:** El sistema muestra: total registros, aceptados, rechazados, completitud por campo, errores encontrados.<br>**Paso 5:** El auditor puede ver el detalle de los registros rechazados con: raw_record, razón del rechazo, campo inválido.<br>**Paso 6:** El sistema también muestra `rejected_records` desde la colección MongoDB. |
| **Flujos Alternos** | **FA-01: Sin ejecuciones recientes**<br>El sistema muestra "No hay ejecuciones ETL registradas". |
| **Reglas de Negocio** | **RN-O27-01:** Cada ejecución ETL debe producir un reporte de calidad en `data_quality_reports` y en `data/reports/` (JSON filesystem).<br>**RN-O27-02:** Ningún registro debe ser descartado silenciosamente — todos los rechazos van a `rejected_records` con la razón exacta. |
| **Entradas** | `execution_id` (opcional, si no se especifica muestra la última ejecución) |
| **Salidas** | Reporte de calidad con métricas detalladas y lista de registros rechazados. |
| **Postcondiciones** | El auditor visualiza el reporte. No se modifican datos. |
| **Colecciones MongoDB** | `data_quality_reports` (lectura), `etl_executions` (lectura), `rejected_records` (lectura), `data/reports/*.json` (filesystem) |
| **Endpoints** | `GET /quality` — Página de calidad HTML.<br>`GET /api/etl-status/reports` — API de reportes.<br>`GET /api/etl-status/execution` — API de estado de ejecución. |
| **Código implementado** | `src/etl/quality.py` — Lógica de calidad.<br>`src/etl/reports.py` — Generación de reportes.<br>`server/src/app/features/quality/` — Frontend de calidad. |

---

## 6.29 CU-O28: Administrar Cuenta, Sesión y Cierre Seguro

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O28 |
| **Nombre** | Administrar cuenta, sesión y cierre seguro |
| **Objetivo** | Permitir que cualquier usuario autenticado cierre su sesión de forma segura (logout) invalidando el token en servidor, consultar el estado de su sesión actual, y gestionar su cuenta |
| **Actor Principal** | Todos los usuarios autenticados |
| **Actores Secundarios** | Sistema |
| **Disparador** | El usuario desea cerrar su sesión o verificar su estado de autenticación |
| **Precondiciones** | 1. El usuario debe tener una sesión activa en `user_sessions`.<br>2. La cookie `hoteldata_session` debe estar presente en la solicitud. |
| **Flujo Principal** | **Paso 1 (Logout):** El usuario hace clic en "Cerrar sesión".<br>**Paso 2:** El sistema recibe la solicitud en `GET /auth/logout`.<br>**Paso 3:** El sistema extrae el token de la cookie `hoteldata_session`.<br>**Paso 4:** El sistema calcula el hash SHA-256 del token y elimina el documento correspondiente de `user_sessions`.<br>**Paso 5:** El sistema elimina la cookie `hoteldata_session` del navegador (Set-Cookie con max-age=0).<br>**Paso 6:** El sistema registra el evento en `user_activity_logs` con tipo "logout".<br>**Paso 7:** El sistema redirige al usuario a la página de login.<br><br>**Paso 1 (Verificar sesión):** El sistema valida la sesión en cada request a ruta protegida usando `require_login()`.<br>**Paso 2:** Si la sesión es válida, el sistema permite el acceso.<br>**Paso 3:** Si la sesión no existe o expiró, el sistema responde HTTP 401 y redirige al login. |
| **Flujos Alternos** | **FA-01: Sesión ya expirada**<br>Si el usuario intenta cerrar sesión pero su sesión ya expiró, el sistema limpia la cookie y redirige al login sin error.<br><br>**FA-02: Sesión inválida**<br>Si el token de la cookie no corresponde a ningún documento en `user_sessions`, el sistema limpia la cookie y redirige al login. |
| **Reglas de Negocio** | **RN-O28-01:** El logout invalida la sesión en el servidor (no solo borra la cookie del lado cliente).<br>**RN-O28-02:** Una sesión expirada (TTL de 8 horas) se limpia automáticamente por MongoDB TTL index.<br>**RN-O28-03:** Si un usuario inicia sesión con una sesión previa activa, la sesión anterior se invalida automáticamente. |
| **Entradas** | Cookie `hoteldata_session` con el token de sesión. |
| **Salidas** | **Logout exitoso:** Cookie eliminada + redirección a `/login`.<br>**Sesión expirada:** HTTP 401 + redirección a `/login`.<br>**Verificación (me):** JSON con `user_id`, `email`, `role`, `display_name`. |
| **Postcondiciones** | 1. `user_sessions` ya no tiene el documento de la sesión (eliminado).<br>2. La cookie del navegador fue eliminada.<br>3. Queda registrado en `user_activity_logs`. |
| **Restricciones** | 1. No confiar en la cookie del lado cliente para validar sesión — siempre verificar en servidor.<br>2. TTL index en `user_sessions.expires_at` para limpieza automática. |
| **Colecciones MongoDB** | `user_sessions` (eliminación), `user_activity_logs` (escritura) |
| **Endpoints** | `GET /auth/logout` — Logout web (HTML).<br>`GET /api/auth/me` — Consultar sesión actual (JSON).<br>`GET /auth/me` — Homepage según rol. |
| **Código implementado** | `server/src/app/modules/auth/routes.py` — Rutas de logout y sesión.<br>`server/src/app/security/session.py` — `invalidate_session()`, `get_session()`. |

---

## 6.30 CU-O29: Cambiar Contraseña y Actualizar Perfil de Usuario

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O29 |
| **Nombre** | Cambiar contraseña y actualizar perfil de usuario |
| **Objetivo** | Permitir que cualquier usuario autenticado cambie su contraseña (verificando la actual), actualice su perfil (display_name, email, teléfono, preferencias), y suba un avatar, registrando toda modificación en auditoría |
| **Actor Principal** | Todos los usuarios autenticados |
| **Actores Secundarios** | Sistema |
| **Disparador** | El usuario desea cambiar su contraseña por seguridad, o actualizar sus datos personales |
| **Precondiciones** | 1. El usuario debe estar autenticado con sesión activa.<br>2. Para cambiar contraseña: debe conocer la contraseña actual. |
| **Flujo Principal (Cambio de contraseña):** | **Paso 1:** El usuario navega a la configuración de su cuenta.<br>**Paso 2:** El usuario ingresa su contraseña actual y la nueva contraseña (dos veces para confirmación).<br>**Paso 3:** El sistema envía los datos a `PUT /api/settings/password`.<br>**Paso 4:** El sistema verifica la contraseña actual con `bcrypt.verify(current_password, user.password_hash)`.<br>**Paso 5:** El sistema valida que la nueva contraseña tenga al menos 8 caracteres y no sea igual a la actual.<br>**Paso 6:** El sistema hashea la nueva contraseña con bcrypt y la almacena en `users.password_hash`.<br>**Paso 7:** El sistema invalida todas las sesiones activas del usuario (excepto la actual) para forzar re-login.<br>**Paso 8:** El sistema registra el cambio en `user_activity_logs`.<br>**Paso 9:** El sistema muestra "Contraseña actualizada exitosamente". |
| **Flujo Principal (Actualizar perfil):** | **Paso 1:** El usuario navega a su perfil.<br>**Paso 2:** El usuario modifica display_name, email, teléfono, dirección, preferencias de viaje.<br>**Paso 3:** El sistema envía los datos a `PUT /api/account/profile`.<br>**Paso 4:** El sistema valida que el email no esté duplicado.<br>**Paso 5:** El sistema actualiza el sub-documento `profile` en `users`.<br>**Paso 6:** El sistema registra el cambio en `user_activity_logs`.<br>**Paso 7:** El sistema muestra "Perfil actualizado exitosamente". |
| **Flujos Alternos** | **FA-01: Contraseña actual incorrecta**<br>Si la contraseña actual no coincide, el sistema responde 400 "Contraseña actual incorrecta".<br><br>**FA-02: Contraseña débil**<br>Si la nueva contraseña tiene menos de 8 caracteres, el sistema responde "La contraseña debe tener al menos 8 caracteres".<br><br>**FA-03: Email duplicado**<br>Si el nuevo email ya está registrado por otro usuario, el sistema responde "El email ya está registrado por otro usuario". |
| **Reglas de Negocio** | **RN-O29-01:** La nueva contraseña debe tener al menos 8 caracteres.<br>**RN-O29-02:** La nueva contraseña no puede ser igual a la actual.<br>**RN-O29-03:** El cambio de contraseña invalida todas las sesiones activas (obliga a re-login).<br>**RN-O29-04:** El email debe ser único en el sistema.<br>**RN-O29-05:** Las contraseñas siempre se almacenan con bcrypt, nunca en texto plano. |
| **Entradas** | **Password:** `current_password`, `new_password`, `confirm_password`.<br>**Perfil:** `display_name`, `email`, `phone`, `address`, `preferencias`.<br>**Avatar:** archivo imagen (JPEG/PNG, máx 2MB). |
| **Salidas** | **Password:** 200 OK + mensaje + invalidación de sesiones.<br>**Perfil:** 200 OK + JSON con perfil actualizado.<br>**Avatar:** 200 OK + URL del avatar. |
| **Postcondiciones** | 1. `users.password_hash` tiene el nuevo hash bcrypt.<br>2. Las sesiones anteriores (excepto la actual) están invalidadas.<br>3. `users.profile` tiene los datos actualizados.<br>4. `user_activity_logs` tiene los registros de cambios. |
| **Restricciones** | 1. Contraseñas almacenadas con bcrypt passlib, nunca texto plano.<br>2. Avatar: máximo 2MB, formatos image/jpeg, image/png.<br>3. No enviar contraseñas en GET o URL params. |
| **Colecciones MongoDB** | `users` (actualización: password_hash, profile), `user_sessions` (eliminación), `user_activity_logs` (escritura) |
| **Endpoints** | `PUT /api/settings/password` — Cambiar contraseña.<br>`GET /api/account/profile` — Obtener perfil.<br>`PUT /api/account/profile` — Actualizar perfil.<br>`POST /api/account/profile/avatar` — Subir avatar.<br>`PUT /api/settings` — Actualizar configuración. |
| **Código implementado** | `server/src/app/modules/settings/routes.py` — Password change.<br>`server/src/app/modules/account/routes.py` — Profile management.<br>`server/src/app/security/session.py` — Invalidación de sesiones. |

---

## 6.31 CU-O30: Gestionar Disponibilidad y Estado de Habitaciones

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O30 |
| **Nombre** | Gestionar disponibilidad y estado de habitaciones |
| **Objetivo** | Unificar en un solo caso de uso la consulta del estado operativo de todas las habitaciones (disponible, ocupada, limpieza, mantenimiento), la consulta de disponibilidad por habitación individual y la asignación de tipo de habitación a una habitación individual, centralizando la gestión del inventario físico del hotel |
| **Actor Principal** | Recepcionista / Gerente de hotel |
| **Actores Secundarios** | Sistema (room_status_log, housekeeping_tasks, room_inventory_calendar) |
| **Disparador** | El recepcionista o gerente necesita conocer el estado de las habitaciones, asignar un nuevo huésped a una habitación específica o verificar disponibilidad individual |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `recepcionista` o `gerente_hotel`.<br>2. El hotel debe tener habitaciones creadas en `hotel_rooms` y `room_types`.<br>3. Debe existir al menos un tipo de habitación configurado para la propiedad. |
| **Flujo Principal** | **Paso 1:** El usuario navega al panel de estado de habitaciones (`GET /partner/hotels/{prop_id}/rooms/status`).<br>**Paso 2:** El sistema muestra un grid/table con todas las habitaciones del hotel, su tipo, estado actual (disponible, ocupada, limpieza, mantenimiento, fuera_de_servicio) y última actualización.<br>**Paso 3:** El usuario puede filtrar por tipo de habitación, estado o rango de fechas.<br>**Paso 4:** El usuario selecciona una habitación específica para ver su detalle o cambiar su estado.<br>**Paso 5:** (Asignación) Si la habitación está disponible, el usuario puede asignar el tipo de habitación a una habitación individual o reasignar a un huésped entrante.<br>**Paso 6:** (Disponibilidad) El sistema muestra el calendario de disponibilidad por habitación individual para las próximas fechas.<br>**Paso 7:** El sistema actualiza `room_status_log` con el nuevo estado o `room_inventory_calendar` si hay cambios de disponibilidad.<br>**Paso 8:** El sistema registra la acción en `user_activity_logs`. |
| **Flujos Alternos** | **FA-01: Habitación en mantenimiento**<br>Si la habitación está en estado "mantenimiento", el sistema muestra el motivo, fecha estimada de finalización y no permite asignación.<br><br>**FA-02: Conflicto de ocupación**<br>Si se intenta asignar una habitación ya ocupada, el sistema muestra "La habitación {número} está actualmente ocupada hasta {fecha}". |
| **Reglas de Negocio** | **RN-O30-01:** Una habitación en estado "mantenimiento" o "limpieza" no puede asignarse a un huésped.<br>**RN-O30-02:** El cambio de estado queda registrado en `room_status_log` con timestamp y usuario responsable.<br>**RN-O30-03:** La disponibilidad por habitación individual se calcula desde `room_inventory_calendar` + `room_status_log`. |
| **Entradas** | `prop_id` (string), `room_id` (string opcional), `room_type_id` (string opcional), `filtro_estado` (string opcional), `fecha_desde`, `fecha_hasta` (dates opcionales) |
| **Salidas** | Grid de estado de habitaciones con: room_id, número, tipo, estado, última actualización, ocupante actual (si aplica), fechas de ocupación.<br>Calendario de disponibilidad por habitación individual. |
| **Postcondiciones** | 1. `room_status_log` tiene los cambios registrados si se modificó algún estado.<br>2. `user_activity_logs` tiene el registro de la consulta/acción.<br>3. El usuario visualiza la información actualizada de disponibilidad y estado. |
| **Restricciones** | 1. El grid de estado se actualiza en tiempo real (polling cada 30s) para reflejar cambios de housekeeping/check-out.<br>2. Solo disponible para roles `recepcionista` y `gerente_hotel`. |
| **Colecciones MongoDB** | `hotel_rooms` (lectura), `room_types` (lectura), `room_status_log` (lectura/escritura), `room_inventory_calendar` (lectura), `booking_orders` (lectura), `housekeeping_tasks` (lectura) |
| **Endpoints** | `GET /partner/hotels/{prop_id}/rooms/status` — Panel de estado HTML.<br>`GET /api/housekeeping/rooms/status?prop_id=X` — API de estado JSON.<br>`PUT /api/housekeeping/rooms/{room_id}/status` — Actualizar estado.<br>`POST /api/management/rooms/{room_id}/assign-room-type` — Asignar tipo de habitación. |
| **Código implementado** | `server/src/app/modules/housekeeping/room_status_service.py` — Servicio de estado.<br>`frontend/src/app/features/housekeeping/room-status/` — RoomStatusPanel. |

---

## 6.32 CU-O31: Gestionar Geolocalización y Metadata de Contenido

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O31 |
| **Nombre** | Gestionar geolocalización y metadata de contenido |
| **Objetivo** | Unificar en un solo caso de uso la edición de metadata de destinos (nombre, coordenadas), la edición de nombre visible de hotel (manual_override), la visualización de mapa mundial interactivo con hoteles geolocalizados y la selección de ubicación de destino en mapa, centralizando toda la gestión geoespacial del catálogo de destinos |
| **Actor Principal** | Auditor de Datos / Marketing hotelero |
| **Actores Secundarios** | Sistema, ETL (respetar manual_override) |
| **Disparador** | El auditor necesita corregir coordenadas de un destino, editar metadata o visualizar el mapa de hoteles. Marketing necesita editar nombres visibles. |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `auditor_datos` o `marketing_hotelero`.<br>2. Deben existir destinos en `dim_hotels.destination` o `destinations_enriched`.<br>3. Se requiere conexión a internet para cargar tiles de mapa (OpenStreetMap vía Leaflet.js). |
| **Flujo Principal** | **Paso 1:** El usuario navega al gestor geoespacial (`GET /geo/destinations`).<br>**Paso 2:** El sistema muestra un mapa mundial interactivo (Leaflet.js) con marcadores de puntos por destino y hoteles asociados.<br>**Paso 3:** El usuario puede hacer clic en un marcador para ver detalle del destino: nombre, país, coordenadas, cantidad de hoteles.<br>**Paso 4:** (Editar metadata) El usuario selecciona "Editar" y modifica: nombre visible del destino, coordenadas (lat, lng), país, ciudad, descripción.<br>**Paso 5:** (Editar nombre hotel) El usuario selecciona un hotel en el mapa o desde el listado y edita su nombre visible, activando `manual_override = true`.<br>**Paso 6:** (Seleccionar ubicación) El usuario hace clic en el mapa para seleccionar una nueva ubicación y arrastra el marcador para ajustar coordenadas.<br>**Paso 7:** El sistema valida los datos y guarda los cambios en las colecciones correspondientes.<br>**Paso 8:** El sistema registra los cambios en `hotel_profile_changes` o `destinations_log` según corresponda.<br>**Paso 9:** El sistema muestra confirmación y actualiza el mapa. |
| **Flujos Alternos** | **FA-01: Sin conexión a internet**<br>Si no hay conexión, el mapa muestra un mensaje "Se requiere conexión a internet para cargar el mapa. Los tiles de OpenStreetMap no están disponibles offline."<br><br>**FA-02: Coordenadas inválidas**<br>Si las coordenadas ingresadas están fuera de rango (lat -90..90, lng -180..180), el sistema rechaza y muestra "Coordenadas inválidas".<br><br>**FA-03: Destino sin coordenadas**<br>Si un destino no tiene coordenadas asignadas, se muestra en el mapa en el centro del país correspondiente (si está disponible) o se omite. |
| **Reglas de Negocio** | **RN-O31-01:** El `prop_id` es la clave técnica inmutable de la propiedad — no puede editarse desde el mapa.<br>**RN-O31-02:** `manual_override` impide que el ETL sobrescriba el nombre editado manualmente.<br>**RN-O31-03:** Las coordenadas (lat, lng) deben ser válidas geográficamente.<br>**RN-O31-04:** Los tiles de mapa se cargan desde `tile.openstreetmap.org` vía internet. No hay modo offline completo.<br>**RN-O31-05:** Todos los cambios de metadata quedan registrados para trazabilidad. |
| **Entradas** | `accion` (editar_metadata/editar_hotel/seleccionar_ubicacion), `destino_id`, `prop_id`, `nombre_visible`, `latitud`, `longitud`, `pais`, `ciudad`, `descripcion`, `hotel_name_override` |
| **Salidas** | Mapa mundial interactivo con marcadores.<br>Formulario de edición de metadata/destino/hotel.<br>Confirmación de cambios guardados. |
| **Postcondiciones** | 1. `destinations_enriched` o `dim_hotels` tienen la metadata actualizada.<br>2. `hotel_profile_changes` o `destinations_log` registran los cambios.<br>3. El mapa refleja los cambios inmediatamente. |
| **Restricciones** | 1. Se requiere internet para cargar tiles del mapa.<br>2. Los tiles de Leaflet.js se cargan desde CDN. Si no hay internet, el mapa no se renderiza.<br>3. `manual_override` no puede desactivarse una vez activado (solo por super admin directo en BD). |
| **Colecciones MongoDB** | `dim_hotels` (lectura/actualización), `destinations_enriched` (lectura/escritura), `hotel_profile_changes` (escritura), `hotel_content_pages` (lectura), `user_activity_logs` (escritura), `hotel_locations_geo` (lectura) |
| **Endpoints** | `GET /geo/destinations` — Gestor geoespacial HTML.<br>`GET /api/geo/destinations` — API de destinos geo.<br>`PUT /api/geo/destinations/{destino_id}` — Actualizar metadata.<br>`PUT /api/management/properties/{prop_id}/profile` — Editar nombre hotel (override).<br>`GET /api/geo/destinations/{destino_id}/map` — Datos para mapa. |
| **Código implementado** | `server/src/app/modules/geo/` — Rutas y servicios geoespaciales.<br>`frontend/src/app/features/geo/` — DestinationMapComponent, DestinationEditor. |

---

## 6.33 CU-O32: Gestionar Notificaciones Transaccionales al Huésped

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O32 |
| **Nombre** | Gestionar notificaciones transaccionales al huésped |
| **Objetivo** | Permitir que el sistema envíe notificaciones automáticas al huésped durante el ciclo de vida de su reserva: confirmación de reserva, recordatorio de check-in, factura post-estancia, cambios de estado y ofertas personalizadas, a través de múltiples canales (email, SMS, push) |
| **Actor Principal** | Sistema (automático). Configurado por Super Admin / Marketing |
| **Actores Secundarios** | Proveedores externos (email/SMS/push), Motor de plantillas |
| **Disparador** | Eventos del ciclo de vida de la reserva: creación, confirmación, check-in, check-out, cancelación, recordatorio programado |
| **Precondiciones** | 1. Debe existir una reserva activa en `booking_orders` con datos de contacto del huésped.<br>2. Deben existir plantillas de notificación configuradas en `notification_templates`.<br>3. El canal de envío (email/SMS/push) debe estar configurado en las preferencias del huésped. |
| **Flujo Principal** | **Paso 1:** Un evento del sistema dispara una notificación (ej: reserva creada → notificación de confirmación).<br>**Paso 2:** El sistema consulta `notification_templates` para obtener la plantilla correspondiente al evento y canal.<br>**Paso 3:** El sistema personaliza la plantilla con datos de la reserva: nombre del huésped, hotel, fechas, monto, etc.<br>**Paso 4:** El sistema verifica las preferencias del huésped en `notification_preferences` (qué canales tiene habilitados).<br>**Paso 5:** El sistema envía la notificación por el/los canales habilitados (email, SMS, push).<br>**Paso 6:** El sistema registra el envío en `notification_logs` con: timestamp, tipo, canal, destinatario, estado (enviado/fallido), event_id de referencia.<br>**Paso 7:** Si el envío falla, el sistema reintenta hasta 3 veces con backoff exponencial. |
| **Flujos Alternos** | **FA-01: Canal no configurado**<br>Si el canal seleccionado no está configurado (ej: no hay API key de SMS), el sistema omite ese canal y registra "canal_no_disponible".<br><br>**FA-02: Huésped sin preferencias**<br>Si el huésped no tiene preferencias configuradas, el sistema envía por email (canal por defecto).<br><br>**FA-03: Falla de envío después de reintentos**<br>Después de 3 reintentos fallidos, el sistema registra "fallo_permanente" y notifica al administrador. |
| **Reglas de Negocio** | **RN-O32-01:** Las notificaciones transaccionales son obligatorias (confirmación, recordatorio, factura) — el huésped no puede desactivarlas.<br>**RN-O32-02:** Las notificaciones promocionales (ofertas, upgrades) requieren opt-in explícito del huésped.<br>**RN-O32-03:** Los reintentos de envío usan backoff exponencial: 1 min, 5 min, 30 min.<br>**RN-O32-04:** Todas las notificaciones quedan registradas en `notification_logs` para auditoría. |
| **Entradas** | Generadas por eventos del sistema: `event_type` (booking_confirmed, checkin_reminder, checkout_bill, etc.), `booking_id`, `guest_email`, `guest_phone`, `guest_push_token` |
| **Salidas** | Notificación enviada al huésped por el/los canales configurados.<br>Registro en `notification_logs` con estado del envío. |
| **Postcondiciones** | 1. `notification_logs` tiene el registro del envío con estado, timestamp, canal y destinatario.<br>2. El huésped recibe la notificación en el/los canales configurados.<br>3. Si falló, queda registrado para diagnóstico. |
| **Restricciones** | 1. Depende de proveedores externos (email: SMTP/SendGrid, SMS: Twilio, Push: Firebase).<br>2. No se envían notificaciones en horas de silencio (23:00-07:00) a menos que sean transaccionales críticas.<br>3. Máximo 5 notificaciones promocionales por huésped por semana. |
| **Colecciones MongoDB** | `notification_templates` (lectura), `notification_logs` (escritura), `notification_preferences` (lectura), `booking_orders` (lectura), `booking_guests` (lectura) |
| **Endpoints** | `POST /api/notifications/send` — Enviar notificación (interno, llamado por eventos del sistema).<br>`GET /api/notifications/logs` — Consultar logs de notificaciones (admin).<br>`GET /api/notifications/preferences` — Consultar preferencias (cliente).<br>`PUT /api/notifications/preferences` — Actualizar preferencias (cliente). |
| **Código implementado** | `server/src/app/modules/notifications/` — Servicios de envío (`email_service.py`, `sms_service.py`, `push_service.py`), `notification_orchestrator.py`. |

---

## 6.34 CU-O33: Gestionar Alertas Operativas Internas al Staff

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O33 |
| **Nombre** | Gestionar alertas operativas internas al staff |
| **Objetivo** | Permitir que el sistema genere y gestione alertas operativas dirigidas al personal interno del hotel (housekeeping, mantenimiento, recepción) basadas en eventos de la operación diaria: check-out completado (limpieza requerida), incidencia reportada, ocupación crítica, mantenimiento programado, cargos adicionales pendientes |
| **Actor Principal** | Sistema (generación automática). Recepcionista / Housekeeping / Mantenimiento (destinatarios) |
| **Actores Secundarios** | Gerente de hotel (supervisión) |
| **Disparador** | Eventos operativos: check-out completado, reporte de avería en habitación, ocupación supera umbral, tarea de mantenimiento programada, hora de limpieza programada |
| **Precondiciones** | 1. Debe existir personal asignado en el hotel (usuarios con roles housekeeping, mantenimiento, recepción).<br>2. Debe existir al menos un tipo de alerta definido en el sistema.<br>3. Las habitaciones deben estar registradas en `hotel_rooms`. |
| **Flujo Principal** | **Paso 1:** Un evento operativo dispara una alerta (ej: check-out completado en habitación 205 → alerta de limpieza).<br>**Paso 2:** El sistema determina el tipo de alerta: limpieza, mantenimiento, ocupación, incidencia, cargo_pendiente.<br>**Paso 3:** El sistema identifica el personal destinatario según el tipo de alerta y disponibilidad.<br>**Paso 4:** El sistema crea la alerta en `notifications_queue` con: tipo, prioridad (alta/media/baja), destino (rol/usuario específico), mensaje, habitación asociada, timestamp.<br>**Paso 5:** El personal recibe la alerta en su panel de notificaciones internas (frontend Angular).<br>**Paso 6:** El destinatario puede marcar la alerta como "vista", "en_proceso" o "resuelta".<br>**Paso 7:** Si la alerta no se resuelve en el tiempo definido (ej: limpieza en 60 min), el sistema escala al gerente de hotel. |
| **Flujos Alternos** | **FA-01: Sin personal disponible**<br>Si no hay personal del rol requerido disponible, el sistema asigna la alerta al gerente de hotel directamente.<br><br>**FA-02: Alerta de alta prioridad**<br>Si la alerta es de alta prioridad (ej: incidencia de seguridad), se muestra con notificación push y sonido en el frontend. |
| **Reglas de Negocio** | **RN-O33-01:** Las alertas de limpieza se generan automáticamente al completar un check-out (CU-O11).<br>**RN-O33-02:** Las alertas de mantenimiento se generan al reportar una incidencia o al llegar la fecha programada de mantenimiento preventivo.<br>**RN-O33-03:** Las alertas no resueltas escalan al gerente después del tiempo límite.<br>**RN-O33-04:** Una alerta puede reasignarse manualmente a otro miembro del staff. |
| **Entradas** | Generadas por eventos del sistema: `event_type` (checkout_completed, incident_reported, maintenance_due, occupancy_critical), `room_id`, `prop_id`, `descripcion`, `prioridad` |
| **Salidas** | Alerta visible en el panel de notificaciones internas del personal destinatario.<br>Registro en `notification_logs` con estado de la alerta. |
| **Postcondiciones** | 1. `notification_queue` tiene la alerta registrada con prioridad y asignación.<br>2. El personal recibe la notificación en su panel.<br>3. Queda registrado en `notification_logs` para auditoría operativa. |
| **Restricciones** | 1. Las alertas operativas son internas — no se envían al huésped.<br>2. Las alertas de alta prioridad no pueden ignorarse (deben marcarse como "vistas").<br>3. El tiempo de resolución por tipo de alerta se configura en `system_catalogs` (limpieza: 60 min, mantenimiento urgente: 120 min). |
| **Colecciones MongoDB** | `notification_queue` (escritura), `notification_logs` (escritura), `hotel_rooms` (lectura), `housekeeping_tasks` (lectura/escritura), `maintenance_tasks` (lectura), `booking_orders` (lectura), `users` (lectura, para asignación) |
| **Endpoints** | `GET /api/notifications/alerts` — Panel de alertas internas.<br>`PUT /api/notifications/alerts/{alert_id}/status` — Actualizar estado (vista/en_proceso/resuelta).<br>`POST /api/notifications/alerts/{alert_id}/reassign` — Reasignar alerta. |
| **Código implementado** | `server/src/app/modules/notifications/` — `alert_service.py` (generación y gestión de alertas), `scaling_rules.py` (escalamiento).<br>`frontend/src/app/features/notifications/` — InternalAlertsPanel. |

---

## 6.35 CU-O34: Gestionar Campañas Promocionales Multicanal

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O34 |
| **Nombre** | Gestionar campañas promocionales multicanal |
| **Objetivo** | Permitir que marketing lance campañas promocionales segmentadas a través de múltiples canales (email, SMS, push) dirigidas a huéspedes según criterios de segmentación: historial de reservas, destino favorito, temporada, valor de reserva, y medir la efectividad de cada campaña en términos de conversión y revenue generado |
| **Actor Principal** | Marketing hotelero / Revenue manager |
| **Actores Secundarios** | Sistema (segmentación, envío, medición), Proveedores externos (email/SMS/push) |
| **Disparador** | El equipo de marketing necesita lanzar una campaña promocional para incentivar reservas en temporada baja o promocionar un nuevo hotel/destino |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `marketing_hotelero` o `revenue_manager`.<br>2. Debe existir al menos una plantilla de notificación configurada en `notification_templates`.<br>3. Debe existir al menos una promoción activa en `promotion_campaigns` o se creará una nueva. |
| **Flujo Principal** | **Paso 1:** El usuario navega al gestor de campañas (`GET /marketing/campaigns`).<br>**Paso 2:** El usuario hace clic en "Nueva campaña" y define: nombre, descripción, tipo (email/SMS/push/multicanal), segmento objetivo (huéspedes frecuentes, clientes de un destino específico, reservas de alto valor, etc.), fechas de envío, promoción asociada (cupón/código de descuento).<br>**Paso 3:** El sistema calcula el tamaño del segmento y muestra una previsualización de la campaña.<br>**Paso 4:** El usuario programa la campaña (inmediata o diferida) y la lanza.<br>**Paso 5:** El sistema ejecuta la campaña: para cada huésped en el segmento, envía la notificación por el/los canales seleccionados usando las plantillas configuradas.<br>**Paso 6:** El sistema registra cada envío en `notification_logs` con campaign_id, huésped, canal, estado.<br>**Paso 7:** El sistema muestra métricas en tiempo real: enviados, abiertos, clickeados, convertidos (reservas con el cupón), revenue generado. |
| **Flujos Alternos** | **FA-01: Segmento vacío**<br>Si el segmento seleccionado no tiene huéspedes, el sistema advierte "El segmento seleccionado no contiene huéspedes. Ajuste los criterios."<br><br>**FA-02: Campaña cancelada**<br>El usuario puede cancelar una campaña programada antes de su ejecución. Las campañas en ejecución no pueden cancelarse. |
| **Reglas de Negocio** | **RN-O34-01:** Los huéspedes deben tener opt-in habilitado para notificaciones promocionales.<br>**RN-O34-02:** Máximo 5 campañas promocionales por huésped por semana.<br>**RN-O34-03:** Las campañas miden efectividad por: tasa de apertura, CTR, tasa de conversión, revenue generado vs costo de envío.<br>**RN-O34-04:** El segmento se calcula al momento del envío (no al momento de creación) para garantizar datos actualizados. |
| **Entradas** | `nombre`, `descripcion`, `tipo` (email/sms/push/multicanal), `segmento` (criterios: frecuencia_reservas, destino, valor_reserva, fecha_ultima_reserva), `plantilla_id`, `promocion_id`, `fecha_programada` |
| **Salidas** | Campaña creada y programada.<br>Métricas en tiempo real de ejecución: enviados, abiertos, clicks, conversiones, revenue. |
| **Postcondiciones** | 1. `marketing_campaigns` tiene la campaña registrada con su configuración.<br>2. `notification_logs` tiene los registros de cada envío.<br>3. Las métricas de efectividad están disponibles en el dashboard de campañas. |
| **Restricciones** | 1. Cada campaña tiene un costo por envío (email: ~$0.001, SMS: ~$0.05, según proveedor).<br>2. No se pueden enviar campañas masivas en horas nocturnas (23:00-07:00). |
| **Colecciones MongoDB** | `marketing_campaigns` (escritura), `campaign_segments` (escritura), `notification_templates` (lectura), `notification_logs` (escritura), `promotion_campaigns` (lectura), `booking_orders` (lectura, para segmentación), `users` (lectura) |
| **Endpoints** | `GET /marketing/campaigns` — Gestor de campañas HTML.<br>`POST /api/marketing/campaigns` — Crear campaña.<br>`PUT /api/marketing/campaigns/{id}/launch` — Lanzar campaña.<br>`PUT /api/marketing/campaigns/{id}/cancel` — Cancelar campaña.<br>`GET /api/marketing/campaigns/{id}/metrics` — Métricas de campaña. |
| **Código implementado** | `server/src/app/modules/marketing/` — `campaign_service.py`, `segmentation_service.py`, `campaign_metrics.py`.<br>`frontend/src/app/features/marketing/` — CampaignManager, CampaignMetrics. |

---

## 6.36 CU-O35: Atender Cliente Mediante Asistente Virtual (Chatbot IA)

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O35 |
| **Nombre** | Atender cliente mediante asistente virtual (chatbot IA) |
| **Objetivo** | Proporcionar un asistente virtual conversacional (chatbot con IA) que atienda consultas de clientes sobre hoteles, reservas, check-in/out, servicios del hotel, actividades locales y preguntas frecuentes, con capacidad de escalar a un agente humano cuando sea necesario |
| **Actor Principal** | Cliente |
| **Actores Secundarios** | Sistema (motor de chatbot IA), Recepcionista (escalamiento humano) |
| **Disparador** | El cliente inicia una conversación desde el widget de chat en la página de búsqueda, detalle de hotel, o desde su panel de reservas |
| **Precondiciones** | 1. El sistema debe tener una base de conocimiento configurada en `chatbot_knowledge_base`.<br>2. El motor de chatbot (integración con API de IA) debe estar operativo.<br>3. Para consultas sobre reservas específicas, el cliente debe estar autenticado. |
| **Flujo Principal** | **Paso 1:** El cliente abre el widget de chat desde cualquier página del frontend.<br>**Paso 2:** El chatbot saluda y pregunta cómo puede ayudar.<br>**Paso 3:** El cliente escribe su consulta en lenguaje natural (ej: "¿Tienen habitaciones disponibles para el fin de semana?" o "¿Cuál es la política de cancelación?").<br>**Paso 4:** El sistema procesa la consulta: busca en la base de conocimiento (`chatbot_knowledge_base`), consulta disponibilidad real si es necesario, y genera una respuesta en lenguaje natural.<br>**Paso 5:** El chatbot muestra la respuesta al cliente con opciones de seguimiento (botones rápidos).<br>**Paso 6:** El cliente puede continuar la conversación o finalizar.<br>**Paso 7:** Si el chatbot no puede resolver la consulta o el cliente solicita hablar con un humano, el sistema escala la conversación a un recepcionista disponible.<br>**Paso 8:** La conversación queda registrada en `chatbot_conversations` para análisis de calidad. |
| **Flujos Alternos** | **FA-01: Consulta no resuelta**<br>Si el chatbot no encuentra respuesta en su base de conocimiento (confianza < 0.7), responde "No estoy seguro de poder responder eso. ¿Quieres que te conecte con un agente humano?" y ofrece escalar.<br><br>**FA-02: Escalamiento a humano**<br>Cuando se escala, el sistema asigna la conversación al recepcionista menos ocupado y le muestra el historial completo del chat.<br><br>**FA-03: Fuera de horario**<br>Si no hay recepcionistas disponibles (horario nocturno), el chatbot recoge los datos y agenda un follow-up para el día siguiente. |
| **Reglas de Negocio** | **RN-O35-01:** El chatbot debe presentarse como asistente virtual y nunca como humano.<br>**RN-O35-02:** Las consultas sobre datos sensibles (datos de tarjeta de crédito) no deben responderse — el chatbot deriva a métodos seguros.<br>**RN-O35-03:** El historial de conversaciones se almacena por 90 días para mejora continua.<br>**RN-O35-04:** El chatbot puede realizar reservas simples (misma capacidad que CU-O05) si el cliente está autenticado. |
| **Entradas** | `mensaje` (texto libre en lenguaje natural), `contexto` (página actual, hotel/booking_id si aplica), `user_id` (si autenticado) |
| **Salidas** | Respuesta en lenguaje natural del chatbot.<br>Opcional: escalamiento a recepcionista humano con historial de conversación. |
| **Postcondiciones** | 1. `chatbot_conversations` tiene el registro de la conversación.<br>2. Si se escaló, el recepcionista tiene la conversación asignada.<br>3. Si se realizó una reserva, `booking_orders` tiene el registro. |
| **Restricciones** | 1. Depende de API de IA externa para procesamiento de lenguaje natural.<br>2. El chatbot no puede procesar pagos ni datos sensibles.<br>3. Límite de 1000 consultas/día en el plan gratuito de la API de IA. |
| **Colecciones MongoDB** | `chatbot_knowledge_base` (lectura), `chatbot_conversations` (escritura), `booking_orders` (lectura/escritura para reservas simples), `hotels` (lectura), `hotel_policies` (lectura), `room_inventory_calendar` (lectura) |
| **Endpoints** | `POST /api/chatbot/message` — Enviar mensaje al chatbot.<br>`GET /api/chatbot/conversations` — Historial de conversaciones (admin).<br>`POST /api/chatbot/escalate` — Escalar a humano. |
| **Código implementado** | `server/src/app/modules/chatbot/` — `chatbot_engine.py` (procesamiento), `knowledge_base.py`, `conversation_service.py`.<br>`frontend/src/app/features/chatbot/` — ChatWidget, ChatConversation. |

---

## 6.37 CU-O36: Gestionar Up-Selling y Ancillaries Durante la Estancia

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O36 |
| **Nombre** | Gestionar up-selling y ancillaries durante la estancia |
| **Objetivo** | Permitir que el recepcionista o revenue manager ofrezca y gestione servicios adicionales durante la estancia del huésped: upgrade de habitación, late check-out, early check-in, servicios de spa, cenas, traslados, y otros ancillaries, generando ingresos adicionales por huésped |
| **Actor Principal** | Recepcionista / Revenue manager |
| **Actores Secundarios** | Sistema, Huésped (acepta/rechaza ofertas) |
| **Disparador** | Durante el check-in, check-out, o durante la estancia, el recepcionista identifica oportunidades de up-selling basadas en disponibilidad y perfil del huésped |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `recepcionista` o `revenue_manager`.<br>2. Debe existir una reserva activa (estado "confirmed" o "checked_in").<br>3. Debe haber disponibilidad para el servicio ofrecido (habitación superior disponible, horario de late check-out disponible, etc.). |
| **Flujo Principal** | **Paso 1:** El recepcionista abre el perfil de la reserva del huésped durante el check-in, estancia o check-out.<br>**Paso 2:** El sistema muestra oportunidades de up-selling basadas en: disponibilidad actual, perfil del huésped (historial de compras anteriores, segmento), temporada.<br>**Paso 3:** El recepcionista selecciona una oferta (ej: "Upgrade a Suite Ejecutiva por $50/noche") y la presenta al huésped.<br>**Paso 4:** Si el huésped acepta, el recepcionista confirma el up-selling en el sistema.<br>**Paso 5:** El sistema crea el cargo adicional en `additional_charges` asociado a la reserva con: tipo, descripción, monto, fecha.<br>**Paso 6:** El sistema actualiza `booking_orders.total` sumando el monto del up-selling.<br>**Paso 7:** Para upgrades de habitación, el sistema actualiza el room_type asignado y el inventario correspondiente.<br>**Paso 8:** El sistema registra el up-selling en `upselling_log` para análisis de revenue.<br>**Paso 9:** El sistema muestra confirmación con el nuevo total de la reserva. |
| **Flujos Alternos** | **FA-01: Huésped rechaza**<br>Si el huésped rechaza la oferta, el recepcionista marca como "rechazada" y el sistema registra la oportunidad perdida para análisis.<br><br>**FA-02: Sin disponibilidad para upgrade**<br>Si no hay habitaciones del tipo superior disponibles, el sistema no muestra opciones de upgrade de habitación pero sí otros ancillaries (spa, cena, traslados). |
| **Reglas de Negocio** | **RN-O36-01:** El up-selling no debe interferir con la experiencia del huésped — máximo 2 ofertas por interacción.<br>**RN-O36-02:** Los upgrades de habitación solo son posibles si hay disponibilidad en la categoría superior.<br>**RN-O36-03:** Late check-out tiene un costo fijo configurable por hotel (ej: $30 hasta las 18:00).<br>**RN-O36-04:** Todos los ancillaries quedan registrados en `additional_charges` para facturación.<br>**RN-O36-05:** Las ofertas se recomiendan basadas en segmento del huésped (frecuente, alto valor, etc.). |
| **Entradas** | `booking_id`, `tipo_upgrade` (room_upgrade, late_checkout, early_checkin, spa, dinner, transport, other), `descripcion`, `monto`, `room_type_id` (si aplica) |
| **Salidas** | Confirmación de up-selling/ancillary registrado.<br>Nuevo total de la reserva actualizado.<br>Si aplica: habitación actualizada al nuevo tipo. |
| **Postcondiciones** | 1. `additional_charges` tiene el cargo registrado.<br>2. `booking_orders.total` refleja el nuevo monto.<br>3. `upselling_log` tiene el registro para analítica.<br>4. Si fue upgrade: `booking_orders.room_type_id` actualizado + inventario ajustado. |
| **Restricciones** | 1. Late check-out no puede exceder las 20:00 horas (límite operativo para limpieza).<br>2. Early check-in solo disponible si la habitación está disponible desde las 06:00.<br>3. Los ancillaries no son reembolsables (política del sistema). |
| **Colecciones MongoDB** | `additional_charges` (escritura), `booking_orders` (actualización), `upselling_log` (escritura), `room_inventory_calendar` (lectura/actualización para upgrades), `hotel_rooms` (lectura), `system_catalogs` (lectura, para precios de ancillaries) |
| **Endpoints** | `POST /api/upselling/offer` — Registrar up-selling/ancillary.<br>`GET /api/upselling/opportunities/{booking_id}` — Obtener oportunidades de up-selling.<br>`GET /api/upselling/metrics` — Reporte de ingresos por up-selling. |
| **Código implementado** | `server/src/app/modules/revenue/upselling/` — `upselling_service.py`, `opportunity_engine.py`.<br>`frontend/src/app/features/upselling/` — UpsellingPanel, AncillarySelector. |

---

## 6.38 CU-O37: Gestionar Contenidos Multimedia con Geolocalización

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-O37 |
| **Nombre** | Gestionar contenidos multimedia con geolocalización |
| **Objetivo** | Permitir que marketing hotelero gestione contenidos multimedia (fotos, videos, tours virtuales) asociados a coordenadas geográficas específicas, enriqueciendo la presentación de hoteles y destinos con material visual geolocalizado para mejorar la experiencia de búsqueda del cliente |
| **Actor Principal** | Marketing hotelero |
| **Actores Secundarios** | Sistema, Almacenamiento MongoDB GridFS |
| **Disparador** | El equipo de marketing necesita subir, geolocalizar o actualizar contenido multimedia de un hotel o destino |
| **Precondiciones** | 1. El usuario debe estar autenticado con rol `marketing_hotelero`.<br>2. El hotel o destino debe existir en la base de datos.<br>3. El archivo multimedia debe cumplir con los formatos y tamaños permitidos. |
| **Flujo Principal** | **Paso 1:** El usuario navega al gestor multimedia del hotel/destino (`GET /partner/hotels/{prop_id}/multimedia` o `GET /geo/destinations/{destino_id}/multimedia`).<br>**Paso 2:** El sistema muestra el contenido multimedia existente con: tipo (foto/video/tour), previsualización, coordenadas asociadas, estado (activo/inactivo).<br>**Paso 3:** El usuario hace clic en "Subir nuevo" y selecciona el archivo.<br>**Paso 4:** El sistema muestra un mapa interactivo para geolocalizar el contenido: el usuario arrastra un marcador a la ubicación exacta (ej: foto de la piscina → coordenadas de la piscina).<br>**Paso 5:** El usuario completa los metadatos: título, descripción, tipo de contenido (habitación, lobby, piscina, restaurante, exterior, destino), tags.<br>**Paso 6:** El usuario guarda el contenido.<br>**Paso 7:** El sistema almacena el archivo en MongoDB GridFS y crea el registro en `hotel_multimedia` con: prop_id, tipo, coordenadas, metadata, estado, URL de acceso.<br>**Paso 8:** El sistema muestra confirmación y actualiza la galería. |
| **Flujos Alternos** | **FA-01: Archivo muy grande**<br>Si el archivo excede 50MB (video) o 20MB (foto), el sistema rechaza con "El archivo excede el tamaño máximo permitido".<br><br>**FA-02: Formato no soportado**<br>Si el formato no es JPEG, PNG, WebP (fotos) o MP4, WebM (videos), el sistema rechaza con "Formato no soportado". |
| **Reglas de Negocio** | **RN-O37-01:** Los formatos permitidos son: JPEG, PNG, WebP (fotos hasta 20MB), MP4, WebM (videos hasta 50MB).<br>**RN-O37-02:** Las coordenadas de geolocalización son opcionales para contenido general, obligatorias para contenido de ubicaciones específicas.<br>**RN-O37-03:** El contenido multimedia puede marcarse como "principal" (aparece en la portada del hotel).<br>**RN-O37-04:** El contenido multimedia puede desactivarse (oculto) sin eliminarse. |
| **Entradas** | `prop_id` o `destino_id`, `archivo` (file), `titulo`, `descripcion`, `tipo_contenido` (habitacion/lobby/piscina/restaurante/exterior/destino/other), `latitud`, `longitud`, `tags[]`, `es_principal` (boolean) |
| **Salidas** | Contenido multimedia subido y geolocalizado.<br>Confirmación con URL de acceso. |
| **Postcondiciones** | 1. `hotel_multimedia` tiene el nuevo registro con archivo en GridFS.<br>2. El contenido es visible en la galería del hotel/destino.<br>3. Si tiene coordenadas, aparece en el mapa interactivo. |
| **Restricciones** | 1. Los archivos se almacenan en MongoDB GridFS (no en disco ni CDN externo).<br>2. Los videos se transcodifican automáticamente a formato compatible con navegadores.<br>3. Máximo 100 archivos multimedia por hotel. |
| **Colecciones MongoDB** | `hotel_multimedia` (escritura), `fs.files` + `fs.chunks` (GridFS, escritura), `destinations_enriched` (lectura/actualización si se asocia a destino), `hotel_content_pages` (actualización) |
| **Endpoints** | `GET /partner/hotels/{prop_id}/multimedia` — Gestor multimedia HTML.<br>`POST /api/management/properties/{prop_id}/multimedia` — Subir archivo.<br>`PUT /api/management/properties/{prop_id}/multimedia/{media_id}` — Actualizar metadata.<br>`DELETE /api/management/properties/{prop_id}/multimedia/{media_id}` — Desactivar/eliminar.<br>`GET /api/management/properties/{prop_id}/multimedia` — Listar multimedia JSON. |
| **Código implementado** | `server/src/app/modules/partner/services/content/multimedia.py` — Servicio multimedia.<br>`server/src/app/modules/partner/routes/content.py` — Rutas de contenido.<br>`frontend/src/app/features/multimedia/` — MultimediaGallery, MapGeolocationPicker. |

---

## 6.42 CU-T14: Gestionar Rotación y Limpieza de Habitaciones (Táctico)

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-T14 |
| **Nombre** | Gestionar rotación y limpieza de habitaciones |
| **Nivel** | Táctico |
| **Objetivo** | Optimizar el tiempo de rotación de habitaciones entre check-out y check-in, estableciendo métricas objetivo de eficiencia de limpieza, asignación de personal y reducción de tiempos muertos |
| **Actor Principal** | Gerente de hotel |
| **Disparador** | Reporte mensual de eficiencia de rotación muestra tiempos por encima del objetivo |
| **Precondiciones** | 1. Usuario autenticado con rol hotel_manager. 2. Datos históricos de rotación disponibles en room_status_log y housekeeping_tasks. |
| **Flujo Principal** | Paso 1: El gerente navega a `GET /management/rotation-report`. Paso 2: El sistema agrega tiempos de rotación por día, semana y mes. Paso 3: El sistema calcula tiempo promedio de rotación (check-out → disponible). Paso 4: El sistema identifica cuellos de botella (horas pico, personal insuficiente). Paso 5: El gerente establece tiempo objetivo de rotación (ej. 4 horas máximo). Paso 6: El gerente ajusta turnos de limpieza según los datos. |
| **Reglas de Negocio** | RN-T14-01: El tiempo de rotación se mide desde check-out hasta disponible. RN-T14-02: El objetivo por defecto es 4 horas para hoteles urbanos, 6 horas para resorts. |
| **Colecciones MongoDB** | `room_status_log`, `housekeeping_tasks`, `booking_orders` |
| **Endpoints** | `GET /api/management/rotation-report` |
| **Código implementado** | `server/src/app/modules/management/reports/rotation.py` |

---

## 6.43 CU-T15: Programar Mantenimiento Preventivo Proactivo (Táctico)

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-T15 |
| **Nombre** | Programar mantenimiento preventivo proactivo |
| **Nivel** | Táctico |
| **Objetivo** | Establecer un plan de mantenimiento preventivo recurrente basado en histórico, estacionalidad y uso de habitaciones, minimizando interrupciones operativas |
| **Actor Principal** | Gerente de hotel |
| **Disparador** | Inicio de temporada baja o revisión trimestral de plan de mantenimiento |
| **Precondiciones** | 1. Usuario autenticado con rol hotel_manager. 2. Historial de mantenimientos previos en maintenance_tasks. |
| **Flujo Principal** | Paso 1: El gerente navega a planificación de mantenimiento. Paso 2: El sistema sugiere mantenimientos basados en: última fecha por tipo, frecuencia recomendada, ocupación histórica. Paso 3: El gerente revisa y ajusta el plan. Paso 4: El gerente programa lotes de mantenimiento para fechas de baja ocupación. Paso 5: El sistema crea tareas en maintenance_schedule para el período. |
| **Reglas de Negocio** | RN-T15-01: Mantenimiento eléctrico cada 6 meses. RN-T15-02: Mantenimiento HVAC cada 3 meses. RN-T15-03: Pintura general cada 12 meses. |
| **Colecciones MongoDB** | `maintenance_schedule`, `maintenance_tasks`, `hotel_rooms` |
| **Endpoints** | `POST /api/management/maintenance-plan` |
| **Código implementado** | `server/src/app/modules/management/planning/maintenance_plan.py` |

---

## 6.44 CU-E09: Monitorear Eficiencia Operativa del Hotel (Estratégico)

| Elemento | Detalle |
|----------|---------|
| **Código** | CU-E09 |
| **Nombre** | Monitorear eficiencia operativa del hotel |
| **Nivel** | Estratégico |
| **Objetivo** | Proporcionar a la gerencia general y super admin una visión consolidada de la eficiencia operativa del hotel: tiempo de rotación, cumplimiento de limpieza, cumplimiento de mantenimiento, ocupación real vs disponible, cargos adicionales por reserva |
| **Actor Principal** | Gerente general / Super Admin |
| **Disparador** | Necesidad de evaluar el rendimiento operativo del hotel a nivel estratégico |
| **Precondiciones** | 1. Usuario autenticado con rol super_admin. 2. Datos operativos disponibles en colecciones de housekeeping y mantenimiento. |
| **Flujo Principal** | Paso 1: El usuario navega al dashboard de eficiencia operativa. Paso 2: El sistema consulta KPIs de todas las fuentes. Paso 3: El sistema muestra tarjetas de KPI: tiempo promedio de rotación, tasa de cumplimiento de limpieza, % de mantenimiento al día, ocupación real vs teórica, cargos adicionales promedio. Paso 4: El usuario puede filtrar por hotel, fecha y comparar períodos. Paso 5: El sistema permite exportar reporte ejecutivo. |
| **Reglas de Negocio** | RN-E09-01: Los KPIs se calculan con datos de los últimos 30 días por defecto. RN-E09-02: Tiempo de rotación objetivo: < 4 horas. RN-E09-03: Cumplimiento de limpieza objetivo: > 95%. |
| **Colecciones MongoDB** | `room_status_log`, `housekeeping_tasks`, `maintenance_schedule`, `maintenance_tasks`, `additional_charges`, `booking_orders` |
| **Endpoints** | `GET /api/management/efficiency-dashboard` |
| **Código implementado** | `server/src/app/modules/management/dashboards/efficiency.py` |

---

# 7. HISTORIAS DE USUARIO — GHERKIN

## 7.1 CU-O01: Iniciar Sesión con Autenticación JWT y Rol

```gherkin
Feature: Inicio de sesión con JWT
  Como usuario registrado del sistema HotelData
  Quiero iniciar sesión con mi email y contraseña
  Para acceder a las funcionalidades según mi rol asignado

  Background:
    Given el usuario existe en la colección "users" con email "cliente@hoteldata.com"
    And su cuenta está activa (is_active = true)
    And su contraseña está almacenada con hash bcrypt

  Scenario: Inicio de sesión exitoso
    When el usuario ingresa email "cliente@hoteldata.com" y contraseña "Password123"
    And hace clic en "Iniciar sesión"
    Then el sistema verifica las credenciales contra la colección "users"
    And el sistema genera un token de sesión de 48 bytes
    And el sistema almacena el hash del token en "user_sessions"
    And el sistema establece la cookie "hoteldata_session" con flags httponly y samesite=lax
    And el sistema redirige al usuario a su homepage según su rol
    And el sistema registra el evento en "user_activity_logs" con tipo "login"

  Scenario: Credenciales inválidas
    When el usuario ingresa email "cliente@hoteldata.com" y contraseña "WrongPassword"
    And hace clic en "Iniciar sesión"
    Then el sistema responde con el mensaje "Credenciales inválidas"
    And el sistema no establece ninguna cookie de sesión
    And el sistema registra el intento fallido en "user_activity_logs"

  Scenario: Cuenta desactivada
    Given la cuenta del usuario tiene is_active = false
    When el usuario ingresa sus credenciales correctas
    Then el sistema responde con "Cuenta desactivada. Contacte al administrador."
    And el sistema no establece ninguna cookie de sesión
```

## 7.2 CU-O02: Buscar Hoteles

```gherkin
Feature: Búsqueda de hoteles
  Como cliente viajero
  Quiero buscar hoteles por destino, fechas y número de huéspedes
  Para encontrar opciones de alojamiento que se ajusten a mi viaje

  Background:
    Given existen hoteles cargados en "dim_hotels" con precios y disponibilidad
    And los hoteles tienen tipos de habitación configurados en "room_types"
    And los hoteles tienen inventario en "room_inventory_calendar"

  Scenario: Búsqueda con resultados
    When el cliente ingresa destino "Ciudad de México"
    And selecciona fechas check_in "2026-07-15" y check_out "2026-07-18"
    And ingresa 2 adultos, 0 niños, 1 habitación
    And hace clic en "Buscar"
    Then el sistema consulta "dim_hotels" filtrando por el destino
    And el sistema cruza con "room_inventory_calendar" para verificar disponibilidad
    And el sistema obtiene el precio mínimo desde "hotel_rate_calendar"
    And el sistema muestra una lista de hoteles con nombre, precio mínimo, rating e imagen

  Scenario: Búsqueda sin resultados
    When el cliente ingresa destino "Isla Inexistente"
    Then el sistema muestra "No se encontraron hoteles para los criterios seleccionados"
    And el sistema sugiere modificar fechas o destino
```

## 7.3 CU-O03: Filtrar y Comparar Hoteles

```gherkin
Feature: Filtrado y comparación de hoteles
  Como cliente viajero
  Quiero filtrar resultados y comparar hoteles lado a lado
  Para tomar una decisión informada sobre mi reserva

  Background:
    Given el cliente ha ejecutado una búsqueda con resultados (CU-O02)

  Scenario: Aplicar filtros con resultados
    When el cliente selecciona precio mínimo $500 y precio máximo $2000
    And selecciona calificación mínima 4 estrellas
    And selecciona amenity "WiFi"
    Then el sistema actualiza la lista mostrando solo hoteles que cumplen los filtros

  Scenario: Filtro sin resultados
    When el cliente selecciona precio máximo $100
    Then el sistema muestra "Ningún hotel coincide con los filtros seleccionados"
    And el sistema permite limpiar los filtros

  Scenario: Comparar 3 hoteles
    When el cliente selecciona 3 hoteles de la lista
    And hace clic en "Comparar"
    Then el sistema navega a la vista de comparación
    And el sistema muestra los 3 hoteles lado a lado con nombre, precio, rating, amenities y políticas
```

## 7.4 CU-O04: Ver Detalle de Hotel

```gherkin
Feature: Detalle de hotel
  Como cliente viajero
  Quiero ver la información completa de un hotel
  Para evaluar si deseo realizar una reserva

  Background:
    Given el hotel existe en "dim_hotels" con datos completos

  Scenario: Ver detalle completo
    When el cliente navega a la página de detalle del hotel
    Then el sistema muestra galería de imágenes desde "hotel_images"
    And el sistema muestra descripción y amenities desde "hotel_content_pages"
    And el sistema muestra políticas desde "hotel_policies"
    And el sistema muestra tarifas por tipo de habitación desde "hotel_rate_calendar"
    And el sistema muestra reseñas desde "reviews"

  Scenario: Hotel sin reseñas
    Given el hotel no tiene reseñas registradas
    When el cliente navega a la página de detalle
    Then el sistema muestra "Aún no hay reseñas para este hotel"

  Scenario: Hotel sin tarifas configuradas
    Given el hotel no tiene tarifas para las fechas consultadas
    When el cliente navega a la página de detalle
    Then el sistema muestra "Consultar disponibilidad" en lugar de tarifas
```

## 7.5 CU-O05: Solicitar Reserva

```gherkin
Feature: Solicitud de reserva
  Como cliente autenticado
  Quiero solicitar una reserva seleccionando tipo de habitación y fechas
  Para asegurar mi alojamiento en el hotel seleccionado

  Background:
    Given el cliente está autenticado con sesión activa
    And el hotel tiene disponibilidad en las fechas seleccionadas

  Scenario: Solicitud de reserva exitosa
    When el cliente selecciona un tipo de habitación, fechas y cantidad
    And el cliente ingresa datos de los huéspedes
    And el cliente confirma la reserva
    Then el sistema valida disponibilidad en "room_inventory_calendar"
    And el sistema calcula el total desde "hotel_rate_calendar"
    And el sistema crea un documento en "booking_orders" con estado "pending"
    And el sistema crea documentos en "booking_guests"
    And el sistema registra en "booking_status_history" con estado "created"
    And el sistema muestra el ID de la reserva y mensaje de confirmación

  Scenario: Sin disponibilidad en alguna noche
    When el cliente intenta reservar una habitación sin inventario suficiente
    Then el sistema muestra "La habitación seleccionada no está disponible para todas las fechas solicitadas"
    And el sistema sugiere fechas alternativas

  Scenario: Usuario no autenticado intenta reservar
    Given el cliente no ha iniciado sesión
    When el cliente hace clic en "Reservar"
    Then el sistema redirige al login
    And después de autenticarse, el sistema regresa al flujo de reserva
```

## 7.6 CU-O06: Consultar Mis Reservas

```gherkin
Feature: Consulta de reservas del cliente
  Como cliente autenticado
  Quiero consultar el listado de mis reservas
  Para conocer el estado y detalle de cada una

  Background:
    Given el cliente está autenticado con sesión activa
    And el cliente tiene reservas registradas en "booking_orders"

  Scenario: Listar reservas del cliente
    When el cliente navega a "Mis reservas"
    Then el sistema consulta "booking_orders" filtrado por user_id del cliente
    And el sistema muestra una tabla con: booking_id, hotel, fechas, estado, total
    And cada reserva tiene un enlace para ver detalle

  Scenario: Cliente sin reservas
    Given el cliente no tiene reservas registradas
    When el cliente navega a "Mis reservas"
    Then el sistema muestra "No tienes reservas activas"
    And el sistema muestra un botón para buscar hoteles
```

## 7.7 CU-O07: Cancelar Reserva según Política

```gherkin
Feature: Cancelación de reserva
  Como cliente autenticado
  Quiero cancelar una reserva existente
  Para liberar mi compromiso según las políticas de cancelación del hotel

  Background:
    Given el cliente está autenticado
    And el cliente tiene una reserva en estado "confirmed" o "pending"

  Scenario: Cancelación dentro del período gratuito
    Given la política de cancelación permite cancelación gratuita hasta 48 horas antes
    When el cliente selecciona cancelar su reserva
    And confirma la cancelación
    Then el sistema actualiza el estado en "booking_orders" a "cancelled"
    And el sistema registra en "booking_status_history" con estado "cancelled" y motivo
    And el sistema libera el inventario en "room_inventory_calendar"
    And el sistema muestra "Reserva cancelada exitosamente"

  Scenario: Cancelación con penalización
    Given la política de cancelación aplica cargo del 50% después de 48 horas
    When el cliente cancela fuera del período gratuito
    Then el sistema muestra el cargo por cancelación
    And el sistema procede con la cancelación registrando la penalización
```

## 7.8 CU-O08: Registrar Reserva Manual

```gherkin
Feature: Registro manual de reserva
  Como recepcionista
  Quiero registrar una reserva manualmente en el sistema
  Para gestionar reservas recibidas por teléfono, email o walk-in

  Background:
    Given el recepcionista está autenticado con rol "recepcionista"
    And el hotel tiene tipos de habitación configurados

  Scenario: Registro manual exitoso
    When el recepcionista accede al formulario de nueva reserva manual
    And selecciona hotel, tipo de habitación, fechas, huéspedes y total
    And confirma el registro
    Then el sistema crea la reserva en "booking_orders" con estado "confirmed"
    And el sistema descuenta el inventario en "room_inventory_calendar"
    And el sistema registra en "booking_status_history"
    And el sistema muestra confirmación con ID de reserva

  Scenario: Sin disponibilidad para reserva manual
    When el recepcionista intenta registrar una reserva sin inventario disponible
    Then el sistema muestra "No hay suficiente inventario para las fechas seleccionadas"
    And la reserva no se crea
```

## 7.9 CU-O09: Consultar Solicitudes de Reserva

```gherkin
Feature: Consulta de solicitudes de reserva
  Como gerente de hotel
  Quiero consultar las solicitudes de reserva pendientes
  Para revisar y gestionar las reservas que requieren confirmación

  Background:
    Given el gerente está autenticado con rol "hotel_manager"

  Scenario: Listar solicitudes pendientes
    When el gerente navega a "Solicitudes de reserva"
    Then el sistema consulta "booking_orders" con estado "pending" del hotel
    And el sistema muestra tabla con: booking_id, cliente, fechas, total, fecha_solicitud
    And cada solicitud tiene botones "Confirmar" y "Rechazar"

  Scenario: Sin solicitudes pendientes
    Given no hay reservas en estado "pending" para el hotel
    When el gerente navega a "Solicitudes de reserva"
    Then el sistema muestra "No hay solicitudes de reserva pendientes"
```

## 7.10 CU-O10: Completar Check-In

```gherkin
Feature: Check-in de reserva
  Como recepcionista
  Quiero completar el check-in de una reserva confirmada
  Para registrar la llegada del huésped y actualizar el estado de la reserva

  Background:
    Given el recepcionista está autenticado con rol "recepcionista"
    And existe una reserva en estado "confirmed"

  Scenario: Check-in exitoso
    When el recepcionista selecciona la reserva para check-in
    And confirma la llegada del huésped
    Then el sistema actualiza "booking_orders" a estado "checked_in"
    And el sistema registra en "booking_status_history" con timestamp de check-in
    And el sistema muestra "Check-in completado exitosamente"

  Scenario: Check-in de reserva ya en estado distinto
    When el gerente intenta hacer check-in de una reserva en estado "cancelled"
    Then el sistema muestra "La reserva no está en estado confirmado para realizar check-in"
```

## 7.11 CU-O11: Completar Check-Out

```gherkin
Feature: Check-out de reserva
  Como recepcionista
  Quiero completar el check-out de una reserva
  Para registrar la salida del huésped y liberar la habitación

  Background:
    Given el recepcionista está autenticado con rol "recepcionista"
    And existe una reserva en estado "checked_in"

  Scenario: Check-out exitoso
    When el recepcionista selecciona la reserva para check-out
    And registra el check-out
    Then el sistema actualiza "booking_orders" a estado "checked_out"
    And el sistema registra en "booking_status_history" con timestamp de check-out
    And el sistema libera inventario futuro si aplica
    And el sistema muestra "Check-out completado exitosamente"

  Scenario: Check-out de reserva no checked-in
    When el gerente intenta hacer check-out de una reserva en estado "confirmed"
    Then el sistema muestra "La reserva debe estar en estado checked_in para realizar check-out"
```

## 7.12 CU-O12: Editar Nombre Comercial del Hotel

```gherkin
Feature: Edición de nombre comercial del hotel
  Como marketing hotelero o partner
  Quiero editar el nombre comercial visible del hotel
  Para mantener actualizada la información comercial de la propiedad

  Background:
    Given el usuario está autenticado con rol "hotel_partner" o "marketing"
    And el usuario tiene acceso al hotel especificado

  Scenario: Edición exitosa de nombre comercial
    When el usuario navega a la configuración del hotel
    And modifica el nombre comercial de "Hotel Antiguo" a "Hotel Renovado"
    And guarda los cambios
    Then el sistema actualiza "hotel_commercial_names" con el nuevo nombre y timestamp
    And el sistema registra en "hotel_edit_history" el cambio con usuario y fecha
    And el sistema actualiza "dim_hotels.hotel_name" si aplica
    And el sistema muestra "Nombre comercial actualizado exitosamente"

  Scenario: Nombre comercial vacío
    When el usuario intenta guardar un nombre comercial vacío
    Then el sistema muestra "El nombre comercial no puede estar vacío"
    And el sistema no guarda los cambios
```

## 7.13 CU-O13: Consultar Historial de Cambios de Propiedad

```gherkin
Feature: Consulta de historial de cambios de propiedad
  Como auditor de datos o partner
  Quiero consultar el historial de cambios realizados sobre una propiedad
  Para auditar las modificaciones y mantener trazabilidad

  Background:
    Given existen registros de cambios en "hotel_edit_history" para la propiedad

  Scenario: Consultar historial de cambios
    When el usuario navega al historial de cambios de una propiedad
    Then el sistema consulta "hotel_edit_history" filtrado por prop_id
    And el sistema muestra tabla con: campo modificado, valor anterior, valor nuevo, usuario, timestamp

  Scenario: Propiedad sin cambios registrados
    Given la propiedad no tiene registros en "hotel_edit_history"
    When el usuario navega al historial de cambios
    Then el sistema muestra "No hay cambios registrados para esta propiedad"
```

## 7.14 CU-O14: Crear Tipo de Habitación

```gherkin
Feature: Creación de tipo de habitación
  Como hotel partner
  Quiero crear un nuevo tipo de habitación para mi hotel
  Para ofrecer diferentes opciones de alojamiento a los clientes

  Background:
    Given el partner está autenticado con rol "hotel_partner"
    And el partner tiene acceso al hotel

  Scenario: Creación exitosa de tipo de habitación
    When el partner accede al formulario de nuevo tipo de habitación
    And ingresa nombre "Suite Presidencial", capacidad 4 adultos, descripción, amenities
    And hace clic en "Guardar"
    Then el sistema crea el documento en "room_types" con prop_id y datos ingresados
    And el sistema muestra "Tipo de habitación creado exitosamente"

  Scenario: Campos obligatorios faltantes
    When el partner intenta guardar sin nombre de habitación
    Then el sistema muestra "El nombre del tipo de habitación es obligatorio"
    And el sistema no crea el registro
```

## 7.15 CU-O15: Actualizar Inventario por Fecha

```gherkin
Feature: Actualización de inventario por fecha
  Como gerente de hotel
  Quiero actualizar el inventario disponible por tipo de habitación y fecha
  Para gestionar la disponibilidad de habitaciones

  Background:
    Given el gerente está autenticado con rol "hotel_manager"
    And existen tipos de habitación configurados en "room_types"

  Scenario: Actualización exitosa de inventario
    When el gerente selecciona un tipo de habitación y rango de fechas
    And ingresa 10 habitaciones disponibles para cada fecha
    And guarda los cambios
    Then el sistema actualiza "room_inventory_calendar" para cada fecha en el rango
    And el sistema muestra "Inventario actualizado exitosamente"

  Scenario: Inventario negativo
    When el gerente intenta ingresar -5 habitaciones disponibles
    Then el sistema muestra "El inventario no puede ser negativo"
    And el sistema no actualiza los registros

  Scenario: Inventario mayor a capacidad máxima
    When el gerente intenta ingresar 500 habitaciones para un hotel con 50 habitaciones
    Then el sistema muestra "El inventario excede la capacidad máxima del hotel"
    And el sistema no actualiza los registros
```

## 7.16 CU-O16: Registrar Bloqueo de Disponibilidad

```gherkin
Feature: Bloqueo de disponibilidad
  Como gerente de hotel
  Quiero bloquear la disponibilidad de habitaciones en fechas específicas
  Para reservar habitaciones para mantenimiento, grupos o eventos especiales

  Background:
    Given el gerente está autenticado con rol "hotel_manager"

  Scenario: Bloqueo exitoso de disponibilidad
    When el gerente selecciona tipo de habitación y rango de fechas
    And ingresa motivo "Mantenimiento programado" y bloquea 5 habitaciones
    Then el sistema actualiza "room_inventory_calendar" reduciendo inventario disponible
    And el sistema registra el bloqueo con motivo y timestamp
    And el sistema muestra "Bloqueo registrado exitosamente"

  Scenario: Bloqueo sin motivo
    When el gerente intenta bloquear habitaciones sin especificar motivo
    Then el sistema muestra "El motivo del bloqueo es obligatorio"
    And el sistema no registra el bloqueo
```

## 7.17 CU-O17: Crear Plan Tarifario

```gherkin
Feature: Creación de plan tarifario
  Como revenue manager
  Quiero crear un plan tarifario con nombre, descripción y políticas
  Para definir las reglas de precios aplicables a tipos de habitación

  Background:
    Given el revenue manager está autenticado con rol "revenue_manager"

  Scenario: Creación exitosa de plan tarifario
    When el revenue manager accede al formulario de nuevo plan tarifario
    And ingresa nombre "Plan Económico", descripción "Sin reembolso"
    And selecciona políticas de cancelación "no_refund"
    And guarda el plan
    Then el sistema crea el documento en "rate_plans" con los datos ingresados
    And el sistema muestra "Plan tarifario creado exitosamente"
```

## 7.18 CU-O18: Configurar Tarifa por Fecha

```gherkin
Feature: Configuración de tarifa por fecha
  Como revenue manager
  Quiero configurar el precio por noche para un tipo de habitación y plan tarifario en fechas específicas
  Para establecer tarifas dinámicas según temporada y demanda

  Background:
    Given el revenue manager está autenticado con rol "revenue_manager"
    And existe un plan tarifario creado en "rate_plans"
    And existe un tipo de habitación en "room_types"

  Scenario: Configuración exitosa de tarifa
    When el revenue manager selecciona tipo de habitación, plan tarifario y rango de fechas
    And ingresa precio $1500 por noche
    And guarda la tarifa
    Then el sistema actualiza "hotel_rate_calendar" con el precio por cada fecha
    And el sistema muestra "Tarifa configurada exitosamente"

  Scenario: Tarifa con precio cero o negativo
    When el revenue manager intenta ingresar precio $0
    Then el sistema muestra "El precio debe ser mayor a cero"
    And el sistema no actualiza las tarifas
```

## 7.19 CU-O19: Crear Promoción y Cupón

```gherkin
Feature: Creación de promoción y cupón
  Como marketing o revenue manager
  Quiero crear promociones y cupones de descuento
  Para incentivar reservas en temporada baja o promocionar hoteles específicos

  Background:
    Given el usuario está autenticado con rol "marketing" o "revenue_manager"

  Scenario: Creación exitosa de promoción
    When el usuario accede al formulario de nueva promoción
    And ingresa nombre "Verano 2026", descuento 15%, código "VERANO15"
    And selecciona fechas de vigencia y hoteles aplicables
    And guarda la promoción
    Then el sistema crea la promoción en "promotions"
    And el sistema crea el cupón en "coupons" asociado a la promoción
    And el sistema muestra "Promoción y cupón creados exitosamente"

  Scenario: Código de cupón duplicado
    When el usuario ingresa un código de cupón que ya existe
    Then el sistema muestra "El código de cupón ya está registrado"
    And el sistema no crea la promoción
```

## 7.20 CU-O20: Editar Política Hotelera

```gherkin
Feature: Edición de política hotelera
  Como hotel partner
  Quiero editar las políticas del hotel
  Para establecer las reglas de cancelación, check-in/out, mascotas y niños

  Background:
    Given el partner está autenticado con rol "hotel_partner"
    And el partner tiene acceso al hotel

  Scenario: Edición exitosa de políticas
    When el partner navega a la sección de políticas del hotel
    And modifica política de cancelación a "free_cancellation_48h"
    And establece check-in desde las 15:00 y check-out hasta las 12:00
    And permite mascotas con costo adicional $500
    And guarda los cambios
    Then el sistema actualiza "hotel_policies" con los nuevos valores
    And el sistema registra el cambio en "hotel_edit_history"
    And el sistema muestra "Políticas actualizadas exitosamente"
```

## 7.21 CU-O21: Actualizar Amenities, Imágenes y Contenido

```gherkin
Feature: Actualización de amenities, imágenes y contenido
  Como marketing hotelero
  Quiero actualizar las amenities, imágenes y contenido descriptivo del hotel
  Para mantener atractiva la ficha del hotel ante los clientes

  Background:
    Given el usuario está autenticado con rol "marketing"
    And el usuario tiene acceso al hotel

  Scenario: Actualización exitosa de amenities
    When el usuario navega a la sección de amenities del hotel
    And agrega "WiFi" y "Piscina" como amenities disponibles
    And guarda los cambios
    Then el sistema actualiza "hotel_content_pages" con los nuevos amenities
    And el sistema muestra "Amenities actualizados exitosamente"

  Scenario: Subida exitosa de imágenes
    When el usuario sube 3 imágenes en formato JPEG (máx 2MB cada una)
    Then el sistema almacena las imágenes en "hotel_images" en base64
    And el sistema actualiza "dim_hotels.main_image" con la primera imagen
    And el sistema muestra "Imágenes actualizadas exitosamente"

  Scenario: Imagen excede tamaño máximo
    When el usuario intenta subir una imagen de 5MB
    Then el sistema muestra "La imagen excede el tamaño máximo de 2MB"
    And el sistema no almacena la imagen
```

## 7.22 CU-O22: Registrar Reseña de Estancia

```gherkin
Feature: Registro de reseña de estancia
  Como cliente
  Quiero registrar una reseña después de mi estancia
  Para compartir mi experiencia y ayudar a otros viajeros

  Background:
    Given el cliente está autenticado
    And el cliente tiene una reserva finalizada (checked_out)

  Scenario: Registro exitoso de reseña
    When el cliente navega a la sección de reseñas de su reserva completada
    And ingresa calificación 4 estrellas y comentario "Excelente servicio y ubicación"
    And hace clic en "Publicar reseña"
    Then el sistema crea el documento en "reviews" con prop_id, user_id, rating, comentario
    And el sistema actualiza "fact_reviews" con los datos de la reseña
    And el sistema muestra "Reseña publicada exitosamente"

  Scenario: Reseña sin comentario
    When el cliente intenta publicar una reseña sin escribir comentario
    Then el sistema permite publicar solo con calificación (comentario opcional)
    And la reseña se crea sin campo de comentario

  Scenario: Cliente sin reserva completada intenta reseñar
    Given el cliente no tiene ninguna reserva en estado "checked_out"
    When el cliente navega a la sección de reseñas
    Then el sistema muestra "Debes tener una estancia completada para escribir una reseña"
```

## 7.23 CU-O23: Moderar y Responder Reseña

```gherkin
Feature: Moderación y respuesta de reseñas
  Como marketing o administrador
  Quiero moderar y responder reseñas de huéspedes
  Para gestionar la reputación online del hotel

  Background:
    Given el usuario está autenticado con rol "marketing" o "super_admin"
    And existen reseñas pendientes de moderación

  Scenario: Moderación — Aprobar reseña
    When el usuario selecciona una reseña pendiente y hace clic en "Aprobar"
    Then el sistema actualiza "reviews.status" a "approved"
    And la reseña se hace visible en la página pública del hotel

  Scenario: Moderación — Rechazar reseña
    When el usuario selecciona una reseña pendiente y hace clic en "Rechazar"
    And ingresa motivo de rechazo "Contenido inapropiado"
    Then el sistema actualiza "reviews.status" a "rejected"
    And la reseña no se muestra en la página pública

  Scenario: Respuesta del hotel a reseña aprobada
    When el usuario selecciona una reseña aprobada
    And escribe respuesta "Agradecemos sus comentarios, nos esforzamos por mejorar"
    And hace clic en "Responder"
    Then el sistema actualiza "reviews.hotel_response" con el texto y timestamp
    And la respuesta se muestra junto a la reseña en la página pública
```

## 7.24 CU-O24: Generar Comprobante o Factura de Reserva

```gherkin
Feature: Generación de comprobante o factura de reserva
  Como recepcionista o sistema
  Quiero generar un comprobante o factura asociado a una reserva finalizada
  Para proporcionar respaldo documental al huésped

  Background:
    Given existe una reserva en estado "checked_out" en "booking_orders"

  Scenario: Generación exitosa de factura
    When el recepcionista navega a la sección de facturación de una reserva
    And ingresa datos fiscales del huésped (RFC, razón social)
    And hace clic en "Generar factura"
    Then el sistema crea el documento en "billing_invoices" con booking_id, datos fiscales, total
    And el sistema genera el comprobante con folio único y timestamp
    And el sistema muestra "Factura generada exitosamente" con el folio

  Scenario: Factura ya existente para la reserva
    When el recepcionista intenta generar una factura para una reserva que ya tiene factura
    Then el sistema muestra "La reserva ya tiene una factura asociada"
    And el sistema permite descargar la factura existente

  Scenario: Reserva en estado no facturable
    When el recepcionista intenta generar factura para una reserva en estado "pending"
    Then el sistema muestra "La reserva debe estar finalizada (checked_out) para generar factura"
```

## 7.25 CU-O25: Registrar Pago Asociado a Reserva

```gherkin
Feature: Registro de pago asociado a reserva
  Como recepcionista
  Quiero registrar un pago asociado a una reserva
  Para llevar la trazabilidad financiera de las transacciones

  Background:
    Given el recepcionista está autenticado con rol "recepcionista"
    And existe una reserva en "booking_orders"

  Scenario: Registro exitoso de pago
    When el recepcionista selecciona una reserva y accede a "Registrar pago"
    And ingresa monto $3500, método "Efectivo", referencia "Pago-001"
    And confirma el pago
    Then el sistema crea el registro en "billing_payments" con booking_id, monto, método, referencia
    And el sistema muestra "Pago registrado exitosamente"

  Scenario: Pago con monto mayor al total de la reserva
    When el gerente intenta registrar un pago de $5000 para una reserva de $3500
    Then el sistema muestra "El monto del pago excede el total de la reserva"
    And el sistema no registra el pago
```

## 7.26 CU-O26: Consultar Reportes de Revenue y Mercado

```gherkin
Feature: Consulta de reportes de revenue y mercado
  Como gerente o revenue manager
  Quiero consultar reportes de revenue, precio medio, ocupación y rendimiento
  Para tomar decisiones basadas en datos del mercado hotelero

  Background:
    Given el usuario está autenticado con rol "hotel_manager" o "revenue_manager"
    And existen datos en "fact_hotel_reservations" y "fact_search_events"

  Scenario: Consultar reporte de revenue por período
    When el usuario selecciona rango de fechas y hotel (o "todos")
    And hace clic en "Generar reporte"
    Then el sistema consulta "fact_hotel_reservations" agregando por fecha
    And el sistema muestra revenue total, ADR, RevPAR, ocupación y precio promedio

  Scenario: Consultar reporte de mercado por destino
    When el usuario selecciona un destino y período
    Then el sistema muestra top 10 hoteles por revenue, precio promedio y ocupación

  Scenario: Exportar reporte
    When el usuario hace clic en "Exportar"
    Then el sistema descarga el reporte en formato CSV o JSON
```

## 7.27 CU-O27: Consultar Reporte de Calidad y Registros Rechazados

```gherkin
Feature: Consulta de reporte de calidad de datos
  Como auditor de datos
  Quiero consultar reportes de calidad y registros rechazados del ETL
  Para monitorear la integridad de los datos en el pipeline

  Background:
    Given el auditor está autenticado con rol "data_auditor"

  Scenario: Consultar reporte de calidad
    When el auditor navega a la sección de calidad de datos
    Then el sistema consulta "data_quality_reports" con las métricas más recientes
    And el sistema muestra total de registros, tasa de rechazo, reglas de calidad y checks

  Scenario: Consultar registros rechazados
    When el auditor filtra por fecha y tipo de error
    Then el sistema consulta "rejected_records" con los registros que fallaron validación
    And el sistema muestra tabla con: registro original, regla fallida, timestamp, acción sugerida

  Scenario: Consultar estado de ejecución ETL
    When el auditor navega a "Ejecuciones ETL"
    Then el sistema consulta "etl_executions" con estado, fecha, duración y resultado
    And el sistema muestra historial de ejecuciones del pipeline
```

## 7.28 CU-O28: Administrar Cuenta, Sesión y Cierre Seguro

```gherkin
Feature: Administración de cuenta, sesión y cierre seguro
  Como usuario autenticado
  Quiero cerrar mi sesión de forma segura y consultar el estado de mi sesión
  Para proteger mi cuenta y gestionar mi acceso al sistema

  Background:
    Given el usuario está autenticado con sesión activa
    And existe un documento en "user_sessions" para el usuario

  Scenario: Cierre de sesión exitoso
    When el usuario hace clic en "Cerrar sesión"
    Then el sistema recibe la solicitud en "GET /auth/logout"
    And el sistema extrae el token de la cookie "hoteldata_session"
    And el sistema calcula el hash SHA-256 del token
    And el sistema elimina el documento correspondiente de "user_sessions"
    And el sistema elimina la cookie "hoteldata_session" (max-age=0)
    And el sistema registra el evento en "user_activity_logs" con tipo "logout"
    And el sistema redirige al usuario a la página de login

  Scenario: Consultar sesión actual
    When el usuario navega a su perfil
    Then el sistema valida la sesión actual contra "user_sessions"
    And el sistema muestra información de la sesión (user_id, email, rol, display_name)

  Scenario: Sesión expirada al intentar acción
    Given la sesión del usuario ha expirado (TTL de 8 horas)
    When el usuario intenta acceder a una ruta protegida
    Then el sistema responde HTTP 401
    And el sistema redirige al login
```

## 7.29 CU-O29: Cambiar Contraseña y Actualizar Perfil de Usuario

```gherkin
Feature: Cambio de contraseña y actualización de perfil
  Como usuario autenticado
  Quiero cambiar mi contraseña y actualizar los datos de mi perfil
  Para mantener segura mi cuenta y actualizada mi información personal

  Background:
    Given el usuario está autenticado con sesión activa en "user_sessions"

  Scenario: Cambio de contraseña exitoso
    When el usuario navega a configuración de cuenta
    And ingresa contraseña actual "OldPass123" y nueva contraseña "NewPass456"
    And confirma la nueva contraseña
    Then el sistema verifica la contraseña actual con bcrypt
    And el sistema valida que la nueva tenga al menos 8 caracteres
    And el sistema hashea la nueva contraseña con bcrypt
    And el sistema actualiza "users.password_hash" con el nuevo hash
    And el sistema invalida todas las sesiones activas excepto la actual
    And el sistema registra el cambio en "user_activity_logs"
    And el sistema muestra "Contraseña actualizada exitosamente"

  Scenario: Contraseña actual incorrecta
    When el usuario ingresa una contraseña actual incorrecta
    Then el sistema responde "Contraseña actual incorrecta"
    And el sistema no cambia la contraseña

  Scenario: Actualización de perfil exitosa
    When el usuario navega a su perfil
    And modifica display_name a "Juan Pérez" y email a "juan@example.com"
    And guarda los cambios
    Then el sistema valida que el email no esté duplicado
    And el sistema actualiza "users.profile" con los nuevos datos
    And el sistema registra el cambio en "user_activity_logs"
    And el sistema muestra "Perfil actualizado exitosamente"

  Scenario: Email duplicado en actualización de perfil
    When el usuario intenta cambiar su email a uno ya registrado por otro usuario
    Then el sistema muestra "El email ya está registrado por otro usuario"
    And el sistema no actualiza el perfil
```

## 7.30 CU-O30: Gestionar Disponibilidad y Estado de Habitaciones

```gherkin
Feature: Gestión de disponibilidad y estado de habitaciones
  Como recepcionista o gerente de hotel
  Quiero consultar el estado de las habitaciones, asignar tipos y verificar disponibilidad individual
  Para gestionar el inventario físico del hotel de manera centralizada

  Background:
    Given el recepcionista está autenticado con rol "recepcionista"
    And el hotel tiene habitaciones configuradas en "hotel_rooms" y "room_types"

  Scenario: Consultar estado de todas las habitaciones
    When el recepcionista navega al panel de estado de habitaciones
    Then el sistema muestra un grid con todas las habitaciones del hotel
    And cada habitación muestra: número, tipo, estado actual, última actualización
    And el sistema permite filtrar por tipo de habitación, estado o rango de fechas

  Scenario: Asignar tipo de habitación a habitación individual
    Given la habitación 205 está en estado "disponible"
    When el recepcionista selecciona la habitación 205
    And asigna el tipo de habitación "Suite Ejecutiva" a esta habitación
    Then el sistema actualiza el tipo de habitación asignado
    And el sistema registra el cambio en "room_status_log" con timestamp

  Scenario: Consultar disponibilidad por habitación individual
    When el recepcionista selecciona la habitación 205
    And solicita ver el calendario de disponibilidad
    Then el sistema muestra disponibilidad por fecha para los próximos 30 días
    And muestra las reservas activas que ocupan esa habitación
```

## 7.31 CU-O31: Gestionar Geolocalización y Metadata de Contenido

```gherkin
Feature: Gestión de geolocalización y metadata
  Como auditor de datos o marketing hotelero
  Quiero editar metadata de destinos, nombres de hoteles y visualizar el mapa mundial
  Para mantener actualizado el catálogo geoespacial de destinos

  Background:
    Given el usuario está autenticado con rol "auditor_datos" o "marketing_hotelero"
    And existen destinos con coordenadas en "destinations_enriched"

  Scenario: Editar metadata de destino
    When el usuario selecciona un destino en el mapa
    And edita el nombre visible a "Cancún Centro" y coordenadas a 21.1619, -86.8515
    Then el sistema actualiza "destinations_enriched" con los nuevos datos
    And el sistema registra el cambio en "destinations_log"

  Scenario: Editar nombre visible de hotel con manual_override
    When el usuario selecciona un hotel en el mapa o listado
    And edita el nombre visible de "Hotel 12345" a "Grand Paradise Resort"
    Then el sistema actualiza "dim_hotels.hotel_name" con el nuevo nombre
    And el sistema activa "manual_override = true" para evitar sobrescritura del ETL

  Scenario: Visualizar mapa mundial con hoteles geolocalizados
    When el usuario navega al gestor geoespacial
    Then el sistema carga el mapa mundial interactivo con Leaflet.js
    And el sistema muestra marcadores en las coordenadas de cada destino con hoteles
    And cada marcador muestra nombre del destino y cantidad de hoteles al hacer clic
```

## 7.32 CU-O32: Gestionar Notificaciones Transaccionales al Huésped

```gherkin
Feature: Notificaciones transaccionales al huésped
  Como sistema
  Quiero enviar notificaciones automáticas al huésped durante el ciclo de su reserva
  Para mantenerlo informado sobre el estado de su estancia

  Background:
    Given existe una reserva activa en "booking_orders" con datos de contacto del huésped
    And existen plantillas configuradas en "notification_templates"

  Scenario: Notificación de confirmación de reserva
    When una reserva es creada con estado "confirmed"
    Then el sistema selecciona la plantilla "booking_confirmation" desde "notification_templates"
    And el sistema personaliza la plantilla con datos de la reserva
    And el sistema envía la notificación por email al huésped
    And el sistema registra el envío en "notification_logs" con estado "enviado"

  Scenario: Notificación de recordatorio de check-in
    Given es 24 horas antes del check-in de una reserva confirmada
    When el sistema ejecuta el job de recordatorios
    Then el sistema envía recordatorio de check-in con instrucciones y horarios
    And el sistema registra el envío en "notification_logs"

  Scenario: Notificación post-checkout con factura
    When el check-out es completado exitosamente
    Then el sistema envía la factura de la estancia al email del huésped
    And el sistema incluye detalle de cargos, fechas y total
```

## 7.33 CU-O33: Gestionar Alertas Operativas Internas al Staff

```gherkin
Feature: Alertas operativas internas al staff
  Como sistema
  Quiero generar alertas operativas para el personal del hotel
  Para coordinar limpieza, mantenimiento y atención al huésped

  Background:
    Given existe personal asignado en roles housekeeping, mantenimiento y recepción
    And las habitaciones están registradas en "hotel_rooms"

  Scenario: Alerta de limpieza post-checkout
    When un check-out es completado en la habitación 205
    Then el sistema crea una alerta de limpieza con prioridad "alta"
    And la alerta se asigna al equipo de housekeeping disponible
    And la alerta aparece en el panel de notificaciones internas

  Scenario: Marcar alerta como resuelta
    Given existe una alerta de limpieza activa para la habitación 205
    When el personal de housekeeping marca la alerta como "resuelta"
    Then el sistema actualiza el estado de la alerta a "resuelta"
    And el sistema registra el tiempo de resolución

  Scenario: Escalamiento de alerta no resuelta
    Given existe una alerta de limpieza sin resolver después de 60 minutos
    When el tiempo límite se supera
    Then el sistema escala la alerta al gerente de hotel
    And la alerta se marca con prioridad "crítica"
```

## 7.34 CU-O34: Gestionar Campañas Promocionales Multicanal

```gherkin
Feature: Campañas promocionales multicanal
  Como marketing hotelero
  Quiero crear y lanzar campañas promocionales segmentadas por múltiples canales
  Para incentivar reservas y medir la efectividad de cada campaña

  Background:
    Given el usuario está autenticado con rol "marketing_hotelero"
    And existen plantillas de notificación configuradas

  Scenario: Crear y lanzar campaña promocional
    When el usuario crea una nueva campaña con nombre "Verano 2026"
    And selecciona segmento: huéspedes frecuentes con historial de 3+ reservas
    And selecciona canales: email y SMS
    And selecciona promoción "Descuento 20%" asociada
    And programa la campaña para el próximo lunes
    Then el sistema calcula el tamaño del segmento (ej: 1,247 huéspedes)
    And el sistema programa la campaña para la fecha seleccionada

  Scenario: Ver métricas de campaña
    Given la campaña "Verano 2026" ha sido ejecutada
    When el usuario navega a las métricas de la campaña
    Then el sistema muestra: enviados, abiertos, clicks, conversiones, revenue generado
    And el sistema muestra el ROI de la campaña
```

## 7.35 CU-O35: Atender Cliente Mediante Asistente Virtual (Chatbot IA)

```gherkin
Feature: Atención al cliente mediante chatbot IA
  Como cliente
  Quiero hacer consultas en lenguaje natural a un asistente virtual
  Para obtener respuestas rápidas sobre hoteles, reservas y servicios

  Background:
    Given el sistema tiene una base de conocimiento configurada en "chatbot_knowledge_base"
    And el motor de chatbot IA está operativo

  Scenario: Consulta resuelta por el chatbot
    When el cliente escribe "¿Cuál es la política de cancelación del Hotel Paraíso?"
    Then el chatbot busca en la base de conocimiento la política de cancelación
    And el chatbot responde con la información de la política
    And la conversación queda registrada en "chatbot_conversations"

  Scenario: Consulta escalada a humano
    When el cliente escribe "Tengo un problema con mi reserva y necesito hablar con alguien"
    Then el chatbot detecta que no puede resolver la consulta
    And el chatbot ofrece escalar a un agente humano
    When el cliente confirma el escalamiento
    Then la conversación se asigna a un recepcionista disponible
    And el recepcionista recibe el historial completo del chat

  Scenario: Chatbot fuera de horario
    Given es horario nocturno (23:00-07:00)
    When el cliente solicita escalamiento a humano
    Then el chatbot informa que no hay agentes disponibles en este horario
    And el chatbot agenda un follow-up para el día siguiente
```

## 7.36 CU-O36: Gestionar Up-Selling y Ancillaries Durante la Estancia

```gherkin
Feature: Up-selling y ancillaries durante la estancia
  Como recepcionista
  Quiero ofrecer servicios adicionales a los huéspedes durante su estancia
  Para generar ingresos adicionales y mejorar su experiencia

  Background:
    Given el recepcionista está autenticado con rol "recepcionista"
    And existe una reserva activa en estado "confirmed" o "checked_in"

  Scenario: Ofrecer upgrade de habitación en check-in
    When el recepcionista abre la reserva durante el check-in
    Then el sistema muestra oportunidades de up-selling basadas en disponibilidad
    When el recepcionista ofrece upgrade a Suite Ejecutiva por $50/noche
    And el huésped acepta
    Then el sistema registra el cargo adicional en "additional_charges"
    And el sistema actualiza "booking_orders.total"
    And el sistema actualiza el tipo de habitación asignado

  Scenario: Late check-out durante la estancia
    When el recepcionista ofrece late check-out hasta las 18:00 por $30
    And el huésped acepta
    Then el sistema registra el cargo adicional por late check-out
    And el sistema actualiza la hora de check-out en la reserva

  Scenario: Huésped rechaza up-selling
    When el recepcionista ofrece un servicio adicional
    And el huésped rechaza la oferta
    Then el recepcionista marca la oferta como "rechazada"
    And el sistema registra la oportunidad perdida para análisis
```

## 7.37 CU-O37: Gestionar Contenidos Multimedia con Geolocalización

```gherkin
Feature: Contenidos multimedia con geolocalización
  Como marketing hotelero
  Quiero subir y geolocalizar contenido multimedia de hoteles y destinos
  Para enriquecer la presentación visual con fotos y videos ubicados geográficamente

  Background:
    Given el usuario está autenticado con rol "marketing_hotelero"
    And el hotel o destino existe en la base de datos

  Scenario: Subir foto geolocalizada
    When el usuario navega al gestor multimedia del hotel
    And selecciona una foto de la piscina (JPEG, 3MB)
    And arrastra el marcador en el mapa a la ubicación de la piscina
    And completa título "Piscina principal" y tags ["piscina", "exterior"]
    Then el sistema almacena la foto en MongoDB GridFS
    And el sistema crea el registro en "hotel_multimedia" con coordenadas y metadata
    And la foto aparece en la galería y en el mapa interactivo

  Scenario: Archivo excede tamaño máximo
    When el usuario intenta subir un video de 80MB
    Then el sistema rechaza con "El archivo excede el tamaño máximo permitido (50MB)"
    And el archivo no se almacena

  Scenario: Desactivar contenido multimedia
    Given existe una foto activa en la galería
    When el usuario desactiva la foto
    Then el sistema cambia el estado a "inactivo"
    And la foto deja de ser visible en la galería pública
    And el archivo no se elimina del almacenamiento
```

## 7.38 CU-T14: Gestionar Rotación y Limpieza de Habitaciones (Táctico)

```gherkin
Feature: Gestión táctica de rotación y limpieza
  Como gerente de hotel
  Quiero optimizar la rotación de habitaciones y asignar personal de limpieza
  Para reducir tiempos muertos entre check-out y check-in

  Background:
    Given el gerente está autenticado con rol "gerente_hotel"

  Scenario: Definir tiempo objetivo de rotación
    When el gerente navega a la configuración de housekeeping
    And establece tiempo objetivo de rotación en 45 minutos
    Then el sistema guarda el tiempo objetivo en "hotel_settings"
    And el dashboard de eficiencia mostrará alertas cuando se supere este tiempo

  Scenario: Asignar cuadrilla de limpieza
    When el gerente navega al planificador de housekeeping
    And asigna 3 personas al turno matutino y 2 al vespertino
    Then el sistema registra la asignación de personal
    And las alertas de limpieza se asignarán automáticamente al personal disponible

  Scenario: Ver reporte de tiempos de rotación
    When el gerente solicita el reporte de rotación semanal
    Then el sistema muestra tiempo promedio de rotación, máximo y mínimo
    And el sistema muestra cuántas habitaciones superaron el tiempo objetivo
```

## 7.39 CU-T15: Programar Mantenimiento Preventivo y Correctivo (Táctico)

```gherkin
Feature: Programación de mantenimiento preventivo y correctivo
  Como gerente de hotel
  Quiero programar y dar seguimiento al mantenimiento de habitaciones
  Para minimizar interrupciones y prolongar la vida útil de las instalaciones

  Background:
    Given el gerente está autenticado con rol "gerente_hotel"

  Scenario: Programar mantenimiento preventivo
    When el gerente navega al planificador de mantenimiento
    And selecciona habitaciones 201-210 para mantenimiento trimestral
    And programa para el próximo lunes 09:00-13:00
    Then el sistema bloquea la disponibilidad de esas habitaciones en ese horario
    And el sistema crea tareas de mantenimiento en "maintenance_schedule"
    And el sistema notifica al equipo de mantenimiento

  Scenario: Registrar mantenimiento correctivo
    Given existe una incidencia reportada en la habitación 305 (Aire acondicionado)
    When el gerente asigna la tarea al técnico disponible
    And el técnico completa la reparación
    Then el sistema registra el mantenimiento en "maintenance_tasks" con fecha y costo
    And la habitación vuelve a estar disponible

  Scenario: Ver calendario de mantenimiento
    When el gerente solicita el calendario de mantenimiento mensual
    Then el sistema muestra las tareas programadas y completadas
    And el sistema muestra el cumplimiento de mantenimiento preventivo (%)
```

## 7.40 CU-T16: Configurar Canales y Plantillas de Notificación (Táctico)

```gherkin
Feature: Configuración de canales y plantillas de notificación
  Como super admin
  Quiero configurar los canales de envío y las plantillas de notificación del sistema
  Para garantizar que las comunicaciones con huéspedes y staff sean correctas y personalizadas

  Background:
    Given el super admin está autenticado con rol "super_admin"

  Scenario: Configurar canal de email
    When el super admin navega a configuración de notificaciones
    And configura servidor SMTP: host "smtp.hoteldata.com", puerto 587, TLS habilitado
    And guarda la configuración
    Then el sistema prueba la conexión SMTP
    And el sistema muestra "Canal de email configurado exitosamente"

  Scenario: Editar plantilla de notificación
    When el super admin selecciona la plantilla "booking_confirmation"
    And edita el asunto a "¡Reserva confirmada en {{hotel_name}}!"
    And modifica el cuerpo de la plantilla
    Then el sistema guarda la plantilla actualizada en "notification_templates"
    And la nueva plantilla se usará en el próximo envío

  Scenario: Probar envío de notificación
    Given existe una plantilla configurada
    When el super admin hace clic en "Enviar prueba"
    And ingresa email "test@hoteldata.com"
    Then el sistema envía una notificación de prueba al email ingresado
    And el sistema muestra "Notificación de prueba enviada"
```

## 7.41 CU-T17: Configurar Base de Conocimiento del Chatbot (Táctico)

```gherkin
Feature: Configuración de base de conocimiento del chatbot
  Como marketing o super admin
  Quiero gestionar la base de conocimiento del chatbot
  Para mejorar la precisión de las respuestas del asistente virtual

  Background:
    Given el usuario está autenticado con rol "marketing_hotelero" o "super_admin"

  Scenario: Agregar entrada a la base de conocimiento
    When el usuario navega al gestor de base de conocimiento
    And agrega nueva entrada: pregunta "¿Hay estacionamiento gratuito?", respuesta "Sí, todos nuestros hoteles ofrecen estacionamiento gratuito para huéspedes"
    And asigna categoría "Servicios del hotel"
    Then el sistema guarda la entrada en "chatbot_knowledge_base"
    And el chatbot podrá responder esta pregunta automáticamente

  Scenario: Desactivar entrada de conocimiento
    Given existe una entrada desactualizada en la base de conocimiento
    When el usuario desactiva la entrada
    Then el sistema cambia el estado a "inactivo"
    And el chatbot dejará de usar esa entrada para responder

  Scenario: Ver estadísticas del chatbot
    When el usuario solicita estadísticas del chatbot
    Then el sistema muestra: consultas totales, tasa de resolución, tasa de escalamiento
    And el sistema muestra las preguntas más frecuentes no resueltas
```

## 7.42 CU-E09: Monitorear Eficiencia Operativa del Hotel (Estratégico)

```gherkin
Feature: Monitoreo de eficiencia operativa del hotel
  Como gerente general o super admin
  Quiero monitorear KPIs operativos del hotel en un dashboard ejecutivo
  Para tomar decisiones estratégicas basadas en datos de operación

  Background:
    Given el usuario está autenticado con rol "gerente_general" o "super_admin"

  Scenario: Ver dashboard de eficiencia operativa
    When el usuario navega al dashboard de eficiencia operativa
    Then el sistema muestra KPIs principales: tiempo promedio de rotación, cumplimiento de limpieza, cumplimiento de mantenimiento, ocupación real vs disponible
    And el sistema muestra tendencias semanales de cada KPI
    And el sistema muestra alertas de eficiencia (cuando un KPI está por debajo del objetivo)

  Scenario: Identificar cuellos de botella operativos
    When el usuario selecciona "Ver detalles de rotación"
    Then el sistema muestra las habitaciones con mayor tiempo de rotación
    And el sistema muestra el personal de limpieza con menor productividad
    And el sistema sugiere optimizaciones basadas en datos históricos
```

## 7.43 CU-E10: Gestionar Ingresos por Up-Selling y Ancillaries (Estratégico)

```gherkin
Feature: Gestión de ingresos por up-selling y ancillaries
  Como gerente general o revenue manager
  Quiero analizar los ingresos generados por up-selling y ancillaries
  Para optimizar la estrategia de venta adicional y maximizar el revenue por huésped

  Background:
    Given el usuario está autenticado con rol "gerente_general" o "revenue_manager"

  Scenario: Ver reporte de ingresos por up-selling
    When el usuario navega al reporte de up-selling
    Then el sistema muestra ingresos totales por up-selling en el período seleccionado
    And el sistema desglosa por tipo: upgrades, late check-out, ancillaries
    And el sistema muestra el revenue por huésped (RevPH) con y sin up-selling

  Scenario: Comparar efectividad por tipo de ancillary
    When el usuario selecciona comparar por tipo de ancillary
    Then el sistema muestra tasa de aceptación por tipo: upgrades 35%, late check-out 28%, spa 15%
    And el sistema muestra el revenue promedio por transacción de cada tipo
    And el sistema recomienda focos de mejora basados en los datos

  Scenario: Proyectar ingresos por up-selling
    When el usuario solicita proyección trimestral
    Then el sistema calcula el revenue potencial basado en ocupación proyectada y tasas históricas de aceptación
    And el sistema muestra el revenue estimado con y sin optimización de up-selling
```


## 8.1 Matriz de Trazabilidad Completa

La siguiente matriz conecta los objetivos estratégicos (OE) con los objetivos tácticos (OT), operativos (OO), casos de uso operativos (CU-O) y sus historias de usuario Gherkin correspondientes.

| OE | OT | OO | CU | Historia Gherkin |
|----|----|----|----|-----------------|
| OE1: Penetrar mercados hoteleros digitales | OT1.1: Automatizar captación digital internacional | OO1.1.1: Registrar eventos de búsqueda y reserva | CU-O02: Buscar hoteles | HU-02: Búsqueda de hoteles |
| OE1 | OT1.1 | OO1.1.1 | CU-O03: Filtrar y comparar hoteles | HU-03: Filtrado y comparación de hoteles |
| OE1 | OT1.1 | OO1.1.1 | CU-O04: Ver detalle de hotel | HU-04: Detalle de hotel |
| OE1 | OT1.1 | OO1.1.1 | CU-O05: Solicitar reserva | HU-05: Solicitud de reserva |
| OE1 | OT1.1 | OO1.1.2: Medir conversión del embudo digital | CU-O26: Consultar reportes de revenue y mercado | HU-26: Consulta de reportes de revenue y mercado |
| OE1 | OT1.2: Fortalecer reputación del huésped | OO1.2.1: Registrar reseñas de estancia | CU-O22: Registrar reseña de estancia | HU-22: Registro de reseña de estancia |
| OE1 | OT1.2 | OO1.2.1 | CU-O23: Moderar y responder reseña | HU-23: Moderación y respuesta de reseñas |
| OE1 | OT1.2 | OO1.2.2: Generar comprobantes/facturación | CU-O24: Generar comprobante o factura | HU-24: Generación de comprobante o factura |
| OE1 | OT1.2 | OO1.2.2 | CU-O25: Registrar pago asociado a reserva | HU-25: Registro de pago asociado a reserva |
| OE2: Escalar comercialmente | OT2.1: Estandarizar servicios por API | OO2.1.2: Validar JWT y roles por endpoint | CU-O01: Iniciar sesión con JWT | HU-01: Inicio de sesión con JWT |
| OE2 | OT2.1 | OO2.1.2 | CU-O28: Administrar cuenta, sesión y cierre seguro | HU-28: Administración de cuenta y cierre seguro |
| OE2 | OT2.2: Integrar módulos comerciales | OO2.2.1: Administrar perfil comercial de hotel | CU-O12: Editar nombre comercial del hotel | HU-12: Edición de nombre comercial del hotel |
| OE2 | OT2.2 | OO2.2.2: Conectar habitaciones, tarifas, disponibilidad | CU-O14: Crear tipo de habitación | HU-14: Creación de tipo de habitación |
| OE2 | OT2.2 | OO2.2.2 | CU-O15: Actualizar inventario por fecha | HU-15: Actualización de inventario por fecha |
| OE2 | OT2.2 | OO2.2.2 | CU-O16: Registrar bloqueo de disponibilidad | HU-16: Bloqueo de disponibilidad |
| OE2 | OT2.2 | OO2.2.2 | CU-O17: Crear plan tarifario | HU-17: Creación de plan tarifario |
| OE2 | OT2.2 | OO2.2.2 | CU-O18: Configurar tarifa por fecha | HU-18: Configuración de tarifa por fecha |
| OE2 | OT2.2 | OO2.2.2 | CU-O20: Editar política hotelera | HU-20: Edición de política hotelera |
| OE3: Asegurar disponibilidad técnica | OT3.1: Mantener infraestructura portable | OO3.1.1-Ejecutar servicios Docker | *(Infraestructura — sin CU operativo directo)* | — |
| OE3 | OT3.1 | OO3.1.2-Monitorear servicios | *(Infraestructura — sin CU operativo directo)* | — |
| OE3 | OT3.2: Automatizar gobierno de datos | OO3.2.1: Ejecutar pipeline ETL | CU-O27: Consultar reporte de calidad de datos | HU-27: Consulta de reporte de calidad y registros rechazados |
| OE3 | OT3.2 | OO3.2.2: Registrar auditoría y trazabilidad | CU-O13: Consultar historial de cambios de propiedad | HU-13: Consulta de historial de cambios de propiedad |
| OE3 | OT3.2 | OO3.2.2 | CU-O28: Administrar cuenta y sesión | HU-28: Administración de cuenta y cierre seguro |
| OE4: Consolidar inteligencia de negocio | OT4.1: Consolidar analítica global | OO4.1.1: Consultar dashboard ejecutivo | CU-O26: Consultar reportes de revenue y mercado | HU-26: Consulta de reportes de revenue y mercado |
| OE4 | OT4.1 | OO4.1.2: Analizar mercados y destinos | CU-O26: Consultar reportes de revenue y mercado | HU-26: Consulta de reportes de revenue y mercado |
| OE4 | OT4.2: Aplicar BI y ML | OO4.2.1: Proyectar demanda y revenue | CU-O26: Consultar reportes de revenue y mercado | HU-26: Consulta de reportes de revenue y mercado |
| OE4 | OT4.2 | OO4.2.2: Detectar anomalías y calidad | CU-O27: Consultar reporte de calidad de datos | HU-27: Consulta de reporte de calidad y registros rechazados |
| OE2 | OT2.3: Enriquecer catálogo geoespacial | OO2.3.1: Editar metadata de destinos | CU-O31: Gestionar geolocalización y metadata | HU-31: Gestión de geolocalización y metadata |
| OE2 | OT2.3 | OO2.3.2: Editar nombre visible de hotel | CU-O31 | HU-31 |
| OE2 | OT2.3 | OO2.3.3: Visualizar destinos en mapa interactivo | CU-O31 | HU-31 |
| OE1 | OT1.2: Fortalecer reputación del huésped | OO1.2.3: Enviar notificaciones transaccionales | CU-O32: Gestionar notificaciones transaccionales | HU-32: Gestión de notificaciones transaccionales |
| OE3 | OT3.3: Automatizar gestión habitaciones | OO3.3.5: Gestionar alertas operativas internas | CU-O33: Gestionar alertas operativas al staff | HU-33: Gestión de alertas operativas |
| OE1 | OT1.1: Automatizar captación digital | OO1.1.3: Gestionar campañas promocionales multicanal | CU-O34: Gestionar campañas promocionales multicanal | HU-34: Gestión de campañas promocionales |
| OE1 | OT1.1 | OO1.1.4: Atender consultas con chatbot IA | CU-O35: Atender cliente mediante chatbot | HU-35: Atención mediante chatbot |
| OE1 | OT1.1 | OO1.1.5: Gestionar up-selling y ancillaries | CU-O36: Gestionar up-selling y ancillaries | HU-36: Gestión de up-selling |
| OE2 | OT2.3 | OO2.3.4: Gestionar contenidos multimedia con geolocalización | CU-O37: Gestionar contenidos multimedia geolocalizados | HU-37: Gestión de contenidos multimedia |

| OE3 | OT3.3: Automatizar gestión habitaciones | OO3.3.1: Consultar estado y disponibilidad de habitaciones | CU-O30: Gestionar disponibilidad y estado de habitaciones | HU-30: Gestión de disponibilidad y estado de habitaciones |
| OE3 | OT3.3 | OO3.3.2: Gestionar limpieza, rotación y housekeeping | CU-T14: Gestionar rotación y limpieza | HU-T14: Gestión de rotación y limpieza |
| OE3 | OT3.3 | OO3.3.3: Programar mantenimiento preventivo y correctivo | CU-T15: Programar mantenimiento preventivo y correctivo | HU-T15: Programación de mantenimiento preventivo |
| OE5 | OT5.1: Monitorear eficiencia operativa | OO5.1.1: Monitorear eficiencia, up-selling y ancillaries | CU-E09, CU-E10 | HU-E09, HU-E10 |

## 8.2 Trazabilidad por Caso de Uso

| Código CU | Nombre CU | OO Asociado | OE | Historia Gherkin (Sección 7) |
|-----------|-----------|-------------|----|------------------------------|
| CU-O01 | Iniciar sesión con JWT | OO2.1.2 | OE2 | §7.1 HU-O01 |
| CU-O02 | Buscar hoteles | OO1.1.1 | OE1 | §7.2 HU-O02 |
| CU-O03 | Filtrar y comparar hoteles | OO1.1.1 | OE1 | §7.3 HU-O03 |
| CU-O04 | Ver detalle de hotel | OO1.1.1 | OE1 | §7.4 HU-O04 |
| CU-O05 | Solicitar reserva | OO1.1.1 | OE1 | §7.5 HU-O05 |
| CU-O06 | Consultar mis reservas | OO1.1.1 | OE1 | §7.6 HU-O06 |
| CU-O07 | Cancelar reserva según política | OO1.1.1 | OE1 | §7.7 HU-O07 |
| CU-O08 | Registrar reserva manual | OO2.2.2 | OE2 | §7.8 HU-O08 |
| CU-O09 | Consultar solicitudes de reserva | OO2.2.2 | OE2 | §7.9 HU-O09 |
| CU-O10 | Completar check-in | OO2.2.2 | OE2 | §7.10 HU-O10 |
| CU-O11 | Completar check-out | OO2.2.2 | OE2 | §7.11 HU-O11 |
| CU-O12 | Editar nombre comercial del hotel | OO2.2.1 | OE2 | §7.12 HU-O12 |
| CU-O13 | Consultar historial de cambios | OO3.2.2 | OE3 | §7.13 HU-O13 |
| CU-O14 | Crear tipo de habitación | OO2.2.2 | OE2 | §7.14 HU-O14 |
| CU-O15 | Actualizar inventario por fecha | OO2.2.2 | OE2 | §7.15 HU-O15 |
| CU-O16 | Registrar bloqueo de disponibilidad | OO2.2.2 | OE2 | §7.16 HU-O16 |
| CU-O17 | Crear plan tarifario | OO2.2.2 | OE2 | §7.17 HU-O17 |
| CU-O18 | Configurar tarifa por fecha | OO2.2.2 | OE2 | §7.18 HU-O18 |
| CU-O19 | Crear promoción y cupón | OO1.1.2 | OE1 | §7.19 HU-O19 |
| CU-O20 | Editar política hotelera | OO2.2.2 | OE2 | §7.20 HU-O20 |
| CU-O21 | Actualizar amenities, imágenes y contenido | OO2.2.2 | OE2 | §7.21 HU-O21 |
| CU-O22 | Registrar reseña de estancia | OO1.2.1 | OE1 | §7.22 HU-O22 |
| CU-O23 | Moderar y responder reseña | OO1.2.1 | OE1 | §7.23 HU-O23 |
| CU-O24 | Generar comprobante o factura | OO1.2.2 | OE1 | §7.24 HU-O24 |
| CU-O25 | Registrar pago asociado a reserva | OO1.2.2 | OE1 | §7.25 HU-O25 |
| CU-O26 | Consultar reportes de revenue y mercado | OO1.1.2, OO4.1.1, OO4.1.2, OO4.2.1 | OE1, OE4 | §7.26 HU-O26 |
| CU-O27 | Consultar reporte de calidad de datos | OO3.2.1, OO4.2.2 | OE3, OE4 | §7.27 HU-O27 |
| CU-O28 | Administrar cuenta, sesión y cierre seguro | OO2.1.2, OO3.2.2 | OE2, OE3 | §7.28 HU-O28 |
| CU-O29 | Cambiar contraseña y actualizar perfil | OO2.1.2 | OE2 | §7.29 HU-O29 |
| CU-O30 | Gestionar disponibilidad y estado de habitaciones | OO3.3.1 | OE3 | §7.30 HU-O30 |
| CU-O31 | Gestionar geolocalización y metadata de contenido | OO2.3.1, OO2.3.2, OO2.3.3 | OE2 | §7.31 HU-O31 |
| CU-O32 | Gestionar notificaciones transaccionales al huésped | OO1.2.3 | OE1 | §7.32 HU-O32 |
| CU-O33 | Gestionar alertas operativas internas al staff | OO3.3.5 | OE3 | §7.33 HU-O33 |
| CU-O34 | Gestionar campañas promocionales multicanal | OO1.1.3 | OE1 | §7.34 HU-O34 |
| CU-O35 | Atender cliente mediante asistente virtual (chatbot) | OO1.1.4 | OE1 | §7.35 HU-O35 |
| CU-O36 | Gestionar up-selling y ancillaries | OO1.1.5 | OE1 | §7.36 HU-O36 |
| CU-O37 | Gestionar contenidos multimedia con geolocalización | OO2.3.4 | OE2 | §7.37 HU-O37 |
| CU-T14 | Gestionar rotación y limpieza (Táctico) | OO3.3.2 | OE3 | §7.38 HU-T14 |
| CU-T15 | Programar mantenimiento preventivo (Táctico) | OO3.3.3 | OE3 | §7.39 HU-T15 |
| CU-E09 | Monitorear eficiencia operativa (Estratégico) | OO5.1.1 | OE5 | §7.42 HU-E09 |
| CU-E10 | Gestionar ingresos por up-selling (Estratégico) | OO5.1.1 | OE1/OE4 | §7.43 HU-E10 |

