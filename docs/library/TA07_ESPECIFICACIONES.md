# TA07 — Documento de Especificaciones del Sistema HotelData

**Asignatura**: Construcción del Software — Sexto semestre
**Sistema**: HotelData — Plataforma de gestión hotelera y analítica
**Versión del documento**: 1.0 | **Fecha**: 2026-06-21
**Base**: TAF06 — Estrategia y Visión Arquitectónica

---

# 1. CONSTITUCIÓN DEL PROYECTO

## 1.1 La Empresa

HotelData es una plataforma web de gestión y analítica hotelera orientada a clientes, hoteles partner, gerentes, revenue managers, marketing hotelero, super administración, operadores y auditores de datos. Su propuesta combina una aplicación Angular, servicios FastAPI, base MongoDB, Redis, Docker y Airflow para sostener una operación hotelera digital con análisis de datos masivos.

Actualmente el sistema trabaja con 600 000 registros hoteleros procesados y organizados mediante colecciones de hechos y dimensiones. Esta base permite estudiar eventos de búsqueda, reservas, clicks, precios, promociones, destinos, países visitantes, canales, propiedades, tarifas y calidad de datos.

| Aspecto | Descripción | |---------|-------------| | **Tecnología principal** | Angular, FastAPI, MongoDB, Redis, Docker, Airflow | | **Qué hace** | Gestiona búsqueda, reservas, propiedades, habitaciones, disponibilidad, tarifas, políticas, amenities, reseñas, facturación/comprobantes, reportes y gobierno de datos | | **A quién sirve** | Clientes/viajeros, hoteles partner, gerentes, revenue managers, marketing hotelero, super administración, operadores y auditores de datos | | **Seguridad** | JWT, roles, permisos, rutas segmentadas y navegación por rol | | **Problema que resuelve** | Reduce dispersión operativa, mejora conversión digital, centraliza datos y permite decisiones de mercado basadas en BI | | **Modelo de datos** | Fact-Dim, dashboards, reportes y trazabilidad | | **Alcance actual** | Plataforma operativa y analítica con módulos de cliente, management, sistema, pipeline, auditoría, reseñas y facturación/comprobantes. 600 000 registros, endpoints JSON, validaciones y documentación técnica |
## 1.2 Misión

Brindar una plataforma digital confiable para gestionar reservas, propiedades hoteleras, datos operativos y analíticos, facilitando la adquisición automatizada de clientes, la administración hotelera, la integración con ecosistemas externos y la toma de decisiones basada en datos.

## 1.3 Visión

Ser una plataforma hotelera digital de referencia para mercados internacionales, reconocida por su capacidad de escalar comercialmente, integrarse mediante APIs, mantener alta disponibilidad y convertir datos hoteleros masivos en ventaja competitiva para hoteles y partners.

## 1.4 Objetivos del Proyecto

### Objetivo General

Implementar un sistema de gestión hotelera que cubra el ciclo operativo completo: desde la búsqueda y reserva del cliente hasta la administración de propiedades, tarifas, reseñas, facturación y reportes, todo sobre una arquitectura modular y escalable.

### Objetivos Específicos

| ID | Objetivo Específico | Alcance | |----|---------------------|---------| | ESP1 | Implementar autenticación segura con JWT, sesiones y RBAC de 9 roles | Sistema y seguridad | | ESP2 | Desarrollar el módulo de búsqueda y experiencia del cliente con filtros, detalle y comparación | Experiencia cliente | | ESP3 | Implementar el ciclo completo de reservas: solicitud, confirmación, check-in, check-out y cancelación | Core de reservas | | ESP4 | Desarrollar la gestión hotelera: tipos de habitación, inventario, tarifas, políticas, amenities e imágenes | Gestión hotelera | | ESP5 | Implementar el módulo de reseñas con registro, moderación y respuesta | Reputación online | | ESP6 | Desarrollar facturación y pagos asociados a reservas con trazabilidad | Respaldo documental | | ESP7 | Implementar reportes operativos de revenue, calidad de datos y mercado | Analítica y reportes | | ESP8 | Desarrollar el módulo de usuarios, roles, permisos y monitoreo del sistema | Administración del sistema |
---

# 2. RELACIÓN ORGANIZACIONAL (Táctico → Operativo) (Táctico → Operativo)

## 2.1 Niveles Organizacionales de HotelData (Táctico y Operativo) (Táctico y Operativo)

HotelData se estructura en tres niveles organizacionales que conectan la estrategia de negocio con la ejecución operativa diaria dentro del sistema.

| Nivel | Responsables | Qué define | Horizonte | |-------|-------------|-----------|-----------| | **Táctico** | Revenue manager, marketing hotelero, admin sistema, gerente hotel, partner | Campañas, tarifas, integraciones, dashboards, roles, disponibilidad, reportes y gestión operativa | Mediano plazo | | **Operativo** | Cliente, recepcionista, gerente hotel, auditor datos, sistema FastAPI/Airflow | Búsquedas, reservas, login JWT, check-in/out, cambios de perfil, reseñas, facturación, ETL y auditoría | Corto plazo |
## 2.3 Objetivos Tácticos (OT)

| Código | Objetivo Táctico | |--------|------------------| | **OT1.1** | Automatizar captación digital internacional mediante búsqueda, reserva, campañas y analítica de embudo | | **OT1.2** | Fortalecer reputación, confianza del huésped, reseñas, comprobantes y comunicación digital | | **OT2.1** | Estandarizar servicios por API, contratos JSON, seguridad JWT y documentación OpenAPI | | **OT2.2** | Integrar módulos comerciales y operativos: propiedades, habitaciones, tarifas, políticas, amenities y contenido | | **OT3.1** | Mantener infraestructura portable y escalable con Docker, Redis, MongoDB, Angular y FastAPI | | **OT3.2** | Automatizar procesamiento de datos, gobierno, ETL/ELT, calidad, auditoría y trazabilidad | | **OT4.1** | Consolidar analítica hotelera global mediante dashboards y reportes de management | | **OT4.2** | Aplicar BI, IA, modelos predictivos, segmentación, forecasting y detección de anomalías | | **OT2.3** | Enriquecer catálogo geoespacial de destinos con mapa interactivo y edición de metadata de nombres y coordenadas | | **OT3.3** | Automatizar gestión de limpieza, rotación, mantenimiento y cargos adicionales de habitaciones | | **OT5.1** | Monitorear eficiencia operativa mediante indicadores de limpieza, mantenimiento, ocupación y cargos adicionales |
## 2.4 Objetivos Operativos (OO)

| Código | Objetivo Operativo | OT asociado | |--------|-------------------|-------------| | **OO1.1.1** | Registrar eventos de búsqueda y reserva digital con país, destino, canal, hotel, fecha y usuario | OT1.1 | | **OO1.1.2** | Medir conversión de búsqueda, detalle, click, reserva, abandono y revenue por segmento | OT1.1 | | **OO1.2.1** | Registrar reseñas de estancia y respuestas del hotel con moderación y trazabilidad | OT1.2 | | **OO1.2.2** | Generar comprobantes/facturación y registro de pago asociado a la reserva | OT1.2 | | **OO2.1.1** | Exponer endpoints JSON para hoteles, reservas, management, sistema, auth y reportes | OT2.1 | | **OO2.1.2** | Validar JWT, sesión, permisos, rol y navegación por cada endpoint sensible | OT2.1 | | **OO2.2.1** | Administrar perfil comercial de hotel con nombres visibles manuales y prop_id estable | OT2.2 | | **OO2.2.2** | Conectar habitaciones, tarifas, disponibilidad, políticas, amenities e imágenes | OT2.2 | | **OO3.1.1** | Ejecutar servicios principales con Docker y configuración reproducible | OT3.1 | | **OO3.1.2** | Monitorear Redis, backend, contratos, health checks y estado de servicios | OT3.1 | | **OO3.2.1** | Ejecutar pipeline Airflow para cargar, validar y actualizar 600 000 registros incrementales | OT3.2 | | **OO3.2.2** | Registrar auditoría funcional, sesiones, cambios, historial y calidad de datos | OT3.2 | | **OO3.2.3** | Gestionar notificaciones automáticas del sistema con plantillas, canales y reglas de envío | OT3.2 | | **OO4.1.1** | Consultar dashboard ejecutivo con eventos, reservas, revenue, precio medio y calidad | OT4.1 | | **OO4.1.2** | Analizar mercados, destinos, canales, países visitantes y hoteles con mayor rendimiento | OT4.1 | | **OO4.2.1** | Proyectar demanda, revenue, conversión, ocupación y campañas por mercado | OT4.2 | | **OO4.2.2** | Detectar anomalías, registros rechazados, caídas de conversión e inconsistencias | OT4.2 | | **OO2.3.1** | Editar metadata de destinos (nombre visible, coordenadas geográficas, país, ciudad, descripción) | OT2.3 | | **OO2.3.2** | Editar nombre visible de hotel (manual_override sobre hoteles con ID numérico) | OT2.3 | | **OO2.3.3** | Visualizar destinos y hoteles en mapa mundial interactivo con geolocalización | OT2.3 | | **OO3.3.1** | Consultar estado actual, limpieza y disponibilidad de cada habitación individual | OT3.3 | | **OO3.3.2** | Gestionar rotación de limpieza y asignación de tareas de housekeeping | OT3.3 | | **OO3.3.3** | Programar y registrar mantenimiento preventivo de habitaciones e instalaciones | OT3.3 | | **OO3.3.4** | Registrar cargos adicionales a reserva (room service, daños, extras) | OT3.3 | | **OO3.3.5** | Validar ciclo de vida de reservas detectando anomalías en cambios de estado | OT3.3 | | **OO5.1.1** | Monitorear eficiencia operativa: tiempo de rotación, cumplimiento de mantenimiento, ocupación real vs disponible, cargos extra | OT5.1 |
## 2.5 Jerarquía Completa OE → OT → OO

```
  ├── OT1.1: Automatizar captación digital internacional
  │   ├── OO1.1.1: Registrar eventos de búsqueda y reserva
  │   └── OO1.1.2: Medir conversión del embudo digital
  └── OT1.2: Fortalecer reputación del huésped
      ├── OO1.2.1: Registrar reseñas de estancia
      └── OO1.2.2: Generar comprobantes/facturación

  ├── OT2.1: Estandarizar servicios por API
  │   ├── OO2.1.1: Exponer endpoints JSON
  │   └── OO2.1.2: Validar JWT y roles por endpoint
  ├── OT2.2: Integrar módulos comerciales y operativos
  │   ├── OO2.2.1: Administrar perfil comercial de hotel
  │   └── OO2.2.2: Conectar habitaciones, tarifas, disponibilidad
  └── OT2.3: Enriquecer catálogo geoespacial de destinos
      ├── OO2.3.1: Editar metadata de destinos
      ├── OO2.3.2: Editar nombre visible de hotel
      └── OO2.3.3: Visualizar destinos en mapa interactivo

  ├── OT3.1: Mantener infraestructura portable
  │   ├── OO3.1.1: Ejecutar servicios con Docker
  │   └── OO3.1.2: Monitorear Redis, backend, health checks
  ├── OT3.2: Automatizar procesamiento y gobierno de datos
  │   ├── OO3.2.1: Ejecutar pipeline ETL con Airflow
  │   ├── OO3.2.2: Registrar auditoría y trazabilidad
  │   └── OO3.2.3: Gestionar notificaciones automáticas del sistema
  └── OT3.3: Automatizar gestión de habitaciones
      ├── OO3.3.1: Consultar estado de habitaciones
      ├── OO3.3.2: Gestionar limpieza y rotación
      ├── OO3.3.3: Programar mantenimiento preventivo
      ├── OO3.3.4: Registrar cargos adicionales
      └── OO3.3.5: Validar ciclo de vida de reservas

  ├── OT4.1: Consolidar analítica hotelera global
  │   ├── OO4.1.1: Consultar dashboard ejecutivo
  │   └── OO4.1.2: Analizar mercados y destinos
  ├── OT4.2: Aplicar BI, IA y modelos predictivos
  │   ├── OO4.2.1: Proyectar demanda y revenue
  │   └── OO4.2.2: Detectar anomalías y problemas de calidad
  └── OT5.1: Monitorear eficiencia operativa
      └── OO5.1.1: Monitorear eficiencia operativa
```

---

# 3. DEPARTAMENTOS

## 3.1 Estructura Departamental de HotelData

La operación de HotelData se organiza en 9 departamentos que cubren todas las áreas funcionales del negocio hotelero digital. Cada departamento agrupa procesos, casos de uso y responsables específicos.

### Departamento 1: Comercial / Experiencia Cliente

| Elemento | Descripción | |----------|-------------| | **Responsable** | Gerente general / Marketing | | **Función** | Gestionar la experiencia del cliente desde la búsqueda hasta la reserva, maximizando la conversión y la satisfacción del viajero | | **Procesos** | Búsqueda de hoteles, filtros comerciales, comparación de alternativas, visualización de detalle, solicitud de reserva, consulta de historial, cancelación | | **Sistemas que usa** | Módulo de hoteles (búsqueda), módulo de reservas (solicitud), frontend Angular | | **CU asociados** | CU-O02, CU-O03, CU-O04, CU-O05, CU-O06, CU-O07 | | **KPIs** | Tasa de conversión, click rate, tiempo medio de reserva, revenue por cliente |
#### 1.1 Objetivos del Departamento

| ID | Objetivo del Departamento | Descripción | |----|--------------------------|-------------| | OD1.1 | Maximizar la tasa de conversión de búsqueda a reserva | Reducir la fricción en el proceso de búsqueda, comparación y reserva para que el mayor porcentaje posible de visitantes complete una reserva | | OD1.2 | Ofrecer una experiencia de búsqueda intuitiva y rápida | Proveer filtros inteligentes, comparación lado a lado y detalle enriquecido para que el cliente tome decisiones informadas en el menor tiempo posible | | OD1.3 | Facilitar la autogestión de reservas por parte del cliente | Permitir que el cliente consulte, modifique y cancele sus reservas sin intervención del personal del hotel | | OD1.4 | Incrementar el revenue por cliente | Mediante upselling visual de categorías superiores, sugerencias de mejora de habitación y promociones personalizadas durante el flujo de búsqueda |
#### 1.2 Actores Involucrados

| Actor | Rol en el Departamento | CU Asociados | |-------|----------------------|--------------| | **Cliente / Viajero** | Usuario final que busca, compara, reserva y gestiona sus reservas | CU-O02, CU-O03, CU-O04, CU-O05, CU-O06, CU-O07 | | **Gerente general / Marketing** | Responsable de definir las estrategias de conversión, campañas y contenido visual | CU-O02, CU-O03 (vista de resultados) | | **Sistema (FastAPI + MongoDB)** | Motor de búsqueda, cálculo de disponibilidad, generación de tarifas, persistencia de reservas | Todos los CU del departamento |
#### 1.3 Requisitos Funcionales

| ID RF | Nombre | Descripción | CU Asociado | HU Asociada | |-------|--------|-------------|-------------|-------------| | RF1.1 | Búsqueda por destino y fechas | El sistema debe permitir buscar hoteles por nombre de destino, fechas de entrada/salida y número de huéspedes | CU-O02 | HU-02 | | RF1.2 | Filtros comerciales | El sistema debe permitir filtrar resultados por precio mínimo/máximo, calificación mínima, amenities requeridas | CU-O03 | HU-03 | | RF1.3 | Comparación lado a lado | El sistema debe mostrar hasta 3 hoteles en vista comparativa con precio, rating, amenities y políticas | CU-O03 | HU-03 | | RF1.4 | Detalle completo de hotel | El sistema debe mostrar galería de imágenes, descripción, amenities, políticas, tarifas por tipo de habitación y reseñas | CU-O04 | HU-04 | | RF1.5 | Solicitud de reserva | El sistema debe permitir al cliente solicitar una reserva seleccionando tipo de habitación, fechas y datos de huéspedes, creando la orden en estado "pending" | CU-O05 | HU-05 | | RF1.6 | Consulta de reservas propias | El sistema debe mostrar al cliente el listado de sus reservas con estado, fechas, hotel y acciones disponibles | CU-O06 | HU-06 | | RF1.7 | Cancelación de reserva | El sistema debe permitir cancelar una reserva validando las políticas de cancelación del hotel y registrando la trazabilidad | CU-O07 | HU-07 | | RF1.8 | Cálculo de tarifas en tiempo real | El sistema debe calcular el total de la reserva sumando tarifas por noche desde `hotel_rate_calendar` | CU-O05 | HU-05 | | RF1.9 | Validación de disponibilidad | El sistema debe verificar disponibilidad en `room_inventory_calendar` antes de crear cualquier reserva | CU-O05 | HU-05 |
#### 1.4 Requisitos No Funcionales

| ID RNF | Nombre | Descripción | Categoría | |--------|--------|-------------|-----------| | RNF1.1 | Tiempo de respuesta de búsqueda | La búsqueda de hoteles no debe exceder 2 segundos bajo carga normal (< 100 peticiones concurrentes) | Rendimiento | | RNF1.2 | Disponibilidad del módulo de búsqueda | El módulo de búsqueda debe estar disponible 99.5% del tiempo en horario diurno (8:00-22:00) | Disponibilidad | | RNF1.3 | Consistencia de disponibilidad | La disponibilidad mostrada al cliente debe reflejar el estado real en el momento de la consulta (consistencia eventual máxima 5 segundos) | Consistencia | | RNF1.4 | Seguridad en reservas | Las reservas solo pueden crearse con usuario autenticado mediante JWT | Seguridad | | RNF1.5 | Escalabilidad de búsqueda | El motor de búsqueda debe soportar hasta 500 consultas simultáneas sin degradación significativa | Escalabilidad | | RNF1.6 | Usabilidad móvil | La interfaz de búsqueda, comparación y reserva debe ser responsiva y funcional en dispositivos móviles (320px-768px) | Usabilidad | | RNF1.7 | Integridad de precios | El precio calculado al solicitar la reserva debe ser el mismo que el mostrado en el detalle (no puede variar entre pantallas) | Integridad |
#### 1.5 Reglas de Negocio

| ID RN | Descripción | Origen | |-------|-------------|--------| | RN1.1 | Solo se muestran hoteles con al menos un tipo de habitación disponible en todas las noches solicitadas | Experiencia cliente | | RN1.2 | El precio mostrado es el precio mínimo por noche entre todos los tipos de habitación disponibles | Experiencia cliente | | RN1.3 | Los resultados se ordenan por precio ascendente por defecto | Experiencia cliente | | RN1.4 | Una reserva se crea siempre en estado "pending" — requiere confirmación del gerente del hotel para pasar a "confirmed" | Core de reservas | | RN1.5 | El inventario no se descuenta hasta que la reserva pasa a estado "confirmed" | Core de reservas | | RN1.6 | El precio total se calcula al momento de la solicitud y no varía después | Core de reservas | | RN1.7 | Una reserva debe tener al menos un huésped asociado | Core de reservas | | RN1.8 | Una reserva solo puede cancelarse si está en estado "pending" o "confirmed" | Core de reservas | | RN1.9 | La política de cancelación se obtiene del hotel (`hotel_policies.cancellation_policy`) y puede variar por hotel | Core de reservas | | RN1.10 | Los filtros de precio y rating se aplican sobre los datos de `dim_hotels` | Experiencia cliente |
#### 1.6 Escenarios de Operación

| ID Escenario | Nombre | CU | Descripción | |-------------|--------|----|-------------| | E1.1 | Búsqueda con resultados exitosos | CU-O02 | Cliente busca "Cancún" del 15 al 18 de julio, 2 adultos, 1 habitación. El sistema encuentra 25 hoteles con disponibilidad y muestra lista ordenada por precio | | E1.2 | Búsqueda sin resultados | CU-O02 | Cliente busca "Isla Inexistente". El sistema muestra mensaje de "No se encontraron hoteles" y sugiere modificar destino | | E1.3 | Filtro con resultados | CU-O03 | Cliente aplica filtro de precio $500-$1500 y rating ≥ 4 estrellas. La lista se reduce a 8 hoteles | | E1.4 | Comparación de 3 hoteles | CU-O03 | Cliente selecciona 3 hoteles y hace clic en "Comparar". El sistema muestra vista lado a lado con nombre, precio, rating, amenities | | E1.5 | Solicitud de reserva exitosa | CU-O05 | Cliente selecciona Suite Deluxe, ingresa datos de 2 huéspedes y confirma. El sistema crea booking_order en estado "pending" y muestra ID de reserva | | E1.6 | Cancelación dentro del período gratuito | CU-O07 | Cliente cancela reserva con 5 días de anticipación. El sistema aplica política de cancelación gratuita y libera inventario | | E1.7 | Cancelación con penalización | CU-O07 | Cliente cancela reserva 1 día antes del check-in. El sistema aplica cargo del 50% según política del hotel |
#### 1.7 Trazabilidad Individual del Departamento

| OT | OO | CU | HU | |----|----|----|----| | OT1.1: Automatizar captación digital internacional | OO1.1.1: Registrar eventos de búsqueda y reserva | CU-O02: Buscar hoteles | HU-02 | | OT1.1 | OO1.1.1 | CU-O03: Filtrar y comparar | HU-03 | | OT1.1 | OO1.1.1 | CU-O04: Ver detalle | HU-04 | | OT1.1 | OO1.1.1 | CU-O05: Solicitar reserva | HU-05 | | OT1.1 | OO1.1.1 | CU-O06: Consultar mis reservas | HU-06 | | OT1.1 | OO1.1.1 | CU-O07: Cancelar reserva | HU-07 |
#### 1.8 KPIs del Departamento

| KPI | Fórmula | Frecuencia | Meta | CU Asociado | |-----|---------|------------|------|-------------| | Tasa de conversión (búsqueda → reserva) | (Reservas creadas / Búsquedas totales) × 100 | Diaria | ≥ 3.5% | CU-O02, CU-O05 | | Click rate (búsqueda → detalle) | (Clics en detalle / Búsquedas totales) × 100 | Diaria | ≥ 25% | CU-O02, CU-O04 | | Tiempo medio de reserva | Tiempo promedio desde primera búsqueda hasta confirmación de reserva | Semanal | ≤ 30 minutos | CU-O02 → CU-O05 | | Revenue por cliente | Suma de totales de reserva / Número único de clientes | Mensual | Incremento ≥ 5% trimestral | CU-O05 | | Tasa de abandono de reserva | (Reservas iniciadas no completadas / Reservas iniciadas) × 100 | Diaria | ≤ 40% | CU-O05 | | Tasa de cancelación | (Reservas canceladas / Reservas totales) × 100 | Semanal | ≤ 15% | CU-O07 | | Precio promedio por noche | Suma de precios por noche / Número de noches reservadas | Semanal | — | CU-O05 |
#### 1.9 Colecciones MongoDB Involucradas

| Colección | Tipo de Acceso | Propósito | CU | |-----------|---------------|-----------|----| | `dim_hotels` | Lectura | Datos básicos de hoteles para búsqueda y visualización | CU-O02, CU-O03, CU-O04 | | `hotels` | Lectura | Datos maestros de hoteles | CU-O02, CU-O04 | | `locations` | Lectura | Ubicaciones y destinos | CU-O02 | | `room_types` | Lectura | Tipos de habitación disponibles por hotel | CU-O04, CU-O05 | | `room_inventory_calendar` | Lectura | Disponibilidad por fecha | CU-O02, CU-O05 | | `hotel_rate_calendar` | Lectura | Precios por fecha y tipo de habitación | CU-O02, CU-O04, CU-O05 | | `hotel_images` | Lectura | Galería de imágenes del hotel | CU-O03, CU-O04 | | `hotel_content_pages` | Lectura | Descripciones, highlights, amenities | CU-O04 | | `hotel_policies` | Lectura | Políticas de cancelación, check-in/out | CU-O04, CU-O07 | | `booking_orders` | Escritura | Creación y actualización de reservas | CU-O05, CU-O06, CU-O07 | | `booking_guests` | Escritura | Datos de huéspedes asociados a la reserva | CU-O05 | | `booking_status_history` | Escritura | Trazabilidad de cambios de estado | CU-O05, CU-O07 | | `user_activity_logs` | Escritura | Auditoría de acciones del cliente | CU-O05, CU-O07 |
#### 1.10 Flujo de Eventos del Departamento

El flujo completo del departamento Comercial / Experiencia Cliente cubre el ciclo de vida del cliente desde que llega al sistema hasta que finaliza su interacción con la reserva. A continuación se describe el flujo de eventos en secuencia:

```
Evento 1: Llegada del Cliente
  └── El cliente accede a la página de búsqueda (GET /hotels/search)
  └── CU-O02: El sistema muestra formulario de búsqueda con campos: destino, fechas, huéspedes
  └── Condición: El cliente puede estar autenticado o no (la búsqueda es pública)

Evento 2: Ejecución de Búsqueda
  └── El cliente ingresa parámetros y hace clic en "Buscar"
  └── CU-O02: El sistema consulta dim_hotels filtrando por destino
  └── CU-O02: El sistema cruza con room_inventory_calendar para verificar disponibilidad
  └── CU-O02: El sistema obtiene precio mínimo desde hotel_rate_calendar
  └── CU-O02: El sistema devuelve lista de hoteles con nombre, precio, rating, imagen
  └── Decisión: ¿Hay resultados? → Sí (Evento 3) | No → Muestra mensaje sin resultados

Evento 3: Refinamiento de Resultados
  └── CU-O03: El cliente aplica filtros (precio, rating, amenities)
  └── CU-O03: El sistema actualiza la lista según los filtros seleccionados
  └── Decisión: ¿Selecciona comparar? → Sí (Evento 4) | No → Evento 5

Evento 4: Comparación de Hoteles
  └── CU-O03: El cliente selecciona 2-3 hoteles y hace clic en "Comparar"
  └── CU-O03: El sistema muestra vista lado a lado con precio, rating, amenities, políticas
  └── Decisión: ¿Desea ver detalle? → Sí (Evento 5) | No → Evento 3

Evento 5: Visualización de Detalle
  └── CU-O04: El cliente hace clic en un hotel
  └── CU-O04: El sistema carga galería de imágenes, descripción, amenities, políticas, tarifas, reseñas
  └── Decisión: ¿Desea reservar? → Sí (Evento 6) | No → Evento 3

Evento 6: Inicio de Reserva
  └── CU-O05: El cliente selecciona tipo de habitación, fechas y cantidad
  └── CU-O05: El sistema muestra resumen: hotel, tipo habitación, fechas, total estimado
  └── Condición: El cliente debe estar autenticado
  └── Decisión: ¿Está autenticado? → Sí (Evento 7) | No → Redirige a login y regresa

Evento 7: Confirmación de Reserva
  └── CU-O05: El cliente ingresa datos de huéspedes (nombre, email, teléfono)
  └── CU-O05: El cliente confirma la reserva
  └── CU-O05: El sistema valida disponibilidad en room_inventory_calendar
  └── CU-O05: El sistema calcula total desde hotel_rate_calendar
  └── CU-O05: El sistema crea booking_orders en estado "pending"
  └── CU-O05: El sistema crea booking_guests asociados
  └── CU-O05: El sistema registra en booking_status_history con estado "created"

Evento 8: Post-Reserva
  └── CU-O06: El cliente consulta sus reservas desde "Mis reservas"
  └── CU-O06: El sistema muestra listado con estado, fechas, hotel, monto
  └── Decisión: ¿Desea cancelar? → Sí (Evento 9) | No → Fin del flujo

Evento 9: Cancelación de Reserva
  └── CU-O07: El cliente selecciona "Cancelar reserva"
  └── CU-O07: El sistema muestra diálogo con política de cancelación y posibles cargos
  └── CU-O07: El cliente confirma cancelación
  └── CU-O07: El sistema valida política en hotel_policies
  └── CU-O07: El sistema actualiza booking_orders a "cancelled"
  └── CU-O07: El sistema libera inventario en room_inventory_calendar (si estaba confirmed)
  └── CU-O07: El sistema registra en booking_status_history
```

#### 1.11 Fuera de Alcance del Departamento

| Aspecto | Fuera de Alcance | Departamento Responsable | |---------|-----------------|-------------------------| | Configuración de tarifas y precios | El departamento solo consulta tarifas, no las configura | Revenue Management | | Moderación de reseñas | El departamento comercial muestra reseñas pero no las modera | Marketing Hotelero | | Check-in y check-out presencial | El departamento solo gestiona la reserva, no la estancia física | Front Desk / Recepción | | Facturación y pagos | El departamento no genera facturas ni registra pagos | Facturación y Pagos | | Gestión de contenido del hotel | El departamento comercial solo consume contenido, no lo edita | Marketing Hotelero |
### Departamento 2: Revenue Management

| Elemento | Descripción | |----------|-------------| | **Responsable** | Revenue Manager | | **Función** | Configurar y optimizar tarifas, planes tarifarios, promociones y cupones para maximizar el ingreso por habitación disponible | | **Procesos** | Creación de planes tarifarios, configuración de tarifas por fecha, creación de promociones y cupones, análisis de revenue | | **Sistemas que usa** | Módulo revenue (tarifas, promociones), rate_plans, hotel_rate_calendar | | **CU asociados** | CU-O17, CU-O18, CU-O19, CU-O26, CU-O34 | | **KPIs** | ADR (Average Daily Rate), RevPAR, revenue bruto, precio promedio, ocupación |
#### 2.1 Objetivos del Departamento

| ID | Objetivo del Departamento | Descripción | |----|--------------------------|-------------| | OD2.1 | Maximizar el ingreso por habitación disponible (RevPAR) | Optimizar la combinación de tarifas, ocupación y promociones para maximizar el ingreso total por habitación en cada período | | OD2.2 | Implementar estrategias de precios dinámicos | Configurar tarifas diferenciadas por temporada, demanda anticipada, eventos especiales y canales de venta | | OD2.3 | Gestionar promociones y descuentos selectivos | Crear campañas promocionales y códigos de cupón para incentivar la demanda en períodos de baja ocupación | | OD2.4 | Registrar y analizar cargos adicionales | Capturar ingresos extras por servicios complementarios (room service, minibar, estacionamiento, daños) para incrementar el revenue total por huésped |
#### 2.2 Actores Involucrados

| Actor | Rol en el Departamento | CU Asociados | |-------|----------------------|--------------| | **Revenue Manager** | Responsable de definir estrategias de precios, crear planes tarifarios, configurar tarifas y analizar reportes | CU-O17, CU-O18, CU-O19, CU-O26 | | **Marketing Hotelero** | Crea promociones y cupones para campañas de descuento | CU-O19 | | **Gerente de hotel** | Consulta reportes de revenue para evaluar rendimiento de su propiedad | CU-O26 | | **Recepcionista / Gerente** | Registra cargos adicionales durante la estancia del huésped | CU-O34 | | **Sistema (FastAPI + MongoDB)** | Motor de cálculo de tarifas, persistencia de planes, promociones y cargos | Todos los CU del departamento |
#### 2.3 Requisitos Funcionales

| ID RF | Nombre | Descripción | CU Asociado | HU Asociada | |-------|--------|-------------|-------------|-------------| | RF2.1 | Creación de plan tarifario | El sistema debe permitir crear planes tarifarios con nombre, descripción, precio base, restricciones y política de cancelación | CU-O17 | HU-17 | | RF2.2 | Configuración de tarifa por fecha | El sistema debe permitir configurar precios específicos por fecha y plan tarifario en el calendario | CU-O18 | HU-18 | | RF2.3 | Creación de promociones | El sistema debe permitir crear campañas promocionales con descuento porcentual o monto fijo | CU-O19 | HU-19 | | RF2.4 | Generación de códigos de cupón | El sistema debe generar códigos de cupón únicos asociados a promociones con límite de usos y vigencia | CU-O19 | HU-19 | | RF2.5 | Consulta de reportes de revenue | El sistema debe mostrar dashboard con revenue total, ADR, RevPAR, precio promedio, top hoteles y destinos | CU-O26 | HU-26 | | RF2.6 | Registro de cargos adicionales | El sistema debe permitir registrar cargos adicionales a una reserva activa (room service, minibar, daños, estacionamiento) | CU-O34 | HU-34 | | RF2.7 | Cálculo de indicadores | El sistema debe calcular ADR, RevPAR, tasa de ocupación y precio promedio a partir de datos de fact tables | CU-O26 | HU-26 | | RF2.8 | Aplicación de promociones en tarifas | El sistema debe aplicar descuentos de promociones sobre las tarifas base al calcular el total de reserva | CU-O19 | HU-19 |
#### 2.4 Requisitos No Funcionales

| ID RNF | Nombre | Descripción | Categoría | |--------|--------|-------------|-----------| | RNF2.1 | Precisión de tarifas | Las tarifas configuradas deben reflejarse inmediatamente en búsqueda y detalle (latencia < 3 segundos) | Consistencia | | RNF2.2 | Control de concurrencia | La actualización de tarifas debe usar optimistic locking (campo version) para evitar sobrescrituras concurrentes | Concurrencia | | RNF2.3 | Historial de precios | El sistema debe mantener un historial de cambios de precios para auditoría (mínimo 90 días) | Auditoría | | RNF2.4 | Cálculo eficiente de reportes | Los reportes agregados deben calcularse en menos de 5 segundos para datasets de hasta 600K registros | Rendimiento | | RNF2.5 | Validación de descuentos | Los descuentos porcentuales no pueden exceder 100% — validación en frontend y backend | Seguridad |
#### 2.5 Reglas de Negocio

| ID RN | Descripción | Origen | |-------|-------------|--------| | RN2.1 | El nombre del plan tarifario debe ser único por propiedad | Revenue | | RN2.2 | El precio base por noche debe ser mayor que 0 | Revenue | | RN2.3 | Un plan tarifario puede asociarse a uno o varios tipos de habitación | Revenue | | RN2.4 | Un precio configurado en el calendario sobreescribe el precio base del plan para esa fecha | Revenue | | RN2.5 | Un descuento porcentual no puede exceder 100% | Revenue | | RN2.6 | Un código de cupón puede tener un límite de usos máximos (si no se especifica, es ilimitado dentro de la vigencia) | Revenue | | RN2.7 | Una promoción puede aplicarse a uno o varios hoteles y tipos de habitación | Revenue | | RN2.8 | El código de cupón debe ser único en el sistema | Revenue | | RN2.9 | Los cargos adicionales se suman al total de la factura final | Revenue | | RN2.10 | El monto del cargo adicional debe ser mayor a cero | Revenue |
#### 2.6 Escenarios de Operación

| ID Escenario | Nombre | CU | Descripción | |-------------|--------|----|-------------| | E2.1 | Creación de plan tarifario estándar | CU-O17 | Revenue manager crea plan "Tarifa Estándar" con precio base $1200, estadía mínima 1 noche, cancelación gratuita hasta 48h antes | | E2.2 | Configuración de tarifa de temporada alta | CU-O18 | Revenue manager configura precio $2500 para el plan "Tarifa Estándar" del 20-dic al 05-ene por temporada alta | | E2.3 | Creación de promoción con cupón | CU-O19 | Marketing crea promoción "Verano 2026" con 15% descuento, código "VERANO15", vigente del 01-jun al 31-ago, aplicable a todos los hoteles | | E2.4 | Registro de cargo adicional | CU-O34 | Recepcionista registra cargo de $450 por room service a la reserva #1234 durante la estancia del huésped | | E2.5 | Consulta de reporte mensual de revenue | CU-O26 | Gerente consulta reporte de julio 2026: revenue $1.2M, ADR $1,850, RevPAR $1,200, ocupación 72% | | E2.6 | Aplicación de cupón en reserva | CU-O19 | Cliente ingresa código "VERANO15" al solicitar reserva. El sistema aplica 15% descuento sobre tarifa base |
#### 2.7 Trazabilidad Individual del Departamento

| OT | OO | CU | HU | |----|----|----|----| | OT1.1: Automatizar captación digital | OO1.1.2: Medir conversión del embudo digital | CU-O26: Reportes de revenue | HU-26 | | OT2.2: Integrar módulos comerciales | OO2.2.2: Conectar habitaciones, tarifas, disponibilidad | CU-O17: Crear plan tarifario | HU-17 | | OT2.2 | OO2.2.2 | CU-O18: Configurar tarifa por fecha | HU-18 | | OT4.1: Consolidar analítica global | OO4.1.1: Consultar dashboard ejecutivo | CU-O26: Reportes de revenue | HU-26 | | OT4.2: Aplicar BI y ML | OO4.2.1: Proyectar demanda y revenue | CU-O26: Reportes de revenue | HU-26 | | OT3.3: Automatizar gestión habitaciones | OO3.3.4: Registrar cargos adicionales | CU-O34: Cargos adicionales | HU-34 |
#### 2.8 KPIs del Departamento

| KPI | Fórmula | Frecuencia | Meta | CU Asociado | |-----|---------|------------|------|-------------| | ADR (Average Daily Rate) | Revenue total habitaciones / Habitaciones ocupadas | Diaria | Incremento ≥ 3% anual | CU-O18 | | RevPAR (Revenue Per Available Room) | Revenue total habitaciones / Habitaciones disponibles | Diaria | ≥ $800 | CU-O18 | | Revenue bruto | Suma de price_usd donde reserva_bool = true | Mensual | — | CU-O26 | | Precio promedio | AVG(price_usd) sobre todos los eventos | Semanal | — | CU-O26 | | Tasa de ocupación | (Habitaciones ocupadas / Habitaciones disponibles) × 100 | Diaria | ≥ 65% anual | CU-O26 | | Ingreso por cargo adicional | Suma de cargos adicionales / Número de reservas | Mensual | ≥ $200/reserva | CU-O34 | | Tasa de uso de promociones | (Reservas con cupón / Reservas totales) × 100 | Mensual | ≥ 10% | CU-O19 |
#### 2.9 Colecciones MongoDB Involucradas

| Colección | Tipo de Acceso | Propósito | CU | |-----------|---------------|-----------|----| | `rate_plans` | Escritura | Creación y gestión de planes tarifarios | CU-O17 | | `rate_rules` | Lectura | Reglas de variación de tarifas | CU-O17 | | `hotel_rate_calendar` | Escritura | Precios por fecha y plan tarifario | CU-O18 | | `promotion_campaigns` | Escritura | Campañas promocionales | CU-O19 | | `coupon_codes` | Escritura | Códigos de cupón únicos | CU-O19 | | `additional_charges` | Escritura | Cargos adicionales por reserva | CU-O34 | | `fact_hotel_reservations` | Lectura | Datos analíticos para reportes de revenue | CU-O26 | | `dim_hotels` | Lectura | Datos de hoteles para reportes | CU-O26 | | `dim_destinations` | Lectura | Datos de destinos para reportes | CU-O26 | | `dim_visitor_countries` | Lectura | Datos de países para reportes | CU-O26 | | `dim_sites` | Lectura | Datos de canales para reportes | CU-O26 | | `dim_dates` | Lectura | Datos de fechas para reportes | CU-O26 | | `user_activity_logs` | Escritura | Auditoría de acciones del revenue manager | CU-O17, CU-O18, CU-O19 |
#### 2.10 Flujo de Eventos del Departamento

El flujo completo del departamento Revenue Management cubre desde la definición de planes tarifarios hasta el análisis de rendimiento:

```
Fase 1 — Definición de Estrategia de Precios
  └── CU-O17: Revenue manager crea plan tarifario con nombre, precio base y restricciones
  └── CU-O17: El sistema valida unicidad del nombre por propiedad
  └── CU-O17: El sistema guarda en rate_plans
  └── Decisión: ¿Plan con reglas especiales? → Sí: Configurar rate_rules | No: Siguiente fase

Fase 2 — Configuración de Tarifas en Calendario
  └── CU-O18: Revenue manager navega al calendario de tarifas
  └── CU-O18: El sistema muestra precios actuales por fecha y plan tarifario
  └── CU-O18: Revenue manager selecciona fecha/rango y asigna nuevo precio
  └── CU-O18: El sistema valida precio > 0
  └── CU-O18: El sistema crea/actualiza hotel_rate_calendar

Fase 3 — Creación de Promociones y Cupones
  └── CU-O19: Marketing o revenue manager crea campaña promocional
  └── CU-O19: El sistema genera código de cupón único
  └── CU-O19: El sistema guarda promoción en promotion_campaigns y cupón en coupon_codes
  └── Decisión: ¿Aplicar a hoteles específicos? → Sí: Asignar prop_ids | No: Aplicar a todos

Fase 4 — Operación Diaria: Cargos Adicionales
  └── El huésped solicita un servicio extra durante su estancia
  └── CU-O34: Recepcionista registra cargo adicional a la reserva
  └── CU-O34: El sistema valida que la reserva esté en estado "confirmed" o "checked_in"
  └── CU-O34: El sistema crea registro en additional_charges
  └── CU-O34: El sistema actualiza el total pendiente de la reserva

Fase 5 — Análisis y Reportes
  └── CU-O26: Gerente o revenue manager consulta dashboard de revenue
  └── CU-O26: El sistema agrega datos desde fact_hotel_reservations
  └── CU-O26: El sistema calcula ADR, RevPAR, ocupación, precio promedio
  └── CU-O26: El sistema muestra top hoteles, destinos y países por revenue
  └── Decisión: ¿Exportar reporte? → Sí: Exportar CSV/JSON | No: Fin del flujo
```

#### 2.11 Fuera de Alcance del Departamento

| Aspecto | Fuera de Alcance | Departamento Responsable | |---------|-----------------|-------------------------| | Gestión de contenido del hotel | El revenue no edita descripciones ni imágenes | Marketing Hotelero | | Moderación de reseñas | El revenue no modera reseñas de huéspedes | Marketing Hotelero | | Configuración de usuarios y roles | El revenue no gestiona cuentas de usuario | Administración / Sistemas | | Ejecución del pipeline ETL | El revenue consume datos analíticos, no ejecuta ETL | Datos / Analítica | | Check-in y check-out presencial | El revenue no participa en la operación de front desk | Operaciones Hoteleras |
### Departamento 3: Marketing Hotelero

| Elemento | Descripción | |----------|-------------| | **Responsable** | Marketing hotelero | | **Función** | Gestionar la reputación online, contenido comercial, imágenes, amenities y campañas de promoción para atraer y retener huéspedes | | **Procesos** | Gestión de reseñas, moderación y respuesta, actualización de contenido, imágenes, amenities, edición de nombre comercial | | **Sistemas que usa** | Módulo de reseñas, módulo partner (contenido, imágenes), frontend Angular | | **CU asociados** | CU-O12, CU-O21, CU-O22, CU-O23, CU-O36 | | **KPIs** | Puntuación promedio de reseñas, tasa de reseñas respondidas, completitud de perfil |
#### 3.1 Objetivos del Departamento

| ID | Objetivo del Departamento | Descripción | |----|--------------------------|-------------| | OD3.1 | Gestionar la reputación online de las propiedades | Moderar y responder reseñas de huéspedes para mantener una imagen positiva y construir confianza con potenciales clientes | | OD3.2 | Mantener contenido comercial actualizado y atractivo | Administrar descripciones, amenities, imágenes y nombres comerciales para maximizar el atractivo de cada propiedad en buscadores y detalle | | OD3.3 | Incrementar la tasa de reseñas positivas | Fomentar que los huéspedes dejen reseñas después de su estancia y gestionar la respuesta del hotel para mejorar la puntuación general | | OD3.4 | Asegurar la consistencia del perfil del hotel | Mantener actualizados los datos comerciales (nombre, descripción, amenities) y evitar sobrescritura por ETL mediante manual override |
#### 3.2 Actores Involucrados

| Actor | Rol en el Departamento | CU Asociados | |-------|----------------------|--------------| | **Marketing Hotelero** | Gestiona contenido, imágenes, amenities, reseñas y nombre comercial | CU-O12, CU-O21, CU-O22, CU-O23 | | **Hotel Partner** | Edita nombre comercial y contenido de su propia propiedad | CU-O12, CU-O21 | | **Cliente / Viajero** | Registra reseñas de estancia después del check-out | CU-O22 | | **Super Admin** | Moderación avanzada y resolución de disputas de reseñas | CU-O23 | | **Sistema** | Dual-write a fact_reviews, moderación automática, validación de contenido | Todos los CU del departamento |
#### 3.3 Requisitos Funcionales

| ID RF | Nombre | Descripción | CU Asociado | HU Asociada | |-------|--------|-------------|-------------|-------------| | RF3.1 | Edición de nombre comercial | El sistema debe permitir editar el nombre visible del hotel activando manual_override para evitar sobrescritura ETL | CU-O12 | HU-12 | | RF3.2 | Registro de reseña | El sistema debe permitir al cliente registrar reseña con calificación general y por categorías, comentario y fotos opcionales | CU-O22 | HU-22 | | RF3.3 | Moderación de reseñas | El sistema debe permitir aprobar o rechazar reseñas pendientes con motivo de rechazo | CU-O23 | HU-23 | | RF3.4 | Respuesta a reseñas | El sistema debe permitir escribir respuesta pública a reseñas aprobadas | CU-O23 | HU-23 | | RF3.5 | Moderación automática | El sistema debe aprobar automáticamente reseñas con calificación ≥ 4 (alto nivel de confianza) | CU-O23 | HU-23 | | RF3.6 | Gestión de amenities | El sistema debe permitir seleccionar amenities del catálogo predefinido para la propiedad | CU-O21 | HU-21 | | RF3.7 | Subida de imágenes | El sistema debe permitir subir imágenes en formato JPEG/PNG (máx 5MB) con almacenamiento en MongoDB | CU-O21 | HU-21 | | RF3.8 | Dual-write a fact_reviews | El sistema debe escribir simultáneamente en `reviews` y `fact_reviews` para alimentar métricas analíticas | CU-O22, CU-O23 | HU-22, HU-23 | | RF3.9 | Historial de cambios de perfil | El sistema debe registrar todos los cambios de contenido en `hotel_profile_changes` para trazabilidad | CU-O12, CU-O21 | HU-12, HU-21 |
#### 3.4 Requisitos No Funcionales

| ID RNF | Nombre | Descripción | Categoría | |--------|--------|-------------|-----------| | RNF3.1 | Protección contra reseñas duplicadas | El sistema debe impedir que un cliente reseñe más de una vez la misma reserva | Integridad | | RNF3.2 | Tiempo de moderación | Las reseñas pendientes deben ser moderadas en menos de 48 horas para mantener la experiencia del usuario | SLA | | RNF3.3 | Consistencia de imagen | Las imágenes almacenadas en MongoDB deben servirse con tiempos de carga < 2 segundos | Rendimiento | | RNF3.4 | Validación de tamaño de imagen | Las imágenes subidas no deben exceder 5MB con validación en frontend y backend | Seguridad | | RNF3.5 | Trazabilidad de cambios | Todos los cambios de contenido deben quedar registrados con usuario responsable y timestamp | Auditoría |
#### 3.5 Reglas de Negocio

| ID RN | Descripción | Origen | |-------|-------------|--------| | RN3.1 | El `prop_id` es la clave técnica inmutable de la propiedad y nunca debe cambiar | Partner | | RN3.2 | `manual_override` impide que el ETL sobrescriba el nombre editado manualmente | Partner | | RN3.3 | Solo clientes con reserva completada (checked_out) pueden reseñar | Reseñas | | RN3.4 | Una reseña por reserva (no se pueden reseñar múltiples veces la misma estancia) | Reseñas | | RN3.5 | Las reseñas se crean en estado "pending" y deben ser moderadas antes de ser públicas | Reseñas | | RN3.6 | Las reseñas con calificación ≥ 4 se aprueban automáticamente | Reseñas | | RN3.7 | Una reseña aprobada no puede eliminarse (solo desactivarse como "hidden") | Reseñas | | RN3.8 | Las imágenes deben estar en formato JPEG o PNG, tamaño máximo 5MB cada una | Contenido | | RN3.9 | Las amenities se seleccionan de un catálogo predefinido (`system_catalogs`) | Contenido | | RN3.10 | Todos los cambios críticos de perfil quedan registrados en `hotel_profile_changes` para trazabilidad | Partner |
#### 3.6 Escenarios de Operación

| ID Escenario | Nombre | CU | Descripción | |-------------|--------|----|-------------| | E3.1 | Edición de nombre comercial de hotel | CU-O12 | Marketing cambia nombre de "Property 8250" a "Hotel Paraíso Caribe". El sistema activa manual_override y registra en hotel_profile_changes | | E3.2 | Actualización de amenities e imágenes | CU-O21 | Marketing agrega amenities "WiFi, Piscina, Gimnasio" y sube 5 imágenes del hotel renovado | | E3.3 | Registro de reseña post-estancia | CU-O22 | Cliente después del check-out reseña con 4 estrellas y comentario "Excelente ubicación y servicio". El sistema crea review en estado "pending" | | E3.4 | Moderación y aprobación de reseña | CU-O23 | Moderador aprueba reseña pendiente con calificación 4. El sistema cambia estado a "approved" y la hace visible | | E3.5 | Moderación y rechazo de reseña | CU-O23 | Moderador rechaza reseña con calificación 1 por "Contenido inapropiado". El sistema cambia a "rejected" y no se publica | | E3.6 | Respuesta del hotel a reseña | CU-O23 | Marketing responde "Agradecemos sus comentarios, nos esforzamos por mejorar" a una reseña aprobada |
#### 3.7 Trazabilidad Individual del Departamento

| OT | OO | CU | HU | |----|----|----|----| | OT1.2: Fortalecer reputación del huésped | OO1.2.1: Registrar reseñas de estancia | CU-O22: Registrar reseña | HU-22 | | OT1.2 | OO1.2.1 | CU-O23: Moderar y responder reseña | HU-23 | | OT2.2: Integrar módulos comerciales | OO2.2.1: Administrar perfil comercial de hotel | CU-O12: Editar nombre comercial | HU-12 | | OT2.2 | OO2.2.2: Conectar habitaciones, tarifas, disponibilidad | CU-O21: Actualizar amenities, imágenes y contenido | HU-21 | | OT2.3 | OO2.3.2: Editar nombre visible de hotel | CU-O36: Manual override | HU-36 |
#### 3.8 KPIs del Departamento

| KPI | Fórmula | Frecuencia | Meta | CU Asociado | |-----|---------|------------|------|-------------| | Puntuación promedio de reseñas | AVG(calificación_general) de todas las reseñas aprobadas | Semanal | ≥ 4.0 | CU-O22, CU-O23 | | Tasa de reseñas respondidas | (Reseñas con respuesta / Reseñas aprobadas) × 100 | Mensual | ≥ 80% | CU-O23 | | Completitud de perfil del hotel | (% de campos completados en contenido del hotel) | Mensual | ≥ 90% | CU-O21 | | Tasa de reseñas por estancia | (Reseñas registradas / Check-outs totales) × 100 | Mensual | ≥ 20% | CU-O22 | | Tiempo medio de moderación | Tiempo promedio desde creación hasta moderación de reseña | Semanal | ≤ 24 horas | CU-O23 | | Número de imágenes por hotel | AVG(conteo de imágenes en hotel_images) | Mensual | ≥ 10 | CU-O21 | | Tasa de rechazo de reseñas | (Reseñas rechazadas / Reseñas totales) × 100 | Mensual | ≤ 10% | CU-O23 |
#### 3.9 Colecciones MongoDB Involucradas

| Colección | Tipo de Acceso | Propósito | CU | |-----------|---------------|-----------|----| | `dim_hotels` | Actualización | Actualización de hotel_name y manual_override | CU-O12, CU-O36 | | `hotel_profile_changes` | Escritura | Registro de cambios de perfil | CU-O12 | | `hotel_content_pages` | Actualización | Descripciones, amenities, highlights | CU-O21 | | `hotel_images` | Actualización | Galería de imágenes del hotel | CU-O21 | | `hotel_content_changes` | Escritura | Registro de cambios de contenido | CU-O21 | | `system_catalogs` | Lectura | Catálogo predefinido de amenities | CU-O21 | | `reviews` | Escritura | Creación, moderación y respuesta de reseñas | CU-O22, CU-O23 | | `fact_reviews` | Escritura | Dual-write analítico de reseñas | CU-O22, CU-O23 | | `user_activity_logs` | Escritura | Auditoría de acciones | CU-O12, CU-O21, CU-O22, CU-O23 | | `hotel_edit_history` | Escritura | Registro de ediciones de perfil | CU-O12 |
#### 3.10 Flujo de Eventos del Departamento

El flujo de Marketing Hotelero abarca tres líneas de trabajo paralelas: gestión de contenido comercial, ciclo de vida de reseñas y administración de perfil:

```
Línea A — Gestión de Contenido Comercial
  └── CU-O21: Marketing navega al gestor de contenido del hotel
  └── CU-O21: El sistema carga contenido actual desde hotel_content_pages, hotel_images, system_catalogs
  └── CU-O21: Marketing selecciona/desmarca amenities del catálogo
  └── CU-O21: Marketing edita descripciones y highlights
  └── CU-O21: Marketing sube/elimina imágenes (validación: JPEG/PNG, máx 5MB)
  └── CU-O21: Marketing guarda cambios
  └── CU-O21: El sistema actualiza hotel_content_pages y hotel_images
  └── CU-O21: El sistema registra en hotel_content_changes

Línea B — Edición de Nombre Comercial
  └── CU-O12: Marketing o partner navega a edición de perfil del hotel
  └── CU-O12: El sistema muestra formulario con campos editables (display_name, hotel_name)
  └── Decisión: ¿El nombre actual es numérico? → Sí: CU-O36 (manual override) | No: Edición normal
  └── CU-O12: Marketing modifica nombre comercial
  └── CU-O12: El sistema valida que prop_id no se intente modificar
  └── CU-O12: El sistema actualiza dim_hotels con manual_override = true
  └── CU-O12: El sistema registra en hotel_profile_changes

Línea C — Ciclo de Vida de Reseñas
  └── Evento externo: Check-out completado → Cliente puede reseñar
  └── CU-O22: Cliente navega a sección de reseñas desde reserva completada
  └── CU-O22: El sistema verifica que la reserva esté en "checked_out"
  └── CU-O22: Cliente ingresa calificación y comentario
  └── CU-O22: El sistema crea review en estado "pending"
  └── CU-O22: El sistema realiza dual-write a fact_reviews
  └── Decisión: ¿Calificación ≥ 4? → Sí: Aprobación automática | No: Pendiente de moderación manual
  └── CU-O23: Moderador revisa reseñas pendientes
  └── CU-O23: Moderador aprueba o rechaza con motivo
  └── Decisión: ¿Aprobada y necesita respuesta? → Sí: CU-O23 responder | No: Fin
  └── CU-O23: Moderador escribe respuesta pública
  └── CU-O23: El sistema guarda respuesta en reviews.hotel_response
```

#### 3.11 Fuera de Alcance del Departamento

| Aspecto | Fuera de Alcance | Departamento Responsable | |---------|-----------------|-------------------------| | Configuración de tarifas y precios | Marketing no configura tarifas ni planes tarifarios | Revenue Management | | Gestión de inventario de habitaciones | Marketing no administra disponibilidad ni bloqueos | Operaciones Hoteleras | | Facturación y pagos | Marketing no genera facturas ni registra pagos | Facturación y Pagos | | Administración de usuarios | Marketing no gestiona cuentas ni roles | Administración / Sistemas | | Ejecución de pipeline ETL | Marketing no ejecuta procesos de calidad de datos | Datos / Analítica |
### Departamento 4: Operaciones Hoteleras

| Elemento | Descripción | |----------|-------------| | **Responsable** | Recepcionista / Gerente de hotel / Hotel partner | | **Función** | Ejecutar la operación diaria del hotel: atención al huésped en front desk, check-in/out, reservas manuales, facturación, gestión de tipos de habitación, inventario, disponibilidad y políticas | | **Procesos** | Check-in, check-out, reservas manuales, facturación, pagos, consulta de solicitudes, creación de tipos de habitación, actualización de inventario, bloqueos, gestión de políticas | | **Sistemas que usa** | Módulo partner (rooms, availability, policies), módulo reservas (check-in/out), módulo billing (facturas, pagos) | | **CU asociados** | CU-O08 (Recepcionista), CU-O09 (Gerente), CU-O10 (Recepcionista), CU-O11 (Recepcionista), CU-O14, CU-O15 (Gerente), CU-O16 (Gerente), CU-O20, CU-O24 (Recepcionista), CU-O25 (Recepcionista), CU-O30, CU-O31, CU-O32, CU-O33, CU-O39, CU-O40 | | **KPIs** | Ocupación, días de inventario configurado, check-ins/outs por día, tiempo de estancia media |
#### 4.1 Objetivos del Departamento

| ID | Objetivo del Departamento | Descripción | |----|--------------------------|-------------| | OD4.1 | Gestionar el ciclo completo de atención al huésped en front desk | Ejecutar check-in, check-out, reservas manuales (walk-in, telefónicas) y facturación en el momento de la estancia | | OD4.2 | Administrar la configuración de habitaciones y disponibilidad | Crear tipos de habitación, actualizar inventario diario, registrar bloqueos y gestionar políticas hoteleras | | OD4.3 | Optimizar la ocupación y el uso del inventario | Mantener el inventario actualizado por fecha para maximizar la disponibilidad y evitar overbooking | | OD4.4 | Proveer atención personalizada al huésped | Registrar cargos adicionales, gestionar solicitudes especiales y asegurar una estancia sin contratiempos |
#### 4.2 Actores Involucrados

| Actor | Rol en el Departamento | CU Asociados | |-------|----------------------|--------------| | **Recepcionista** | Ejecuta la operación diaria de front desk: check-in, check-out, reservas manuales, facturación, pagos y consulta de estado de habitaciones | CU-O08, CU-O10, CU-O11, CU-O24, CU-O25, CU-O30, CU-O31, CU-O32, CU-O34, CU-O39 | | **Gerente de hotel** | Supervisa operaciones, confirma/rechaza solicitudes de reserva, gestiona inventario y bloqueos, programa mantenimiento | CU-O09, CU-O15, CU-O16, CU-O30, CU-O31, CU-O32, CU-O39, CU-O40 | | **Hotel partner** | Define tipos de habitación, políticas hoteleras y amenities de su propiedad | CU-O14, CU-O20, CU-O33 | | **Sistema** | Persistencia de reservas, actualización de inventario, cálculo de tarifas, generación de facturas | Todos los CU del departamento |
#### 4.3 Requisitos Funcionales

| ID RF | Nombre | Descripción | CU Asociado | HU Asociada | |-------|--------|-------------|-------------|-------------| | RF4.1 | Reserva manual | El sistema debe permitir al recepcionista crear una reserva directamente en estado "confirmed" para walk-ins y reservas telefónicas | CU-O08 | HU-08 | | RF4.2 | Consulta de solicitudes | El sistema debe mostrar al gerente las reservas en estado "pending" para su propiedad | CU-O09 | HU-09 | | RF4.3 | Confirmación/rechazo de solicitud | El sistema debe permitir al gerente confirmar (→ "confirmed") o rechazar (→ "cancelled") una solicitud de reserva | CU-O09 | HU-09 | | RF4.4 | Check-in | El sistema debe permitir cambiar el estado de una reserva de "confirmed" a "checked_in" registrando la llegada del huésped | CU-O10 | HU-10 | | RF4.5 | Check-out | El sistema debe permitir cambiar el estado de "checked_in" a "checked_out" liberando el inventario | CU-O11 | HU-11 | | RF4.6 | Creación de tipo de habitación | El sistema debe permitir crear tipos de habitación con nombre, capacidad, descripción y amenities | CU-O14 | HU-14 | | RF4.7 | Actualización de inventario | El sistema debe permitir actualizar el inventario disponible por fecha con optimistic locking | CU-O15 | HU-15 | | RF4.8 | Bloqueo de disponibilidad | El sistema debe permitir bloquear rangos de fechas para tipos de habitación específicos | CU-O16 | HU-16 | | RF4.9 | Edición de políticas hoteleras | El sistema debe permitir configurar horarios, políticas de cancelación, mascotas y condiciones | CU-O20 | HU-20 | | RF4.10 | Consulta de estado de habitaciones | El sistema debe mostrar matriz visual del estado de todas las habitaciones con código de colores | CU-O30 | HU-30 | | RF4.11 | Asignación de tipo de habitación | El sistema debe permitir cambiar el tipo de habitación a una habitación física individual | CU-O31 | HU-31 | | RF4.12 | Consulta de disponibilidad por habitación | El sistema debe mostrar calendario de 90 días con ocupación, bloqueos y mantenimiento | CU-O32 | HU-32 | | RF4.13 | Gestión de amenities por tipo de habitación | El sistema debe permitir configurar amenities específicos por tipo de habitación | CU-O33 | HU-33 |
#### 4.4 Requisitos No Funcionales

| ID RNF | Nombre | Descripción | Categoría | |--------|--------|-------------|-----------| | RNF4.1 | Control de concurrencia en inventario | La actualización de inventario debe usar optimistic locking con campo version para evitar conflictos | Concurrencia | | RNF4.2 | Tiempo de respuesta en check-in | El check-in debe completarse en menos de 3 segundos para no afectar la atención al huésped | Rendimiento | | RNF4.3 | Consistencia de inventario | El inventario disponible nunca debe ser negativo ni exceder el total | Integridad | | RNF4.4 | Disponibilidad del módulo de front desk | El módulo debe estar disponible 24/7 con tolerancia a fallos (hotel opera 365 días) | Disponibilidad | | RNF4.5 | Validación de reservas manuales | Las reservas manuales solo pueden ser creadas por roles autorizados (recepcionista, hotel_partner) | Seguridad | | RNF4.6 | Trazabilidad de cambios de estado | Todos los cambios de estado de reserva deben registrarse en booking_status_history | Auditoría |
#### 4.5 Reglas de Negocio

| ID RN | Descripción | Origen | |-------|-------------|--------| | RN4.1 | La reserva manual se crea en estado "confirmed" directamente, no "pending" | Front desk | | RN4.2 | El inventario se descuenta inmediatamente al crear la reserva manual | Front desk | | RN4.3 | Una solicitud en "pending" que no se confirma en 24 horas se cancela automáticamente | Front desk | | RN4.4 | Solo reservas en estado "confirmed" pueden hacer check-in | Front desk | | RN4.5 | El check-in solo puede completarse en la fecha de check-in o posterior | Front desk | | RN4.6 | Una vez en "checked_in", la reserva no puede cancelarse (solo por excepción del gerente) | Front desk | | RN4.7 | Solo reservas en estado "checked_in" pueden hacer check-out | Front desk | | RN4.8 | Un "checked_out" es el estado final del ciclo de vida de la reserva | Front desk | | RN4.9 | El nombre del tipo de habitación debe ser único por propiedad | Gestión habitaciones | | RN4.10 | El inventario disponible no puede exceder el inventario total | Gestión habitaciones | | RN4.11 | El inventario bloqueado + reservado no puede exceder el inventario total | Gestión habitaciones | | RN4.12 | Una habitación se considera disponible si no tiene booking en estado confirmed/checked_in para esa noche | Gestión habitaciones |
#### 4.6 Escenarios de Operación

| ID Escenario | Nombre | CU | Descripción | |-------------|--------|----|-------------| | E4.1 | Reserva manual walk-in | CU-O08 | Huésped llega sin reserva. Recepcionista crea reserva manual con tipo "Estándar", 2 noches, $2,400 total. El sistema crea en estado "confirmed" | | E4.2 | Confirmación de solicitud pendiente | CU-O09 | Gerente revisa solicitud de reserva #5678 y hace clic en "Confirmar". El sistema cambia a "confirmed" y descuenta inventario | | E4.3 | Check-in exitoso | CU-O10 | Huésped llega al hotel. Recepcionista busca reserva #5678 y completa check-in. El sistema cambia estado a "checked_in" | | E4.4 | Check-out con liberación de inventario | CU-O11 | Huésped finaliza estancia. Recepcionista completa check-out. El sistema cambia a "checked_out" y libera inventario | | E4.5 | Creación de tipo de habitación "Suite Ejecutiva" | CU-O14 | Partner crea tipo "Suite Ejecutiva", capacidad 3 adultos, descripción "Suite con vista al mar", 10 habitaciones físicas | | E4.6 | Actualización de inventario por fecha | CU-O15 | Gerente actualiza inventario del 15-jul para tipo "Estándar" a 20 habitaciones disponibles. El sistema aplica optimistic locking | | E4.7 | Bloqueo por mantenimiento | CU-O16 | Gerente bloquea 5 habitaciones tipo "Estándar" del 01-ago al 05-ago por mantenimiento de HVAC | | E4.8 | Consulta de matriz de estado de habitaciones | CU-O30 | Recepcionista abre panel de estado y ve matriz visual: 15 verdes, 8 rojas, 2 amarillas, 1 gris |
#### 4.7 Trazabilidad Individual del Departamento

| OT | OO | CU | HU | |----|----|----|----| | OT2.2: Integrar módulos comerciales | OO2.2.2: Conectar habitaciones, tarifas, disponibilidad | CU-O14: Crear tipo habitación | HU-14 | | OT2.2 | OO2.2.2 | CU-O15: Actualizar inventario | HU-15 | | OT2.2 | OO2.2.2 | CU-O16: Bloquear disponibilidad | HU-16 | | OT2.2 | OO2.2.2 | CU-O20: Editar políticas | HU-20 | | OT2.2 | OO2.2.2 | CU-O08: Reserva manual | HU-08 | | OT2.2 | OO2.2.2 | CU-O09: Solicitudes reserva | HU-09 | | OT2.2 | OO2.2.2 | CU-O10: Check-in | HU-10 | | OT2.2 | OO2.2.2 | CU-O11: Check-out | HU-11 | | OT3.3: Automatizar gestión habitaciones | OO3.3.1: Consultar estado habitaciones | CU-O30: Estado habitaciones | HU-30 | | OT3.3 | OO3.3.1 | CU-O31: Asignar tipo habitación | HU-31 | | OT3.3 | OO3.3.1 | CU-O32: Disponibilidad por habitación | HU-32 | | OT3.3 | OO3.3.1 | CU-O33: Amenities por tipo habitación | HU-33 | | OT3.3 | OO3.3.2 | CU-O39: Limpieza y rotación | HU-39 | | OT3.3 | OO3.3.3 | CU-O40: Mantenimiento preventivo | HU-40 |
#### 4.8 KPIs del Departamento

| KPI | Fórmula | Frecuencia | Meta | CU Asociado | |-----|---------|------------|------|-------------| | Tasa de ocupación | (Habitaciones ocupadas / Habitaciones totales) × 100 | Diaria | ≥ 70% | CU-O30 | | Días de inventario configurado | Días con inventario actualizado en los últimos 90 días | Mensual | ≥ 85 días | CU-O15 | | Check-ins por día | Conteo de check-ins completados | Diaria | — | CU-O10 | | Check-outs por día | Conteo de check-outs completados | Diaria | — | CU-O11 | | Tiempo de estancia media | AVG(check_out - check_in) en días | Semanal | 2-4 días | CU-O10, CU-O11 | | Tasa de confirmación de solicitudes | (Solicitudes confirmadas / Solicitudes totales) × 100 | Semanal | ≥ 80% | CU-O09 | | Tiempo medio de confirmación | Tiempo desde creación hasta confirmación de solicitud | Semanal | ≤ 4 horas | CU-O09 | | % de inventario bloqueado | (Habitaciones bloqueadas / Habitaciones totales) × 100 | Semanal | ≤ 10% | CU-O16 | | Overbooking evitado | Número de veces que optimistic locking evitó conflicto | Mensual | — | CU-O15 |
#### 4.9 Colecciones MongoDB Involucradas

| Colección | Tipo de Acceso | Propósito | CU | |-----------|---------------|-----------|----| | `booking_orders` | Lectura/Escritura | Estado y datos de la reserva | CU-O08, O09, O10, O11 | | `booking_guests` | Escritura | Datos de huéspedes | CU-O08 | | `booking_status_history` | Escritura | Trazabilidad de cambios de estado | CU-O08, O09, O10, O11 | | `manual_reservations` | Escritura | Registro de reservas de origen manual | CU-O08 | | `room_types` | Escritura | Creación y gestión de tipos de habitación | CU-O14, O31, O33 | | `hotel_rooms` | Escritura | Habitaciones físicas individuales | CU-O14, O30, O31, O32 | | `room_inventory_calendar` | Escritura | Inventario disponible por fecha | CU-O15, O16 | | `blackout_dates` | Escritura | Bloques de disponibilidad | CU-O16 | | `room_availability_blocks` | Escritura | Registros de bloqueo | CU-O16 | | `hotel_policies` | Escritura | Políticas del hotel | CU-O20 | | `reservation_invoices` | Escritura | Facturas generadas | CU-O24 | | `reservation_payments` | Escritura | Pagos registrados | CU-O25 | | `room_status_log` | Escritura | Registro de cambios de estado de habitación | CU-O30, O31, O39, O40 | | `housekeeping_tasks` | Escritura | Tareas de limpieza asignadas | CU-O39 | | `maintenance_schedule` | Escritura | Programación de mantenimiento | CU-O40 | | `maintenance_tasks` | Escritura | Ejecución de tareas de mantenimiento | CU-O40 | | `additional_charges` | Escritura | Cargos adicionales a reservas | CU-O34 | | `room_availability_blocks` | Escritura | Bloqueos administrativos | CU-O32 | | `user_activity_logs` | Escritura | Auditoría de acciones operativas | Múltiples CU |
#### 4.10 Flujo de Eventos del Departamento

El flujo de Operaciones Hoteleras es el más complejo del sistema. Se organiza en cuatro subflujos que se ejecutan en paralelo:

```
SUBMÓDULO A — Atención en Front Desk (Ciclo de Estancia del Huésped)
  └── Llegada del huésped:
  │     └── ¿Tiene reserva? → Sí: Buscar booking por ID/nombre → Evento 2
  │     └── No (walk-in) → CU-O08: Crear reserva manual en estado "confirmed"
  │
  ├── Evento 1: Check-in (CU-O10)
  │     └── Recepcionista busca reserva en lista de check-ins del día
  │     └── Recepcionista verifica identidad del huésped
  │     └── Recepcionista confirma check-in
  │     └── Sistema: booking_orders.estado → "checked_in"
  │     └── Sistema: booking_status_history registra el cambio
  │     └── Sistema: room_inventory_calendar marca como ocupada
  │
  ├── Evento 2: Estancia del huésped (paralelo)
  │     └── CU-O34: Recepcionista registra cargos adicionales (room service, minibar, etc.)
  │     └── CU-O33: Gestión de amenities por tipo de habitación (solicitudes del huésped)
  │
  └── Evento 3: Check-out (CU-O11)
        └── Recepcionista busca reserva en lista de check-outs del día
        └── Recepcionista verifica cargos adicionales y genera factura (CU-O24)
        └── Recepcionista registra pago (CU-O25)
        └── Recepcionista confirma check-out
        └── Sistema: booking_orders.estado → "checked_out"
        └── Sistema: room_inventory_calendar libera inventario de noches futuras
        └── Sistema: marca habitación como "cleaning_needed" en room_status_log

SUBMÓDULO B — Gestión de Solicitudes de Reserva
  └── Cliente solicita reserva online → booking_orders.estado = "pending"
  └── CU-O09: Gerente consulta solicitudes pendientes
  └── Decisión del gerente:
  │     └── Confirmar:
  │     │     └── Sistema: booking_orders.estado → "confirmed"
  │     │     └── Sistema: descuenta inventario en room_inventory_calendar
  │     │     └── Sistema: booking_status_history registra
  │     └── Rechazar:
  │           └── Sistema: booking_orders.estado → "cancelled"
  │           └── Sistema: registra motivo de rechazo
  └── Automático: si pasa 24h sin acción → "cancelled" automático

SUBMÓDULO C — Configuración de Habitaciones e Inventario
  └── CU-O14: Partner crea tipos de habitación
  │     └── Sistema: crea room_types + hotel_rooms físicas
  │
  └── CU-O20: Partner define políticas hoteleras
  │     └── Sistema: actualiza hotel_policies
  │
  └── CU-O15: Gerente actualiza inventario diario
  │     └── Sistema: actualiza room_inventory_calendar con optimistic locking
  │
  └── CU-O16: Gerente bloquea disponibilidad
        └── Sistema: crea blackout_dates + actualiza room_inventory_calendar

SUBMÓDULO D — Monitoreo y Operación de Habitaciones
  └── CU-O30: Consulta de matriz de estado de habitaciones
  └── CU-O32: Consulta de disponibilidad por habitación individual
  └── CU-O31: Asignación/cambio de tipo de habitación
  └── CU-O39: Gestión de limpieza y rotación
  └── CU-O40: Gestión de mantenimiento preventivo
```

#### 4.11 Fuera de Alcance del Departamento

| Aspecto | Fuera de Alcance | Departamento Responsable | |---------|-----------------|-------------------------| | Configuración de tarifas y planes tarifarios | Las operaciones hoteleras solo consultan tarifas, no las definen | Revenue Management | | Moderación de reseñas | El front desk no modera reseñas de huéspedes | Marketing Hotelero | | Administración de usuarios del sistema | El departamento no gestiona cuentas ni roles de usuario | Administración / Sistemas | | Ejecución de pipeline ETL | Las operaciones hoteleras no ejecutan procesos de datos | Datos / Analítica | | Geolocalización y metadata de destinos | El front desk no edita coordenadas ni metadata de destinos | Datos / Analítica | | Visualización de mapa mundial | El departamento no gestiona el mapa interactivo | Datos / Analítica |
### Departamento 5: Administración / Sistemas

| Elemento | Descripción | |----------|-------------| | **Responsable** | Super Admin | | **Función** | Administrar usuarios, roles, permisos, autenticación, monitoreo de servicios, contratos API, configuración global del sistema y auditoría | | **Procesos** | Gestión de usuarios, roles y permisos, autenticación JWT, monitoreo de servicios, gestión de contratos API, auditoría, navegación por rol | | **Sistemas que usa** | Módulo admin (usuarios, roles, permisos), módulo auth (login, sesiones), módulo settings, módulo audit | | **CU asociados** | CU-O01, CU-O13, CU-O23, CU-O27, CU-O28, CU-O29 | | **KPIs** | Usuarios con rol, accesos no autorizados, tiempo de actividad del sistema, sesiones activas |
#### 5.1 Objetivos del Departamento

| ID | Objetivo del Departamento | Descripción | |----|--------------------------|-------------| | OD5.1 | Garantizar la seguridad del acceso al sistema | Implementar autenticación JWT robusta, sesiones con TTL, control de roles y permisos granulares para proteger los datos y operaciones del sistema | | OD5.2 | Administrar el ciclo de vida de usuarios y roles | Gestionar creación, activación, desactivación de usuarios, asignación de roles y definición de permisos por rol | | OD5.3 | Mantener la auditoría y trazabilidad del sistema | Registrar todas las acciones sensibles en `user_activity_logs` para permitir auditoría forense y cumplimiento normativo | | OD5.4 | Monitorear la salud y disponibilidad del sistema | Supervisar servicios (Redis, backend, MongoDB), health checks y estado de contratos API |
#### 5.2 Actores Involucrados

| Actor | Rol en el Departamento | CU Asociados | |-------|----------------------|--------------| | **Super Admin** | Administra usuarios, roles, permisos, monitorea servicios y audita el sistema | CU-O01, CU-O13, CU-O23, CU-O27, CU-O28, CU-O29 | | **Todos los usuarios del sistema** | Inician sesión, cierran sesión, cambian contraseña y actualizan perfil | CU-O01, CU-O28, CU-O29 | | **Auditor de Datos** | Consulta historial de cambios y reportes de auditoría | CU-O13, CU-O27 | | **Marketing Hotelero** | Moderación de reseñas (con rol asignado) | CU-O23 | | **Sistema** | Generación de tokens, registro de auditoría, validación de sesiones | Todos los CU del departamento |
#### 5.3 Requisitos Funcionales

| ID RF | Nombre | Descripción | CU Asociado | HU Asociada | |-------|--------|-------------|-------------|-------------| | RF5.1 | Inicio de sesión JWT | El sistema debe autenticar usuarios mediante email + contraseña, generar token de 48 bytes y establecer cookie httponly | CU-O01 | HU-01 | | RF5.2 | Validación de sesión | El sistema debe validar la sesión en cada request a ruta protegida usando `require_login()` | CU-O01, CU-O28 | HU-01, HU-28 | | RF5.3 | Cierre de sesión seguro | El sistema debe invalidar la sesión en servidor (eliminar de user_sessions) y eliminar la cookie | CU-O28 | HU-28 | | RF5.4 | Cambio de contraseña | El sistema debe permitir cambiar contraseña verificando la actual, con hash bcrypt e invalidación de sesiones | CU-O29 | HU-29 | | RF5.5 | Actualización de perfil | El sistema debe permitir actualizar datos del perfil (display_name, email, teléfono, avatar) | CU-O29 | HU-29 | | RF5.6 | Control de roles y permisos | El sistema debe verificar el rol del usuario para cada endpoint sensible y redirigir según navegación por rol | CU-O01 | HU-01 | | RF5.7 | Registro de auditoría | El sistema debe registrar en `user_activity_logs` todas las acciones sensibles (login, logout, cambios de perfil) | CU-O01, O28, O29 | HU-01, HU-28, HU-29 | | RF5.8 | Gestión de usuarios | El sistema debe permitir al super admin crear, editar, activar/desactivar usuarios y asignar roles | CU-O01 (admin) | — | | RF5.9 | Monitoreo de servicios | El sistema debe exponer health checks y estado de conexión a MongoDB, Redis y servicios backend | — | — |
#### 5.4 Requisitos No Funcionales

| ID RNF | Nombre | Descripción | Categoría | |--------|--------|-------------|-----------| | RNF5.1 | Hash de contraseñas | Las contraseñas se almacenan exclusivamente con bcrypt (passlib). Nunca en texto plano ni con hash reversible | Seguridad | | RNF5.2 | Longitud del token | El token de sesión tiene exactamente 48 bytes generados con `secrets.token_urlsafe()` | Seguridad | | RNF5.3 | Hash del token en BD | El hash almacenado en DB es SHA-256 del token. El token plano solo existe en la cookie del navegador | Seguridad | | RNF5.4 | Cookie httponly | La cookie tiene flag httponly (no accesible desde JavaScript) para mitigar XSS | Seguridad | | RNF5.5 | Cookie samesite | La cookie tiene flag samesite=lax para mitigar CSRF | Seguridad | | RNF5.6 | TTL de sesión | La sesión expira a las 8 horas configuradas en `settings.SESSION_TTL_HOURS` | Seguridad | | RNF5.7 | TTL index automático | MongoDB TTL index elimina automáticamente documentos expirados de `user_sessions` | Mantenimiento | | RNF5.8 | Mensaje de error genérico | El mensaje de error para credenciales inválidas debe ser genérico sin revelar si el email existe | Seguridad | | RNF5.9 | Una sesión por usuario | Cada usuario puede tener solo una sesión activa a la vez (la anterior se invalida al hacer login) | Seguridad | | RNF5.10 | Disponibilidad del módulo auth | El módulo de autenticación debe tener 99.9% de disponibilidad | Disponibilidad |
#### 5.5 Reglas de Negocio

| ID RN | Descripción | Origen | |-------|-------------|--------| | RN5.1 | El mensaje de error para credenciales inválidas debe ser genérico: "Credenciales inválidas". No debe revelar si el email no existe o la contraseña es incorrecta | Seguridad | | RN5.2 | Una cuenta desactivada no puede iniciar sesión bajo ninguna circunstancia | Seguridad | | RN5.3 | Cada usuario solo puede tener una sesión activa a la vez | Seguridad | | RN5.4 | La sesión expira después de 8 horas de inactividad | Seguridad | | RN5.5 | El logout invalida la sesión en el servidor (no solo borra la cookie del lado cliente) | Seguridad | | RN5.6 | La nueva contraseña debe tener al menos 8 caracteres | Seguridad | | RN5.7 | La nueva contraseña no puede ser igual a la actual | Seguridad | | RN5.8 | El cambio de contraseña invalida todas las sesiones activas para forzar re-login | Seguridad | | RN5.9 | El email debe ser único en el sistema | Usuarios | | RN5.10 | Las contraseñas siempre se almacenan con bcrypt, nunca en texto plano | Seguridad |
#### 5.6 Escenarios de Operación

| ID Escenario | Nombre | CU | Descripción | |-------------|--------|----|-------------| | E5.1 | Inicio de sesión exitoso | CU-O01 | Usuario ingresa credenciales correctas. Sistema genera token, establece cookie, redirige según rol. Registra evento en user_activity_logs | | E5.2 | Inicio de sesión con credenciales inválidas | CU-O01 | Usuario ingresa contraseña incorrecta. Sistema responde "Credenciales inválidas" sin especificar cuál campo falló. Registra intento fallido | | E5.3 | Inicio de sesión con cuenta desactivada | CU-O01 | Usuario con is_active=false intenta login. Sistema responde "Cuenta desactivada. Contacte al administrador." | | E5.4 | Cierre de sesión exitoso | CU-O28 | Usuario hace clic en "Cerrar sesión". Sistema invalida sesión en user_sessions, elimina cookie, redirige a login | | E5.5 | Cambio de contraseña exitoso | CU-O29 | Usuario cambia contraseña. Sistema verifica actual, hashea nueva con bcrypt, invalida sesiones anteriores | | E5.6 | Cambio de contraseña con contraseña actual incorrecta | CU-O29 | Usuario ingresa contraseña actual incorrecta. Sistema responde "Contraseña actual incorrecta" | | E5.7 | Actualización de perfil exitosa | CU-O29 | Usuario actualiza display_name y email. Sistema valida unicidad de email y actualiza users.profile | | E5.8 | Sesión expirada | CU-O01, CU-O28 | Usuario intenta acceder a ruta protegida con sesión vencida. Sistema responde HTTP 401 y redirige a login |
#### 5.7 Trazabilidad Individual del Departamento

| OT | OO | CU | HU | |----|----|----|----| | OT2.1: Estandarizar servicios por API | OO2.1.2: Validar JWT y roles por endpoint | CU-O01: Iniciar sesión JWT | HU-01 | | OT2.1 | OO2.1.2 | CU-O28: Administrar cuenta, sesión y cierre seguro | HU-28 | | OT2.1 | OO2.1.2 | CU-O29: Cambiar contraseña y actualizar perfil | HU-29 | | OT3.2: Automatizar gobierno de datos | OO3.2.2: Registrar auditoría y trazabilidad | CU-O13: Historial cambios propiedad | HU-13 | | OT3.2 | OO3.2.2 | CU-O27: Consultar reporte de calidad de datos | HU-27 | | OT3.2 | OO3.2.2 | CU-O23: Moderar y responder reseña | HU-23 |
#### 5.8 KPIs del Departamento

| KPI | Fórmula | Frecuencia | Meta | CU Asociado | |-----|---------|------------|------|-------------| | Usuarios con rol activo | Conteo de usuarios con is_active = true agrupados por rol | Mensual | — | CU-O01 | | Intentos de acceso no autorizados | Conteo de intentos fallidos de login | Diaria | < 10/día | CU-O01 | | Tiempo de actividad del sistema | (Tiempo total - tiempo caída) / Tiempo total × 100 | Mensual | ≥ 99.5% | — | | Sesiones activas simultáneas | AVG(sesiones activas por hora) | Diaria | — | CU-O01, CU-O28 | | Tiempo medio de respuesta de login | Tiempo desde envío de credenciales hasta respuesta | Diaria | < 500ms | CU-O01 | | Tasa de cambio de contraseña | (Cambios de contraseña / Usuarios activos) × 100 | Mensual | — | CU-O29 | | Duplicidad de email evitada | Número de intentos de email duplicado bloqueados | Mensual | — | CU-O29 |
#### 5.9 Colecciones MongoDB Involucradas

| Colección | Tipo de Acceso | Propósito | CU | |-----------|---------------|-----------|----| | `users` | Lectura/Escritura | Autenticación, perfil, password_hash | CU-O01, CU-O29 | | `user_sessions` | Escritura | Creación y eliminación de sesiones | CU-O01, CU-O28 | | `user_activity_logs` | Escritura | Registro de auditoría de acciones | CU-O01, CU-O28, CU-O29 | | `roles` | Lectura | Definición de roles del sistema | CU-O01 | | `permissions` | Lectura | Definición de permisos | CU-O01 | | `role_permissions` | Lectura | Asignación de permisos a roles | CU-O01 | | `hotel_profile_changes` | Lectura | Consulta de historial de cambios | CU-O13 | | `data_quality_reports` | Lectura | Consulta de reportes de calidad | CU-O27 | | `etl_executions` | Lectura | Consulta de ejecuciones ETL | CU-O27 |
#### 5.10 Flujo de Eventos del Departamento

```
Evento 1: Autenticación (Login)
  └── Usuario navega a página de login
  └── CU-O01: Usuario ingresa email y contraseña
  └── CU-O01: Sistema busca usuario en users por email
  └── Decisión 1: ¿Usuario existe? → Sí: continuar | No: "Credenciales inválidas"
  └── CU-O01: Sistema verifica contraseña con bcrypt
  └── Decisión 2: ¿Contraseña coincide? → Sí: continuar | No: "Credenciales inválidas"
  └── CU-O01: Sistema verifica is_active = true
  └── Decisión 3: ¿Cuenta activa? → Sí: continuar | No: "Cuenta desactivada"
  └── CU-O01: Sistema invalida sesión previa (si existe)
  └── CU-O01: Sistema genera token de 48 bytes
  └── CU-O01: Sistema almacena hash SHA-256 en user_sessions
  └── CU-O01: Sistema establece cookie httponly, samesite=lax, max-age=28800
  └── CU-O01: Sistema registra en user_activity_logs
  └── CU-O01: Sistema redirige según navegación por rol

Evento 2: Cierre de Sesión (Logout)
  └── Usuario autenticado hace clic en "Cerrar sesión"
  └── CU-O28: Sistema extrae token de cookie hoteldata_session
  └── CU-O28: Sistema calcula hash SHA-256
  └── CU-O28: Sistema elimina documento de user_sessions
  └── CU-O28: Sistema elimina cookie (max-age=0)
  └── CU-O28: Sistema registra en user_activity_logs
  └── CU-O28: Sistema redirige a login

Evento 3: Cambio de Contraseña
  └── Usuario autenticado navega a configuración de cuenta
  └── CU-O29: Usuario ingresa contraseña actual y nueva (×2)
  └── CU-O29: Sistema verifica contraseña actual con bcrypt
  └── Decisión: ¿Coincide? → Sí: continuar | No: "Contraseña actual incorrecta"
  └── CU-O29: Sistema valida nueva contraseña ≥ 8 caracteres
  └── CU-O29: Sistema hashea nueva contraseña con bcrypt
  └── CU-O29: Sistema actualiza users.password_hash
  └── CU-O29: Sistema invalida todas las sesiones excepto la actual
  └── CU-O29: Sistema registra en user_activity_logs

Evento 4: Actualización de Perfil
  └── Usuario autenticado navega a su perfil
  └── CU-O29: Usuario modifica datos (display_name, email, teléfono, avatar)
  └── CU-O29: Sistema valida unicidad de email
  └── Decisión: ¿Email único? → Sí: continuar | No: "Email ya registrado"
  └── CU-O29: Sistema actualiza users.profile
  └── CU-O29: Sistema registra en user_activity_logs
```

#### 5.11 Fuera de Alcance del Departamento

| Aspecto | Fuera de Alcance | Departamento Responsable | |---------|-----------------|-------------------------| | Configuración de tarifas y planes | La administración no define precios ni promociones | Revenue Management | | Gestión de contenido de hoteles | La administración no edita descripciones ni imágenes de hoteles | Marketing Hotelero | | Operación de front desk (check-in/out) | La administración no participa en la atención al huésped | Operaciones Hoteleras | | Ejecución de pipeline ETL | La administración monitorea pero no ejecuta procesos ETL | Datos / Analítica | | Gestión de limpieza y mantenimiento | La administración no gestiona tareas operativas de habitaciones | Operaciones de Infraestructura Hotelera |
### Departamento 6: Datos / Analítica

| Elemento | Descripción | |----------|-------------| | **Responsable** | Auditor de Datos | | **Función** | Ejecutar y validar pipelines ETL, monitorear calidad de datos, auditar trazabilidad del sistema, generar reportes de revenue y calidad | | **Procesos** | Ejecución de pipeline ETL, validación de calidad, consulta de reportes, consulta de auditoría, análisis de mercados, consulta de historial de cambios | | **Sistemas que usa** | Módulo ETL (Airflow), dashboard, reportes, calidad, auditoría, módulo partner (historial) | | **CU asociados** | CU-O13, CU-O26, CU-O27, CU-O35, CU-O36, CU-O37, CU-O38 | | **KPIs** | Registros procesados, registros rechazados, cobertura de auditoría, calidad del dataset, tiempo de ejecución ETL |
#### 6.1 Objetivos del Departamento

| ID | Objetivo del Departamento | Descripción | |----|--------------------------|-------------| | OD6.1 | Ejecutar y monitorear el pipeline ETL de datos hoteleros | Procesar 600 000 registros desde archivos CSV hacia MongoDB mediante Airflow, con control de calidad y registro de auditoría | | OD6.2 | Garantizar la calidad e integridad de los datos | Validar cada registro contra reglas de calidad, rechazar datos inválidos con trazabilidad y generar reportes de calidad | | OD6.3 | Enriquecer y corregir metadata de catálogos | Editar nombres de destinos, coordenadas geográficas y nombres comerciales de hoteles para mejorar la calidad del catálogo | | OD6.4 | Proveer inteligencia de negocio mediante reportes | Generar dashboards y reportes de revenue, calidad de datos, mercados y eficiencia operativa |
#### 6.2 Actores Involucrados

| Actor | Rol en el Departamento | CU Asociados | |-------|----------------------|--------------| | **Auditor de Datos** | Ejecuta pipeline ETL, valida calidad, edita metadata de destinos y hoteles, consulta reportes | CU-O13, CU-O27, CU-O35, CU-O36, CU-O37, CU-O38 | | **Gerente / Revenue Manager** | Consulta reportes de revenue y mercado | CU-O26 | | **Marketing Hotelero** | Consulta mapa mundial y edita override de nombres de hotel | CU-O36, CU-O37 | | **Sistema (Airflow + FastAPI)** | Ejecuta pipelines, calcula agregaciones, sirve datos geoespaciales | Todos los CU del departamento |
#### 6.3 Requisitos Funcionales

| ID RF | Nombre | Descripción | CU Asociado | HU Asociada | |-------|--------|-------------|-------------|-------------| | RF6.1 | Consulta de historial de cambios | El sistema debe mostrar el historial completo de cambios de perfil de una propiedad | CU-O13 | HU-13 | | RF6.2 | Reporte de calidad de datos | El sistema debe mostrar total de registros procesados, aceptados, rechazados y completitud por campo | CU-O27 | HU-27 | | RF6.3 | Detalle de registros rechazados | El sistema debe mostrar cada registro rechazado con la razón exacta y el campo inválido | CU-O27 | HU-27 | | RF6.4 | Edición de metadata de destino | El sistema debe permitir editar nombre visible, coordenadas, país, ciudad y descripción de destinos | CU-O35 | HU-35 | | RF6.5 | Edición de nombre visible de hotel | El sistema debe permitir asignar nombre real a hoteles con ID numérico (manual_override) | CU-O36 | HU-36 | | RF6.6 | Visualización de mapa mundial | El sistema debe mostrar mapa Leaflet.js con marcadores de destinos y hoteles coloreados por precio | CU-O37 | HU-37 | | RF6.7 | Selección de ubicación en mapa | El sistema debe permitir seleccionar coordenadas geográficas mediante clic en mapa interactivo | CU-O38 | HU-38 | | RF6.8 | Reportes agregados de revenue | El sistema debe calcular eventos totales, reservas, conversión, revenue bruto, precio promedio, top hoteles | CU-O26 | HU-26 | | RF6.9 | Exportación de reportes | El sistema debe permitir exportar reportes en formato CSV o JSON | CU-O26 | HU-26 |
#### 6.4 Requisitos No Funcionales

| ID RNF | Nombre | Descripción | Categoría | |--------|--------|-------------|-----------| | RNF6.1 | Tiempo de ejecución ETL | El pipeline ETL completo debe ejecutarse en menos de 30 minutos para 600K registros | Rendimiento | | RNF6.2 | Cobertura de calidad | El 100% de los registros deben pasar por validación de calidad antes de cargarse | Calidad | | RNF6.3 | Trazabilidad de rechazos | Ningún registro debe ser descartado silenciosamente — todos los rechazos van a `rejected_records` | Auditoría | | RNF6.4 | Precisión de coordenadas | Las coordenadas geográficas se almacenan con precisión de 6 decimales | Precisión | | RNF6.5 | Disponibilidad de reportes | Los reportes agregados deben cargar en menos de 5 segundos | Rendimiento | | RNF6.6 | Dual-write analítico | Las fact tables deben actualizarse simultáneamente con las colecciones operacionales | Consistencia |
#### 6.5 Reglas de Negocio

| ID RN | Descripción | Origen | |-------|-------------|--------| | RN6.1 | Todos los cambios críticos de perfil son registrados en `hotel_profile_changes` | Auditoría | | RN6.2 | El historial es de solo lectura y no puede modificarse ni eliminarse | Auditoría | | RN6.3 | Cada ejecución ETL debe producir un reporte de calidad en `data_quality_reports` | Calidad | | RN6.4 | El nombre visible del destino no puede estar vacío | Geo | | RN6.5 | Las coordenadas deben ser válidas (lat: -90 a 90, lng: -180 a 180) | Geo | | RN6.6 | Se conserva el ID original del destino para mantener trazabilidad con el dataset | Geo | | RN6.7 | El nombre override se usa en todas las interfaces visibles (búsqueda, detalle, factura) | Geo | | RN6.8 | El nombre original siempre se conserva en un campo `original_name` para referencia | Geo | | RN6.9 | Los destinos sin coordenadas no se muestran en el mapa | Geo |
#### 6.6 Escenarios de Operación

| ID Escenario | Nombre | CU | Descripción | |-------------|--------|----|-------------| | E6.1 | Consulta de historial de cambios de propiedad | CU-O13 | Auditor consulta historial de cambios del hotel #14239 y ve 15 modificaciones con usuario, fecha, valores anterior y nuevo | | E6.2 | Consulta de reporte de calidad post-ETL | CU-O27 | Auditor consulta reporte de última ejecución: 600,000 procesados, 595,000 aceptados, 5,000 rechazados (0.83%) | | E6.3 | Edición de metadata de destino "Cancún" | CU-O35 | Auditor cambia nombre de "Destination 8250" a "Cancún", asigna coordenadas 21.1619, -86.8515, país "México" | | E6.4 | Manual override de nombre de hotel | CU-O36 | Auditor cambia "Property 14239" a "Hotel Paraíso Caribe" con manual_override = true | | E6.5 | Visualización de mapa mundial | CU-O37 | Auditor abre mapa mundial y ve 50 destinos con hoteles coloreados por precio. Hace clic en Cancún y ve 15 hoteles | | E6.6 | Selección de ubicación en mapa | CU-O38 | Auditor edita destino, hace clic en "Seleccionar en mapa", navega a Cancún, hace clic, captura coordenadas 21.1619, -86.8515 |
#### 6.7 Trazabilidad Individual del Departamento

| OT | OO | CU | HU | |----|----|----|----| | OT3.2: Automatizar gobierno de datos | OO3.2.1: Ejecutar pipeline ETL | CU-O27: Reporte calidad datos | HU-27 | | OT3.2 | OO3.2.2: Registrar auditoría y trazabilidad | CU-O13: Historial cambios propiedad | HU-13 | | OT4.1: Consolidar analítica global | OO4.1.1: Consultar dashboard ejecutivo | CU-O26: Reportes revenue | HU-26 | | OT4.1 | OO4.1.2: Analizar mercados y destinos | CU-O26: Reportes revenue | HU-26 | | OT4.2: Aplicar BI y ML | OO4.2.2: Detectar anomalías y calidad | CU-O27: Reporte calidad datos | HU-27 | | OT2.3: Enriquecer catálogo geoespacial | OO2.3.1: Editar metadata de destinos | CU-O35: Editar metadata destino | HU-35 | | OT2.3 | OO2.3.2: Editar nombre visible de hotel | CU-O36: Manual override | HU-36 | | OT2.3 | OO2.3.3: Visualizar destinos en mapa | CU-O37: Mapa mundial | HU-37 | | OT2.3 | OO2.3.3 | CU-O38: Seleccionar ubicación en mapa | HU-38 |
#### 6.8 KPIs del Departamento

| KPI | Fórmula | Frecuencia | Meta | CU Asociado | |-----|---------|------------|------|-------------| | Registros procesados por ETL | Conteo de registros procesados en última ejecución | Por ejecución | 600,000 | CU-O27 | | Tasa de rechazo | (Registros rechazados / Registros totales) × 100 | Por ejecución | ≤ 2% | CU-O27 | | Cobertura de auditoría | (Acciones auditadas / Acciones totales) × 100 | Mensual | 100% | CU-O13 | | Calidad del dataset | % de campos con completitud ≥ 95% | Semanal | ≥ 90% | CU-O27 | | Tiempo de ejecución ETL | Tiempo desde inicio hasta fin del pipeline | Por ejecución | ≤ 30 min | CU-O27 | | Destinos con coordenadas | (Destinos con coordenadas / Destinos totales) × 100 | Mensual | ≥ 80% | CU-O35 | | Hoteles con override completado | Conteo de hoteles con manual_override = true | Mensual | — | CU-O36 |
#### 6.9 Colecciones MongoDB Involucradas

| Colección | Tipo de Acceso | Propósito | CU | |-----------|---------------|-----------|----| | `hotel_profile_changes` | Lectura | Consulta de historial de cambios | CU-O13 | | `data_quality_reports` | Lectura | Reportes de calidad de datos | CU-O27 | | `etl_executions` | Lectura | Estado de ejecuciones ETL | CU-O27 | | `rejected_records` | Lectura | Detalle de registros rechazados | CU-O27 | | `dim_destinations` | Escritura | Actualización de metadata de destinos | CU-O35 | | `locations` | Escritura | Actualización de ubicaciones | CU-O35 | | `dim_hotels` | Escritura | Manual override de nombre de hotel | CU-O36 | | `hotels` | Escritura | Actualización de nombre de hotel | CU-O36 | | `hotel_edit_history` | Escritura | Registro de cambios de metadata | CU-O35, CU-O36 | | `dim_visitor_countries` | Lectura | Reportes de países visitantes | CU-O26 | | `dim_sites` | Lectura | Reportes por canal | CU-O26 | | `dim_dates` | Lectura | Reportes por fecha | CU-O26 | | `fact_hotel_reservations` | Lectura | Reportes agregados de revenue | CU-O26 | | `destinations_enriched` | Lectura | Datos geoespaciales para mapa | CU-O37, CU-O38 | | `hotel_locations_geo` | Lectura | Ubicaciones de hoteles para mapa | CU-O37 |
#### 6.10 Flujo de Eventos del Departamento

```
Fase A — Pipeline ETL y Calidad de Datos
  └── Evento: Ejecución programada de Airflow DAG
  └── Sistema: Lee archivos CSV desde data/raw/
  └── Sistema: Valida cada registro contra reglas de calidad
  │     └── ¿Registro válido? → Sí: Carga a MongoDB (colecciones maestras)
  │     └── No: Almacena en rejected_records con razón exacta
  └── Sistema: Actualiza fact tables (fact_hotel_reservations)
  └── Sistema: Actualiza dimensiones (dim_hotels, dim_destinations, etc.)
  └── Sistema: Genera reporte de calidad en data_quality_reports
  └── CU-O27: Auditor consulta reporte de calidad post-ejecución
  └── CU-O27: Auditor investiga registros rechazados con detalle

Fase B — Corrección de Metadata de Catálogo
  └── CU-O35: Auditor edita metadata de destino
  │     └── Sistema: actualiza dim_destinations
  │     └── Decisión: ¿Asignar coordenadas? → Sí: CU-O38 (seleccionar en mapa) | No: ingresar manualmente
  │
  └── CU-O36: Auditor edita nombre visible de hotel
  │     └── Sistema: actualiza dim_hotels con manual_override = true
  │
  └── CU-O37: Auditor visualiza cambios en mapa mundial

Fase C — Consulta de Reportes y Auditoría
  └── CU-O13: Auditor consulta historial de cambios de propiedad
  └── CU-O26: Gerente/revenue manager consulta reportes de revenue
  └── CU-O26: Sistema calcula agregaciones desde fact_hotel_reservations
  └── CU-O26: Sistema muestra KPIs: eventos totales, conversión, revenue, precio promedio

Fase D — Visualización Geoespacial
  └── CU-O37: Usuario navega a mapa mundial
  └── Sistema: consulta dim_destinations con coordenadas no nulas
  └── Sistema: consulta dim_hotels asociados a cada destino
  └── Sistema: envía datos como GeoJSON al frontend
  └── Frontend (Leaflet.js): renderiza marcadores coloreados por precio
  └── Usuario: hace zoom, clic en marcadores para ver detalle (CU-O04)
```

#### 6.11 Fuera de Alcance del Departamento

| Aspecto | Fuera de Alcance | Departamento Responsable | |---------|-----------------|-------------------------| | Gestión de usuarios y roles | El departamento de datos no administra cuentas de usuario | Administración / Sistemas | | Configuración de tarifas | El departamento de datos no define precios ni promociones | Revenue Management | | Operación de front desk | El departamento de datos no realiza check-in/out | Operaciones Hoteleras | | Moderación de reseñas | El departamento de datos no modera reseñas | Marketing Hotelero | | Gestión de limpieza de habitaciones | El departamento de datos no gestiona tareas de housekeeping | Operaciones de Infraestructura Hotelera |
### Departamento 7: Operaciones de Infraestructura Hotelera

| Elemento | Descripción | |----------|-------------| | **Responsable** | Gerente de hotel / Housekeeping / Mantenimiento | | **Función** | Gestionar el estado físico y operativo de las habitaciones: limpieza, rotación, mantenimiento preventivo y cargos adicionales | | **Procesos** | Consulta de estado de habitaciones, asignación de limpieza, rotación post-checkout, mantenimiento programado, registro de cargos extras | | **Sistemas que usa** | Módulo housekeeping (room_status, tareas), módulo maintenance (programación), módulo billing (cargos adicionales) | | **CU asociados** | CU-O30, CU-O31, CU-O32, CU-O33, CU-O34, CU-O39, CU-O40 | | **KPIs** | Tiempo de rotación de habitaciones, cumplimiento de limpieza, cumplimiento de mantenimiento, cargos adicionales por reserva |
#### 7.1 Objetivos del Departamento

| ID | Objetivo del Departamento | Descripción | |----|--------------------------|-------------| | OD7.1 | Gestionar el estado físico y operativo de las habitaciones | Mantener una matriz actualizada del estado de cada habitación (disponible, ocupada, limpieza, mantenimiento, bloqueada) para optimizar la asignación | | OD7.2 | Optimizar el flujo de limpieza y rotación post-checkout | Reducir el tiempo entre el check-out del huésped y la disponibilidad de la habitación para el próximo huésped | | OD7.3 | Programar y ejecutar mantenimiento preventivo | Mantener las instalaciones en óptimas condiciones mediante mantenimiento programado de HVAC, eléctrico, plomería, mobiliario y pintura | | OD7.4 | Monitorear la eficiencia operativa del hotel | Medir KPIs de rotación, cumplimiento de limpieza, cumplimiento de mantenimiento y ocupación para mejorar la operación |
#### 7.2 Actores Involucrados

| Actor | Rol en el Departamento | CU Asociados | |-------|----------------------|--------------| | **Recepcionista** | Consulta estado de habitaciones, asigna limpieza, inicia/completa tareas | CU-O30, CU-O31, CU-O32, CU-O39 | | **Gerente de hotel** | Supervisa la operación, programa mantenimiento, monitorea eficiencia, gestiona rotación | CU-O30, CU-O31, CU-O32, CU-O39, CU-O40, CU-T14, CU-T15 | | **Sistema** | Registro de cambios de estado, cálculo de tiempos de rotación, programación de mantenimiento | Todos los CU del departamento |
#### 7.3 Requisitos Funcionales

| ID RF | Nombre | Descripción | CU Asociado | HU Asociada | |-------|--------|-------------|-------------|-------------| | RF7.1 | Matriz de estado de habitaciones | El sistema debe mostrar matriz visual con código de colores para todos los estados de habitación | CU-O30 | HU-30 | | RF7.2 | Asignación de tipo de habitación | El sistema debe permitir cambiar el tipo de habitación a una habitación física individual | CU-O31 | HU-31 | | RF7.3 | Calendario de disponibilidad por habitación | El sistema debe mostrar calendario de 90 días con ocupación, bloqueos y mantenimiento | CU-O32 | HU-32 | | RF7.4 | Gestión de amenities por tipo de habitación | El sistema debe permitir configurar amenities específicos por tipo de habitación | CU-O33 | HU-33 | | RF7.5 | Asignación de limpieza | El sistema debe permitir asignar tarea de limpieza post-checkout a personal | CU-O39 | HU-39 | | RF7.6 | Registro de ciclo de limpieza | El sistema debe registrar inicio y fin de limpieza con tiempo de rotación | CU-O39 | HU-39 | | RF7.7 | Programación de mantenimiento | El sistema debe permitir programar mantenimiento preventivo con fecha, tipo, prioridad | CU-O40 | HU-40 | | RF7.8 | Reporte de rotación | El sistema debe calcular tiempo promedio de rotación check-out → disponible | CU-T14 | HU-T14 | | RF7.9 | Plan de mantenimiento proactivo | El sistema debe sugerir mantenimientos basados en histórico y frecuencia recomendada | CU-T15 | HU-T15 | | RF7.10 | Dashboard de eficiencia operativa | El sistema debe mostrar KPIs consolidados de rotación, limpieza, mantenimiento y ocupación 
#### 7.4 Requisitos No Funcionales

| ID RNF | Nombre | Descripción | Categoría | |--------|--------|-------------|-----------| | RNF7.1 | Actualización en tiempo real | El estado de las habitaciones debe reflejarse en menos de 3 segundos después de cualquier cambio | Rendimiento | | RNF7.2 | Precisión de tiempos de rotación | El tiempo de rotación debe calcularse con precisión de minutos | Precisión | | RNF7.3 | Consistencia de estados | Una habitación no puede estar en dos estados simultáneamente (ej. "occupied" y "cleaning") | Integridad | | RNF7.4 | Visibilidad por hotel | Cada usuario solo debe ver las habitaciones de su propiedad asignada | Seguridad | | RNF7.5 | Historial de estados | El sistema debe mantener historial completo de cambios de estado (mínimo 90 días) | Auditoría |
#### 7.5 Reglas de Negocio

| ID RN | Descripción | Origen | |-------|-------------|--------| | RN7.1 | El estado de una habitación se determina por el registro más reciente en `room_status_log` | Housekeeping | | RN7.2 | Una habitación con booking activo (checked_in) se marca como "occupied" automáticamente | Housekeeping | | RN7.3 | Una habitación no puede ser asignada hasta que esté "available" | Housekeeping | | RN7.4 | Solo se puede cambiar el tipo si la habitación está en estado "available", "cleaning" o "maintenance" | Housekeeping | | RN7.5 | Una habitación en mantenimiento no está disponible para reservas | Mantenimiento | | RN7.6 | El mantenimiento preventivo se programa con al menos 7 días de anticipación | Mantenimiento | | RN7.7 | Mantenimiento crítico (avería) se puede programar inmediato con prioridad "crítica" | Mantenimiento | | RN7.8 | El tiempo de rotación se mide desde check-out hasta disponible | Housekeeping | | RN7.9 | Tiempo de rotación objetivo: < 4 horas para hoteles urbanos, < 6 horas para resorts | Housekeeping | | RN7.10 | Estados posibles: available, cleaning_needed, cleaning_in_progress, occupied, maintenance, blocked | Housekeeping |
#### 7.6 Escenarios de Operación

| ID Escenario | Nombre | CU | Descripción | |-------------|--------|----|-------------| | E7.1 | Consulta de matriz de estado de habitaciones | CU-O30 | Recepcionista abre panel y ve: 20 verdes (disponibles), 10 rojas (ocupadas), 3 amarillas (limpieza), 1 gris (mantenimiento) | | E7.2 | Ciclo completo de limpieza post-checkout | CU-O39 | Check-out completado → sistema marca "cleaning_needed". Recepcionista asigna tarea → "cleaning_in_progress". Personal completa → "available". Tiempo: 2h 15min | | E7.3 | Asignación de tipo de habitación | CU-O31 | Recepcionista cambia habitación 101 de "Estándar" a "Suite". Sistema actualiza hotel_rooms.room_type_id | | E7.4 | Programación de mantenimiento preventivo | CU-O40 | Gerente programa mantenimiento de HVAC para habitación 205 el 15-jul. Sistema valida que no esté ocupada | | E7.5 | Reporte mensual de rotación | CU-T14 | Gerente consulta reporte: tiempo promedio de rotación = 3h 45min, dentro del objetivo de 4h | | E7.6 | Dashboard de eficiencia operativa 
#### 7.7 Trazabilidad Individual del Departamento

| OT | OO | CU | HU | |----|----|----|----| | OT3.3: Automatizar gestión habitaciones | OO3.3.1: Consultar estado habitaciones | CU-O30: Estado habitaciones | HU-30 | | OT3.3 | OO3.3.1 | CU-O31: Asignar tipo habitación | HU-31 | | OT3.3 | OO3.3.1 | CU-O32: Disponibilidad por habitación | HU-32 | | OT3.3 | OO3.3.1 | CU-O33: Amenities por tipo habitación | HU-33 | | OT3.3 | OO3.3.2: Gestionar limpieza y rotación | CU-O39: Limpieza y rotación | HU-39 | | OT3.3 | OO3.3.2 | CU-T14: Rotación y limpieza táctico | HU-T14 | | OT3.3 | OO3.3.3: Programar mantenimiento preventivo | CU-O40: Mantenimiento preventivo | HU-40 | | OT3.3 | OO3.3.3 | CU-T15: Mantenimiento proactivo | HU-T15 | | OT5.1: Monitorear eficiencia operativa | OO5.1.1: Monitorear eficiencia | : Eficiencia operativa | HU-E09 |
#### 7.8 KPIs del Departamento

| KPI | Fórmula | Frecuencia | Meta | CU Asociado | |-----|---------|------------|------|-------------| | Tiempo promedio de rotación | AVG(room_status_log.rotation_time_minutes) para el período | Diaria | ≤ 240 min (4h) | CU-O39 | | Cumplimiento de limpieza | (Limpiezas completadas a tiempo / Limpiezas totales) × 100 | Diaria | ≥ 95% | CU-O39 | | Cumplimiento de mantenimiento | (Mantenimientos ejecutados a tiempo / Programados) × 100 | Mensual | ≥ 90% | CU-O40 | | Cargos adicionales por reserva | SUM(additional_charges.amount) / COUNT(booking_orders) | Mensual | ≥ $200 | CU-O34 | | Ocupación real vs disponible | (Habitaciones ocupadas / Habitaciones disponibles) × 100 | Diaria | ≥ 70% | CU-O30 | | Tiempo de inactividad por mantenimiento | Horas de habitación no disponible / Total horas disponibles × 100 | Mensual | ≤ 5% | CU-O40 | | Eficiencia de rotación (T14) | Tiempo real / Tiempo objetivo × 100 | Semanal | ≤ 100% | CU-T14 |
#### 7.9 Colecciones MongoDB Involucradas

| Colección | Tipo de Acceso | Propósito | CU | |-----------|---------------|-----------|----| | `hotel_rooms` | Lectura/Escritura | Datos maestros de habitaciones físicas | CU-O30, O31, O32, O39, O40 | | `room_status_log` | Escritura | Registro de cambios de estado con timestamp | CU-O30, O31, O39 | | `room_inventory_calendar` | Lectura | Disponibilidad por fecha | CU-O30, O32 | | `booking_orders` | Lectura | Ocupación actual de habitaciones | CU-O30, O32 | | `room_types` | Lectura | Tipos de habitación disponibles | CU-O31, O33 | | `housekeeping_tasks` | Escritura | Asignación de tareas de limpieza | CU-O39 | | `maintenance_schedule` | Escritura | Programación de mantenimiento | CU-O40, T15 | | `maintenance_tasks` | Escritura | Ejecución de tareas de mantenimiento | CU-O40 | | `additional_charges` | Lectura | Cargos adicionales (para reportes) | | | `user_activity_logs` | Escritura | Auditoría de acciones | Múltiples CU |
#### 7.10 Flujo de Eventos del Departamento

```
SUBMÓDULO A — Gestión de Estado de Habitaciones (Tiempo Real)
  └── Línea base: Matriz de estado siempre visible en panel
  └── Evento: Check-out completado (CU-O11)
  │     └── Sistema: marca habitación como "cleaning_needed" en room_status_log
  │     └── Sistema: inicia contador de tiempo de rotación
  │
  └── CU-O39: Recepcionista consulta lista de limpieza pendiente
  │     └── Sistema: muestra habitaciones en "cleaning_needed" con tiempo desde check-out
  │
  └── CU-O39: Recepcionista asigna tarea a personal de limpieza
  │     └── Sistema: crea housekeeping_task
  │     └── Sistema: cambia estado a "cleaning_in_progress"
  │
  └── Personal de limpieza completa tarea
  │     └── CU-O39: Recepcionista marca limpieza como completada
  │     └── Sistema: cambia estado a "available" en room_status_log
  │     └── Sistema: calcula y registra tiempo de rotación
  │     └── Sistema: notifica disponibilidad para nuevas reservas
  │
  └── CU-O30: Cualquier usuario autorizado consulta matriz actualizada

SUBMÓDULO B — Mantenimiento Preventivo
  └── CU-O40: Gerente programa mantenimiento
  │     └── Sistema: valida que habitación no esté ocupada en fecha seleccionada
  │     └── Decisión: ¿Disponible? → Sí: crear maintenance_schedule | No: sugerir fechas alternativas
  │
  └── En fecha programada:
  │     └── Gerente marca mantenimiento como "in_progress"
  │     └── Sistema: cambia hotel_rooms.status a "maintenance"
  │     └── Gerente marca como "completed"
  │     └── Sistema: cambia hotel_rooms.status a "available"
  │
  └── CU-T15: Gerente programa mantenimiento proactivo recurrente
        └── Sistema: sugiere fechas basadas en histórico y frecuencia recomendada

SUBMÓDULO C — Monitoreo de Eficiencia Operativa
  └── : Super Admin/Gerente consulta dashboard
  └── Sistema: calcula KPIs desde room_status_log, housekeeping_tasks, maintenance_tasks
  └── Sistema: muestra tarjetas: rotación promedio, cumplimiento limpieza, mantenimiento al día
  └── Sistema: compara con objetivos (T14: < 4h, T15: > 90% cumplimiento)
```

#### 7.11 Fuera de Alcance del Departamento

| Aspecto | Fuera de Alcance | Departamento Responsable | |---------|-----------------|-------------------------| | Facturación y pagos | El departamento no genera facturas ni registra pagos | Facturación y Pagos | | Gestión de contenido del hotel | El departamento no edita descripciones ni imágenes | Marketing Hotelero | | Configuración de tarifas | El departamento no define precios ni promociones | Revenue Management | | Administración de usuarios | El departamento no gestiona cuentas de usuario | Administración / Sistemas | | Ejecución de pipeline ETL | El departamento no ejecuta procesos de datos | Datos / Analítica |
### Departamento 8: Notificaciones y Comunicaciones

| Elemento | Descripción | |----------|-------------| | **Responsable** | Sistema / Super Admin | | **Función** | Gestionar notificaciones automáticas, alertas operativas, plantillas de comunicación y canales de notificación para eventos del sistema | | **Procesos** | Creación y edición de plantillas de notificación, configuración de canales (email, SMS, in-app), envío de alertas operativas, registro de historial de notificaciones | | **Sistemas que usa** | Módulo de notificaciones (plantillas, canales, historial), módulo de alertas operativas | | **CU asociados** | CU-O41, CU-O42 | | **KPIs** | Tasa de entrega de notificaciones, tiempo medio de envío, plantillas activas, alertas generadas |
#### 8.1 Objetivos del Departamento

| ID | Objetivo del Departamento | Descripción | |----|--------------------------|-------------| | OD8.1 | Automatizar las comunicaciones del sistema | Enviar notificaciones automáticas a usuarios y personal sobre eventos relevantes (check-in pendiente, reserva confirmada, mantenimiento programado) | | OD8.2 | Gestionar plantillas de notificación reutilizables | Mantener un catálogo de plantillas parametrizables para email, SMS y notificaciones in-app | | OD8.3 | Alertar sobre eventos operativos críticos | Generar alertas automáticas para el personal del hotel cuando se requiera atención inmediata (check-in no completado, mantenimiento urgente) |
#### 8.2 Actores Involucrados

| Actor | Rol | CU Asociados | |-------|-----|--------------| | **Super Admin** | Configura plantillas, canales y reglas de notificación | CU-O41 | | **Sistema** | Genera notificaciones automáticas basadas en eventos | CU-O41, CU-O42 | | **Gerente de hotel** | Recibe alertas operativas | CU-O42 | | **Recepcionista** | Recibe notificaciones de check-in/out y limpieza | CU-O42 |
#### 8.3 Requisitos Funcionales

| ID RF | Nombre | Descripción | CU | |-------|--------|-------------|----| | RF8.1 | Gestión de plantillas | El sistema debe permitir crear, editar y eliminar plantillas de notificación con variables parametrizables | CU-O41 | | RF8.2 | Configuración de canales | El sistema debe permitir configurar canales de envío (email, notificación in-app) por tipo de evento | CU-O41 | | RF8.3 | Envío automático de notificaciones | El sistema debe enviar notificaciones automáticas al ocurrir eventos del ciclo de vida de la reserva | CU-O41 | | RF8.4 | Validación del ciclo de vida de la reserva | El sistema debe validar que el ciclo de vida de cada reserva (pending → confirmed → checked_in → checked_out) se complete sin anomalías | CU-O42 | | RF8.5 | Alerta de anomalías en reservas | El sistema debe generar alertas cuando una reserva permanezca en un estado intermedio más tiempo del esperado | CU-O42 | | RF8.6 | Historial de notificaciones | El sistema debe mantener un registro de todas las notificaciones enviadas con estado de entrega | CU-O41 |
#### 8.4 Reglas de Negocio

| ID RN | Descripción | |-------|-------------| | RN8.1 | Una reserva en "pending" por más de 24h debe generar una alerta al gerente | | RN8.2 | Un check-in programado para hoy que no se haya completado a las 18:00 debe generar una alerta | | RN8.3 | Las notificaciones de mantenimiento deben enviarse con 48h de anticipación | | RN8.4 | Las plantillas deben soportar variables: {hotel_name}, {guest_name}, {booking_id}, {check_in}, {check_out} |
#### 8.5 KPIs del Departamento

| KPI | Frecuencia | Meta | |-----|------------|------| | Tasa de entrega de notificaciones | Mensual | ≥ 99% | | Tiempo medio de envío | Diaria | ≤ 30 segundos | | Alertas generadas por día | Diaria | — | | Tiempo medio de resolución de alerta | Semanal | ≤ 2 horas | | Anomalías de ciclo de vida detectadas | Mensual | — |
#### 8.6 Flujo de Eventos del Departamento

```
Evento: Notificación Automática
  └── Ocurre un evento del sistema (reserva creada, check-in pendiente, mantenimiento programado)
  └── Sistema: consulta plantilla correspondiente al tipo de evento
  └── Sistema: reemplaza variables con datos del evento
  └── Sistema: envía notificación por canal configurado (email, in-app)
  └── Sistema: registra en historial de notificaciones

Evento: Validación de Ciclo de Vida (CU-O42)
  └── Sistema: ejecuta tarea programada cada hora
  └── Sistema: consulta booking_orders con estados anómalos
  └── Detección: reservas en "pending" > 24h sin acción del gerente
  └── Detección: check-ins programados para hoy no completados después de las 18:00
  └── Detección: reservas "confirmed" con check_in ya vencido
  └── Sistema: genera alerta en el panel de notificaciones
  └── Sistema: envía notificación al gerente/responsable
```

#### 8.7 Trazabilidad Individual del Departamento

| OT | OO | CU | HU | |----|----|----|----| | OT3.2: Automatizar gobierno de datos | OO3.2.2: Registrar auditoría y trazabilidad | CU-O41: Gestionar notificaciones | HU-41 | | OT3.3: Automatizar gestión habitaciones | OO3.3.5: Validar ciclo de vida de reservas | CU-O42: Validar ciclo de vida reserva | HU-42 |
#### 8.8 Colecciones MongoDB Involucradas

| Colección | Tipo de Acceso | Propósito | CU | |-----------|---------------|-----------|----| | `notification_history` | Escritura/Lectura | Registro de notificaciones enviadas con estado de entrega | CU-O41 | | `notification_templates` | Escritura/Lectura | Plantillas de notificación parametrizables | CU-O41 | | `notification_channels` | Escritura/Lectura | Configuración de canales por tipo de evento | CU-O41 | | `booking_orders` | Lectura | Consulta de estados de reserva para validación de ciclo de vida | CU-O42 | | `booking_status_history` | Lectura | Historial de cambios de estado de reserva | CU-O42 | | `alerts` | Escritura | Generación de alertas operativas | CU-O42 |
#### 8.9 Fuera de Alcance del Departamento

| Aspecto | Fuera de Alcance | Departamento Responsable | |---------|-----------------|-------------------------| | Comunicación directa con huéspedes vía SMS/WhatsApp | El sistema no tiene integración directa con proveedores de SMS o WhatsApp | — | | Diseño visual de plantillas HTML | El sistema no incluye editor visual de plantillas (solo texto parametrizable) | — | | Historial de acciones del usuario | El departamento no gestiona logs de actividad de usuario | Administración / Sistemas |
### Departamento 9: Facturación y Pagos

| Elemento | Descripción | |----------|-------------| | **Responsable** | Recepcionista / Sistema | | **Función** | Gestionar la generación de facturas, comprobantes fiscales, registro de pagos, cargos adicionales y conciliación financiera de las reservas | | **Procesos** | Generación de factura con datos fiscales, registro de pagos (efectivo, tarjeta, transferencia), registro de cargos adicionales a reserva, conciliación de pagos contra factura | | **Sistemas que usa** | Módulo de facturación (billing), módulo de pagos, módulo de cargos adicionales | | **CU asociados** | CU-O24, CU-O25, CU-O34 | | **KPIs** | Facturas generadas por período, pagos registrados, cargos adicionales por reserva, tiempo de facturación post-checkout |
#### 9.1 Objetivos del Departamento

| ID | Objetivo del Departamento | Descripción | |----|--------------------------|-------------| | OD9.1 | Generar comprobantes fiscales de reservas finalizadas | Emitir facturas con datos fiscales del huésped y folio único por cada reserva en estado checked_out | | OD9.2 | Registrar pagos asociados a reservas | Capturar pagos en efectivo, tarjeta o transferencia vinculados a booking_orders con trazabilidad completa | | OD9.3 | Gestionar cargos adicionales intra-estancia | Permitir registrar consumos y servicios adicionales durante la estancia que se reflejen en la factura final | | OD9.4 | Evitar pagos duplicados o montos excedidos | Validar que los pagos no superen el total de la reserva y que no existan facturas duplicadas |
#### 9.2 Actores Involucrados

| Actor | Rol | CU Asociados | |-------|-----|--------------| | **Recepcionista** | Genera facturas, registra pagos y cargos adicionales de huéspedes | CU-O24, CU-O25, CU-O34 | | **Gerente de hotel** | Consulta reportes de facturación y pagos | CU-O26 | | **Sistema** | Genera folios únicos, valida montos, actualiza saldos de reserva | CU-O24, CU-O25, CU-O34 |
#### 9.3 Requisitos Funcionales

| ID RF | Nombre | Descripción | CU | |-------|--------|-------------|----| | RF9.1 | Generación de factura | El sistema debe generar factura con folio único, datos fiscales y desglose de cargos | CU-O24 | | RF9.2 | Datos fiscales del huésped | El sistema debe capturar RFC, razón social y régimen fiscal del huésped | CU-O24 | | RF9.3 | Validación de estado facturable | El sistema debe validar que la reserva esté en estado checked_out antes de facturar | CU-O24 | | RF9.4 | Detección de factura duplicada | El sistema debe impedir generar una segunda factura para la misma reserva | CU-O24 | | RF9.5 | Registro de pago | El sistema debe registrar pagos con monto, método, referencia y fecha | CU-O25 | | RF9.6 | Validación de monto máximo | El sistema debe rechazar pagos cuyo monto exceda el total pendiente de la reserva | CU-O25 | | RF9.7 | Registro de cargos adicionales | El sistema debe permitir registrar cargos adicionales durante la estancia activa | CU-O34 | | RF9.8 | Cargos solo en estancia activa | El sistema debe permitir cargos solo en reservas en estado confirmed o checked_in | CU-O34 | | RF9.9 | Actualización de saldo pendiente | El sistema debe recalcular el saldo pendiente al registrar pagos y cargos | CU-O25, CU-O34 |
#### 9.4 Reglas de Negocio

| ID RN | Descripción | |-------|-------------| | RN9.1 | Una reserva solo puede tener una factura asociada | | RN9.2 | La factura solo puede generarse cuando la reserva está en estado "checked_out" | | RN9.3 | El monto total de pagos registrados no puede exceder el total de la reserva | | RN9.4 | Los cargos adicionales solo pueden registrarse en reservas con estado "confirmed" o "checked_in" | | RN9.5 | El folio de factura debe ser único en todo el sistema (formato: FAC-{hotel_id}-{YYYYMMDD}-{secuencial}) | | RN9.6 | Un pago no puede ser modificado ni eliminado después de registrado |
#### 9.5 KPIs del Departamento

| KPI | Frecuencia | Meta | |-----|------------|------| | Facturas generadas por período | Mensual | — | | Tasa de facturación post-checkout | Semanal | ≥ 80% a las 48h | | Cargos adicionales promedio por reserva | Mensual | ≥ $200 | | Tiempo medio entre check-out y facturación | Diaria | ≤ 24h | | Pagos registrados vs total de reservas | Mensual | ≥ 95% |
#### 9.6 Flujo de Eventos del Departamento

```
SUBMÓDULO A — Facturación
  └── Evento: Check-out completado (CU-O11)
  │     └── Sistema: marca reserva como facturable
  │
  └── CU-O24: Recepcionista genera factura
        └── Sistema: valida estado checked_out
        └── Sistema: consulta booking_orders, additional_charges, room_inventory_calendar
        └── Sistema: calcula total (noches × precio + cargos adicionales)
        └── Recepcionista: ingresa datos fiscales (RFC, razón social)
        └── Sistema: genera folio único FAC-{hotel_id}-{YYYYMMDD}-{NNNN}
        └── Sistema: crea documento en billing_invoices
        └── Sistema: muestra factura generada con folio

SUBMÓDULO B — Pagos
  └── CU-O25: Recepcionista registra pago
  └── Sistema: valida que monto ≤ total pendiente de la reserva
  └── Sistema: registra en billing_payments con booking_id, monto, método, referencia
  └── Sistema: actualiza saldo pendiente

SUBMÓDULO C — Cargos Adicionales
  └── CU-O34: Recepcionista registra cargo durante estancia
  └── Sistema: valida estado (confirmed o checked_in)
  └── Sistema: registra en additional_charges con tipo, descripción, monto
  └── Sistema: actualiza total pendiente de la reserva
```

#### 9.7 Trazabilidad Individual del Departamento

| OT | OO | CU | HU | |----|----|----|----| | OT1.2: Fortalecer reputación del huésped | OO1.2.2: Generar comprobantes/facturación | CU-O24: Generar factura | HU-24 | | OT1.2 | OO1.2.2 | CU-O25: Registrar pago | HU-25 | | OT3.3: Automatizar gestión habitaciones | OO3.3.4: Registrar cargos adicionales | CU-O34: Registrar cargos adicionales | HU-34 |
#### 9.8 Colecciones MongoDB Involucradas

| Colección | Tipo de Acceso | Propósito | CU | |-----------|---------------|-----------|----| | `billing_invoices` | Escritura | Factura generada con datos fiscales y folio único | CU-O24 | | `billing_payments` | Escritura | Pagos registrados asociados a reservas | CU-O25 | | `additional_charges` | Escritura/Lectura | Cargos adicionales durante estancia | CU-O34 | | `booking_orders` | Lectura | Consulta de datos de la reserva para facturación | CU-O24, O25, O34 | | `fact_invoices` | Escritura | Hechos de factura para analítica | CU-O24 | | `fact_payments` | Escritura | Hechos de pago para analítica | CU-O25 |
#### 9.9 Fuera de Alcance del Departamento

| Aspecto | Fuera de Alcance | Departamento Responsable | |---------|-----------------|-------------------------| | Procesamiento de pagos en línea | El sistema no se conecta a pasarelas de pago (PayPal, Stripe) | — | | Conciliación bancaria | El sistema no realiza conciliación automática contra estados de cuenta bancarios | Administración / Sistemas | | Gestión de devoluciones y reembolsos | El sistema no procesa reembolsos automáticos | Revenue Management | | Facturación CFDI electrónica México | El sistema no genera XML de CFDI ni timbra ante el SAT | — |
---

# 4. PAQUETES DEL SISTEMA

## 4.1 Mapa de Paquetes

El sistema HotelData se organiza en 10 paquetes funcionales que agrupan los módulos, colecciones y casos de uso relacionados.

| # | Paquete | Descripción | Módulo backend | Colecciones principales | |---|---------|-------------|----------------|------------------------| | 1 | **Autenticación y Seguridad** | Gestión de identidad, sesiones, roles y permisos de acceso | auth, admin (usuarios/roles) | users, user_sessions, user_activity_logs, roles, permissions, role_permissions | | 2 | **Búsqueda y Experiencia Cliente** | Motor de búsqueda hotelera, filtros, comparación y detalle de propiedad | hotels | dim_hotels, hotels, locations, contacts, facilities, attractions | | 3 | **Core de Reservas** | Ciclo de vida completo de la reserva: solicitud, confirmación, check-in, check-out, cancelación | reservations | booking_orders, booking_guests, booking_status_history, manual_reservations | | 4 | **Gestión Hotelera (Partner Central)** | Administración de propiedades, habitaciones, inventario, tarifas, políticas, contenido e imágenes | partner (rooms, rates, content, policies, amenities, hotels) | room_types, hotel_rooms, room_inventory_calendar, rate_plans, hotel_rate_calendar, hotel_policies, hotel_content_pages, hotel_images, hotel_profile_changes | | 5 | **Promociones y Revenue** | Campañas promocionales, cupones, descuentos y análisis de ingresos | revenue | promotion_campaigns, coupon_codes, rate_plans, hotel_rate_calendar | | 6 | **Reseñas y Reputación** | Registro, moderación y respuesta de reseñas de huéspedes | reviews | reviews, fact_reviews | | 7 | **Facturación y Pagos** | Generación de comprobantes, facturas y registro de pagos | billing | reservation_invoices, reservation_payments, fact_invoices, fact_payments | | 8 | **Reportes y Analítica** | Dashboards ejecutivos, reportes de revenue, calidad de datos y análisis de mercado | revenue (reportes), dashboard, quality, audit | data_quality_reports, etl_executions, fact_hotel_reservations, dim_* | | 9 | **Mapa y Geo-localización** | Visualización de destinos y hoteles en mapa mundial interactivo con Leaflet.js, selección de ubicación por coordenadas | map | destinations_enriched, hotel_locations_geo | | 10 | **Housekeeping y Mantenimiento** | Gestión de estado de habitaciones, limpieza, rotación, mantenimiento preventivo y cargos adicionales | housekeeping, maintenance | room_status_log, housekeeping_tasks, maintenance_schedule, maintenance_tasks, additional_charges |
---

# 5. MATRIZ NIVEL → DEPARTAMENTO → PAQUETE → CASO DE USO

## 5.1 Matriz Completa de la Parte Operativa (CU-O01 a CU-O42) + Tácticos (T14-T15)

La siguiente matriz relaciona los niveles organizacionales, departamentos funcionales, paquetes del sistema y casos de uso operativos de HotelData.

| Código CU | Nivel | Departamento | Paquete | Nombre del Caso de Uso | Actor Principal | |-----------|-------|-------------|---------|----------------------|-----------------| | CU-O01 | Operativo | Administración/Sistemas | Autenticación y Seguridad | Iniciar sesión con autenticación JWT y rol | Todos los usuarios | | CU-O02 | Operativo | Comercial/Cliente | Búsqueda y Experiencia Cliente | Buscar hoteles | Cliente | | CU-O03 | Operativo | Comercial/Cliente | Búsqueda y Experiencia Cliente | Filtrar y comparar hoteles | Cliente | | CU-O04 | Operativo | Comercial/Cliente | Búsqueda y Experiencia Cliente | Ver detalle de hotel | Cliente | | CU-O05 | Operativo | Comercial/Cliente | Core de Reservas | Solicitar reserva | Cliente | | CU-O06 | Operativo | Comercial/Cliente | Core de Reservas | Consultar mis reservas | Cliente | | CU-O07 | Operativo | Comercial/Cliente | Core de Reservas | Cancelar reserva según política | Cliente | | CU-O08 | Operativo | Operaciones Hoteleras | Core de Reservas | Registrar reserva manual | Recepcionista | | CU-O09 | Operativo | Operaciones Hoteleras | Core de Reservas | Consultar solicitudes de reserva | Gerente de hotel | | CU-O10 | Operativo | Operaciones Hoteleras | Core de Reservas | Completar check-in | Recepcionista | | CU-O11 | Operativo | Operaciones Hoteleras | Core de Reservas | Completar check-out | Recepcionista | | CU-O12 | Operativo | Marketing Hotelero | Gestión Hotelera (Partner Central) | Editar nombre comercial del hotel | Marketing / Partner | | CU-O13 | Operativo | Administración/Sistemas | Gestión Hotelera (Partner Central) | Consultar historial de cambios de propiedad | Auditor de Datos / Partner | | CU-O14 | Operativo | Operaciones Hoteleras | Gestión Hotelera (Partner Central) | Crear tipo de habitación | Hotel partner | | CU-O15 | Operativo | Operaciones Hoteleras | Gestión Hotelera (Partner Central) | Actualizar inventario por fecha | Gerente de hotel | | CU-O16 | Operativo | Operaciones Hoteleras | Gestión Hotelera (Partner Central) | Registrar bloqueo de disponibilidad | Gerente de hotel | | CU-O17 | Operativo | Revenue Management | Promociones y Revenue | Crear plan tarifario | Revenue manager | | CU-O18 | Operativo | Revenue Management | Promociones y Revenue | Configurar tarifa por fecha | Revenue manager | | CU-O19 | Operativo | Revenue Management | Promociones y Revenue | Crear promoción y cupón | Marketing / Revenue | | CU-O20 | Operativo | Operaciones Hoteleras | Gestión Hotelera (Partner Central) | Editar política hotelera | Hotel partner | | CU-O21 | Operativo | Marketing Hotelero | Gestión Hotelera (Partner Central) | Actualizar amenities, imágenes y contenido | Marketing hotelero | | CU-O22 | Operativo | Marketing Hotelero | Reseñas y Reputación | Registrar reseña de estancia | Cliente | | CU-O23 | Operativo | Marketing Hotelero | Reseñas y Reputación | Moderar y responder reseña | Marketing / Admin | | CU-O24 | Operativo | Operaciones Hoteleras | Facturación y Pagos | Generar comprobante o factura de reserva | Sistema / Recepcionista | | CU-O25 | Operativo | Operaciones Hoteleras | Facturación y Pagos | Registrar pago asociado a reserva | Recepcionista | | CU-O26 | Operativo | Revenue Management | Reportes y Analítica | Consultar reportes de revenue y mercado | Gerente / Revenue | | CU-O27 | Operativo | Datos/Analítica | Reportes y Analítica | Consultar reporte de calidad y registros rechazados | Auditor de Datos | | CU-O28 | Operativo | Administración/Sistemas | Autenticación y Seguridad | Administrar cuenta, sesión y cierre seguro | Todos los usuarios | | CU-O29 | Operativo | Administración/Sistemas | Autenticación y Seguridad | Cambiar contraseña y actualizar perfil de usuario | Todos los usuarios | | CU-O30 | Operativo | Operaciones Hoteleras | Gestión Hotelera (Partner Central) | Consultar estado actual de habitaciones | Recepcionista / Gerente | | CU-O31 | Operativo | Operaciones Hoteleras | Gestión Hotelera (Partner Central) | Asignar tipo de habitación a habitación individual | Recepcionista / Gerente | | CU-O32 | Operativo | Operaciones Hoteleras | Gestión Hotelera (Partner Central) | Consultar disponibilidad por habitación individual | Recepcionista / Gerente | | CU-O33 | Operativo | Operaciones Hoteleras | Gestión Hotelera (Partner Central) | Gestionar amenities por tipo de habitación | Hotel partner / Marketing | | CU-O34 | Operativo | Revenue Management | Promociones y Revenue | Registrar cargos adicionales a reserva | Recepcionista / Gerente | | CU-O35 | Operativo | Datos/Analítica | Mapa y Geo-localización | Editar metadata de destino (nombre, coordenadas geográficas) | Auditor de Datos | | CU-O36 | Operativo | Datos/Analítica | Gestión Hotelera (Partner Central) | Editar nombre visible de hotel (manual_override) | Auditor de Datos / Marketing | | CU-O37 | Operativo | Datos/Analítica | Mapa y Geo-localización | Visualizar mapa mundial de destinos con hoteles geolocalizados | Auditor de Datos / Marketing | | CU-O38 | Operativo | Datos/Analítica | Mapa y Geo-localización | Seleccionar ubicación de destino en mapa interactivo | Auditor de Datos | | CU-O39 | Operativo | Operaciones Hoteleras | Housekeeping y Mantenimiento | Gestionar limpieza y rotación de habitaciones | Recepcionista / Gerente | | CU-O40 | Operativo | Operaciones Hoteleras | Housekeeping y Mantenimiento | Gestionar mantenimiento preventivo de habitaciones | Gerente de hotel | | CU-T14 | Táctico | Operaciones Hoteleras | Housekeeping y Mantenimiento | Gestionar rotación y limpieza de habitaciones | Gerente de hotel | | CU-T15 | Táctico | Operaciones Hoteleras | Housekeeping y Mantenimiento | Programar mantenimiento preventivo proactivo | Gerente de hotel |
---

# 6. ESPECIFICACIÓN DETALLADA DE CASOS DE USO OPERATIVOS

## 6.1 Estructura de la Especificación

Cada caso de uso operativo se especifica con la siguiente estructura:

| Sección | Descripción | |---------|-------------| | **Código** | Identificador único del caso de uso | | **Nombre** | Nombre descriptivo del caso de uso | | **Objetivo** | Propósito del caso de uso en el negocio hotelero | | **Actor Principal** | Usuario que ejecuta el caso de uso | | **Actores Secundarios** | Otros sistemas o usuarios involucrados | | **Disparador** | Evento que inicia el caso de uso |    | **Reglas de Negocio** | Reglas del dominio hotelero que aplican |     | **Colecciones MongoDB** | Colecciones involucradas | | **Endpoints** | Rutas de API expuestas |
---

## 6.2 CU-O01: Iniciar Sesión con Autenticación JWT y Rol

| Elemento | Detalle | |----------|---------| | **Código** | CU-O01 | | **Nombre** | Iniciar sesión con autenticación JWT y rol | | **Objetivo** | Permitir que cualquier usuario registrado acceda al sistema mediante credenciales (email + contraseña), validando su identidad, verificando el estado de su cuenta y estableciendo una sesión segura con redirección según su rol | | **Actor Principal** | Todos los usuarios del sistema (cliente, recepcionista, hotel partner, gerente, revenue manager, marketing, super admin, auditor de datos) | | **Actores Secundarios** | Sistema (generación de token, registro de auditoría) | | **Disparador** | El usuario accede a la página de login e ingresa sus credenciales |    | **Reglas de Negocio** | **RN-O01-01:** El mensaje de error para credenciales inválidas debe ser genérico: "Credenciales inválidas". No debe revelar si el email no existe o la contraseña es incorrecta (medida de seguridad contra enumeración de usuarios).<br>**RN-O01-02:** Una cuenta desactivada no puede iniciar sesión bajo ninguna circunstancia.<br>**RN-O01-03:** Cada usuario solo puede tener una sesión activa a la vez. Si el usuario ya tiene una sesión activa y hace login, la sesión anterior se invalida automáticamente.<br>**RN-O01-04:** La sesión expira después de 8 horas de inactividad. El TTL index de MongoDB elimina automáticamente los documentos expirados. |     | **Colecciones MongoDB** | `users` (lectura: email, password_hash, is_active, primary_role)<br>`user_sessions` (escritura: token_hash, user_id, role, created_at, expires_at)<br>`user_activity_logs` (escritura: tipo, user_id, email, rol, timestamp, éxito/fallo) | | **Endpoints** | `GET /auth/login` — Formulario HTML de login.<br>`POST /auth/login` — Procesa login desde formulario HTML.<br>`POST /api/auth/login` — Login vía API JSON.<br>`GET /api/auth/me` — Consulta sesión actual. |
---

## 6.3 CU-O02: Buscar Hoteles

| Elemento | Detalle | |----------|---------| | **Código** | CU-O02 | | **Nombre** | Buscar hoteles | | **Objetivo** | Permitir que el cliente busque hoteles disponibles ingresando destino, fechas y número de huéspedes, obteniendo una lista de propiedades con precios, ratings e imágenes | | **Actor Principal** | Cliente / Viajero | | **Actores Secundarios** | Sistema (consulta a MongoDB, cálculo de disponibilidad) | | **Disparador** | El cliente accede a la página de búsqueda e ingresa los parámetros de su viaje |    | **Reglas de Negocio** | **RN-O02-01:** Solo se muestran hoteles con al menos un tipo de habitación disponible en todas las noches solicitadas.<br>**RN-O02-02:** El precio mostrado es el precio mínimo por noche entre todos los tipos de habitación disponibles.<br>**RN-O02-03:** Los resultados se ordenan por precio ascendente por defecto. |     | **Colecciones MongoDB** | `dim_hotels` (lectura), `hotels` (lectura), `locations` (lectura), `room_inventory_calendar` (lectura), `hotel_rate_calendar` (lectura) | | **Endpoints** | `GET /hotels/search` — Página de búsqueda HTML.<br>`GET /api/hotels/search` — API de búsqueda JSON. |
---

## 6.4 CU-O03: Filtrar y Comparar Hoteles

| Elemento | Detalle | |----------|---------| | **Código** | CU-O03 | | **Nombre** | Filtrar y comparar hoteles | | **Objetivo** | Permitir que el cliente refine los resultados de búsqueda mediante filtros (precio, rating, amenities) y compare hasta 3 hoteles lado a lado para tomar una decisión informada | | **Actor Principal** | Cliente / Viajero | | **Actores Secundarios** | Sistema | | **Disparador** | El cliente ha realizado una búsqueda y desea refinar los resultados o comparar opciones |    | **Reglas de Negocio** | **RN-O03-01:** Los filtros de precio y rating se aplican sobre los datos de `dim_hotels`.<br>**RN-O03-02:** La comparación muestra máximo 3 hoteles simultáneamente.<br>**RN-O03-03:** Los amenities se obtienen desde `hotel_content_pages` y `hotel_quality`. |     | **Colecciones MongoDB** | `dim_hotels`, `hotel_content_pages`, `hotel_images`, `hotel_quality` | | **Endpoints** | `GET /api/hotels/search?precio_min=X&precio_max=Y&rating_min=Z`<br>`GET /hotels/compare?ids=id1,id2,id3` |
---

## 6.5 CU-O04: Ver Detalle de Hotel

| Elemento | Detalle | |----------|---------| | **Código** | CU-O04 | | **Nombre** | Ver detalle de hotel | | **Objetivo** | Mostrar al cliente la información completa de una propiedad hotelera: galería de imágenes, descripción, amenities, políticas, tarifas por tipo de habitación con disponibilidad, reseñas de huéspedes y ubicación | | **Actor Principal** | Cliente / Viajero | | **Actores Secundarios** | Sistema | | **Disparador** | El cliente hace clic en un hotel desde los resultados de búsqueda o comparación |    | **Reglas de Negocio** | **RN-O04-01:** Las tarifas mostradas son por noche e incluyen impuestos si están configurados.<br>**RN-O04-02:** Las reseñas se muestran ordenadas por fecha descendente, máximo 10 inicialmente.<br>**RN-O04-03:** Las políticas de cancelación se muestran según lo configurado en `hotel_policies`. |     | **Colecciones MongoDB** | `dim_hotels`, `hotel_content_pages`, `hotel_images`, `hotel_policies`, `room_types`, `hotel_rate_calendar`, `reviews`, `fact_reviews` | | **Endpoints** | `GET /hotels/{prop_id}` — Página de detalle HTML.<br>`GET /api/hotels/{prop_id}` — API de detalle JSON. |
---

## 6.6 CU-O05: Solicitar Reserva

| Elemento | Detalle | |----------|---------| | **Código** | CU-O05 | | **Nombre** | Solicitar reserva | | **Objetivo** | Permitir que el cliente solicite una reserva seleccionando tipo de habitación, fechas, datos de huéspedes, creando una orden de reserva en estado "pending" con trazabilidad completa | | **Actor Principal** | Cliente / Viajero | | **Actores Secundarios** | Sistema (creación de booking_order, booking_guests, booking_status_history) | | **Disparador** | El cliente, desde la página de detalle del hotel, hace clic en "Reservar" para un tipo de habitación y fechas específicas |    | **Reglas de Negocio** | **RN-O05-01:** Una reserva se crea siempre en estado "pending". Requiere confirmación del gerente del hotel para pasar a "confirmed".<br>**RN-O05-02:** El inventario no se descuenta hasta que la reserva pasa a estado "confirmed".<br>**RN-O05-03:** El precio total se calcula al momento de la solicitud y no varía después.<br>**RN-O05-04:** Una reserva debe tener al menos un huésped asociado. |     | **Colecciones MongoDB** | `booking_orders` (escritura), `booking_guests` (escritura), `booking_status_history` (escritura), `room_inventory_calendar` (lectura), `hotel_rate_calendar` (lectura) | | **Endpoints** | `GET /reservations/new` — Formulario de nueva reserva HTML.<br>`POST /reservations/new` — Crear reserva desde formulario HTML.<br>`POST /api/reservations` — Crear reserva vía API JSON. |
---

## 6.7 CU-O06: Consultar Mis Reservas

| Elemento | Detalle | |----------|---------| | **Código** | CU-O06 | | **Nombre** | Consultar mis reservas | | **Objetivo** | Permitir que el cliente (y el gerente de hotel) consulten el listado de reservas con estado, fechas, hotel, monto y acciones disponibles | | **Actor Principal** | Cliente / Viajero (consulta sus propias reservas). Gerente de hotel (consulta reservas de su propiedad) | | **Actores Secundarios** | Sistema | | **Disparador** | El cliente navega a "Mis reservas" desde el menú de usuario. El gerente navega a "Reservas" desde el panel de gestión |    | **Reglas de Negocio** | **RN-O06-01:** Un cliente solo puede ver sus propias reservas (filtro por user_id).<br>**RN-O06-02:** Un gerente puede ver todas las reservas de sus propiedades asignadas.<br>**RN-O06-03:** Las reservas se muestran ordenadas por fecha de creación descendente (más recientes primero). |     | **Colecciones MongoDB** | `booking_orders` (lectura), `booking_guests` (lectura), `booking_status_history` (lectura), `dim_hotels` (lectura) | | **Endpoints** | `GET /reservations` — Listado HTML para cliente.<br>`GET /reservations/{booking_id}` — Detalle de reserva HTML.<br>`GET /api/reservations` — Listado API JSON.<br>`GET /api/reservations/{booking_id}` — Detalle API JSON. |
---

## 6.8 CU-O07: Cancelar Reserva Según Política

| Elemento | Detalle | |----------|---------| | **Código** | CU-O07 | | **Nombre** | Cancelar reserva según política | | **Objetivo** | Permitir que el cliente cancele una reserva existente validando las políticas de cancelación del hotel, registrando el cambio de estado con trazabilidad | | **Actor Principal** | Cliente / Viajero (cancela su propia reserva). Gerente de hotel (cancela cualquier reserva de su propiedad) | | **Actores Secundarios** | Sistema (validación de política, liberación de inventario) | | **Disparador** | El usuario hace clic en "Cancelar reserva" desde el detalle o listado de reservas |    | **Reglas de Negocio** | **RN-O07-01:** Una reserva solo puede cancelarse si está en estado "pending" o "confirmed".<br>**RN-O07-02:** La política de cancelación se obtiene del hotel (`hotel_policies.cancellation_policy`) y puede variar por hotel.<br>**RN-O07-03:** Si la reserva estaba "confirmed" y se cancela, el inventario debe liberarse automáticamente.<br>**RN-O07-04:** La cancelación queda registrada permanentemente en `booking_status_history` como evidencia de trazabilidad. |     | **Colecciones MongoDB** | `booking_orders` (actualización), `booking_status_history` (escritura), `room_inventory_calendar` (actualización), `hotel_policies` (lectura), `user_activity_logs` (escritura) | | **Endpoints** | `POST /reservations/{booking_id}/cancel` — Cancelar desde formulario HTML.<br>`POST /api/reservations/{booking_id}/cancel` — Cancelar vía API JSON. |
---

## 6.9 CU-O08: Registrar Reserva Manual

| Elemento | Detalle | |----------|---------| | **Código** | CU-O08 | | **Nombre** | Registrar reserva manual | | **Objetivo** | Permitir que el recepcionista cree una reserva manualmente desde el panel de gestión para reservas telefónicas, walk-in (huésped sin reserva previa) o cortesía, creando la reserva directamente en estado "confirmed" | | **Actor Principal** | Recepcionista | | **Actores Secundarios** | Sistema, Hotel partner | | **Disparador** | El recepcionista recibe una solicitud de reserva por teléfono o un huésped llega sin reserva (walk-in) |    | **Reglas de Negocio** | **RN-O08-01:** La reserva manual se crea en estado "confirmed" directamente, no "pending".<br>**RN-O08-02:** El inventario se descuenta inmediatamente al crear la reserva manual.<br>**RN-O08-03:** Las reservas manuales quedan registradas en la colección `manual_reservations` para trazabilidad. |     | **Colecciones MongoDB** | `booking_orders` (escritura), `booking_guests` (escritura), `booking_status_history` (escritura), `room_inventory_calendar` (actualización), `manual_reservations` (escritura) | | **Endpoints** | `GET /partner/manual-reservations/new` — Formulario HTML.<br>`POST /partner/manual-reservations/new` — Crear reserva manual. |
---

## 6.10 CU-O09: Consultar Solicitudes de Reserva

| Elemento | Detalle | |----------|---------| | **Código** | CU-O09 | | **Nombre** | Consultar solicitudes de reserva | | **Objetivo** | Permitir que el gerente de hotel consulte todas las solicitudes de reserva (en estado "pending") para su propiedad, y pueda confirmarlas o rechazarlas | | **Actor Principal** | Gerente de hotel | | **Actores Secundarios** | Sistema | | **Disparador** | El gerente accede al panel de gestión y selecciona "Solicitudes de reserva" |    | **Reglas de Negocio** | **RN-O09-01:** Una solicitud en "pending" que no se confirma en 24 horas se cancela automáticamente.<br>**RN-O09-02:** Solo el gerente del hotel puede confirmar o rechazar solicitudes de su propiedad. |    | **Colecciones MongoDB** | `booking_orders`, `booking_guests`, `dim_hotels` | | **Endpoints** | `GET /api/reservations?estado=pending` — Solicitudes pendientes API. |
---

## 6.11 CU-O10: Completar Check-In

| Elemento | Detalle | |----------|---------| | **Código** | CU-O10 | | **Nombre** | Completar check-in | | **Objetivo** | Permitir que el recepcionista registre la llegada del huésped, cambiando el estado de la reserva de "confirmed" a "checked_in" y marcando la habitación como ocupada | | **Actor Principal** | Recepcionista | | **Actores Secundarios** | Sistema | | **Disparador** | El huésped llega al hotel y el recepcionista procede a realizar el check-in |    | **Reglas de Negocio** | **RN-O10-01:** Solo reservas en estado "confirmed" pueden hacer check-in.<br>**RN-O10-02:** El check-in solo puede completarse en la fecha de check-in o posterior.<br>**RN-O10-03:** Una vez en "checked_in", la reserva no puede cancelarse (solo por excepción del gerente). |     | **Colecciones MongoDB** | `booking_orders` (actualización), `booking_status_history` (escritura), `room_inventory_calendar` (actualización) | | **Endpoints** | `GET /api/management/check-ins` — Lista de check-ins del día.<br>`POST /api/management/check-ins/{booking_id}/complete` — Completar check-in. |
---

## 6.12 CU-O11: Completar Check-Out

| Elemento | Detalle | |----------|---------| | **Código** | CU-O11 | | **Nombre** | Completar check-out | | **Objetivo** | Permitir que el recepcionista registre la salida del huésped, cambiando el estado de "checked_in" a "checked_out" y liberando la habitación para nuevas reservas | | **Actor Principal** | Recepcionista | | **Actores Secundarios** | Sistema | | **Disparador** | El huésped finaliza su estancia y el recepcionista procede al check-out |    | **Reglas de Negocio** | **RN-O11-01:** Solo reservas en estado "checked_in" pueden hacer check-out.<br>**RN-O11-02:** El check-out libera el inventario inmediatamente.<br>**RN-O11-03:** Un "checked_out" es el estado final del ciclo de vida de la reserva. |     | **Colecciones MongoDB** | `booking_orders` (actualización), `booking_status_history` (escritura), `room_inventory_calendar` (actualización) | | **Endpoints** | `GET /api/management/check-outs` — Lista de check-outs del día.<br>`POST /api/management/check-outs/{booking_id}/complete` — Completar check-out. |
---

## 6.13 CU-O12: Editar Nombre Comercial del Hotel

| Elemento | Detalle | |----------|---------| | **Código** | CU-O12 | | **Nombre** | Editar nombre comercial del hotel | | **Objetivo** | Permitir que el hotel partner o marketing edite el nombre comercial visible del hotel (display_name, hotel_name, descripciones), preservando el prop_id técnico inmutable y activando manual_override para evitar sobrescritura del ETL | | **Actor Principal** | Marketing hotelero, Hotel partner | | **Actores Secundarios** | Sistema, ETL | | **Disparador** | El usuario desea actualizar el nombre comercial de una propiedad para mejorar su presentación en buscadores y detalle |    | **Reglas de Negocio** | **RN-O12-01:** El `prop_id` es la clave técnica inmutable de la propiedad y nunca debe cambiar.<br>**RN-O12-02:** `manual_override` impide que el ETL (GA03, TA02) sobrescriba el nombre editado manualmente.<br>**RN-O12-03:** Todos los cambios de perfil quedan registrados en `hotel_profile_changes` para trazabilidad. |     | **Colecciones MongoDB** | `dim_hotels` (actualización), `hotel_profile_changes` (escritura), `user_activity_logs` (escritura) | | **Endpoints** | `GET /partner/hotels/{prop_id}/edit` — Formulario de edición HTML.<br>`PUT /api/management/properties/{prop_id}/profile` — API de actualización.<br>`GET /api/management/properties/{prop_id}/edit` — API con datos actuales. |
---

## 6.14 CU-O13: Consultar Historial de Cambios de Propiedad

| Elemento | Detalle | |----------|---------| | **Código** | CU-O13 | | **Nombre** | Consultar historial de cambios de propiedad | | **Objetivo** | Permitir que el auditor de datos o el hotel partner consulte el historial completo de cambios realizados sobre el perfil de una propiedad, incluyendo qué campo cambió, valor anterior, valor nuevo, usuario responsable y fecha | | **Actor Principal** | Auditor de Datos, Hotel partner | | **Actores Secundarios** | Sistema | | **Disparador** | El usuario necesita verificar quién realizó un cambio específico en el perfil de un hotel |    | **Reglas de Negocio** | **RN-O13-01:** Todos los cambios críticos de perfil son registrados en `hotel_profile_changes`.<br>**RN-O13-02:** El historial es de solo lectura y no puede modificarse ni eliminarse. |    | **Colecciones MongoDB** | `hotel_profile_changes` (lectura) | | **Endpoints** | `GET /api/management/properties/{prop_id}/profile` — Incluye historial.<br>Auditoría general: `GET /api/audit/activity`. |
---

## 6.15 CU-O14: Crear Tipo de Habitación

| Elemento | Detalle | |----------|---------| | **Código** | CU-O14 | | **Nombre** | Crear tipo de habitación | | **Objetivo** | Permitir que el hotel partner defina los tipos de habitación de su propiedad (estándar, deluxe, suite, etc.) especificando nombre, capacidad, descripción y comodidades incluidas | | **Actor Principal** | Hotel partner | | **Actores Secundarios** | Sistema | | **Disparador** | El hotel partner necesita configurar los tipos de habitación que ofrece su propiedad |   | **Reglas de Negocio** | **RN-O14-01:** El nombre del tipo de habitación debe ser único por propiedad.<br>**RN-O14-02:** La capacidad máxima de adultos no puede exceder 10.<br>**RN-O14-03:** La cantidad de habitaciones físicas debe ser ≥ 1. |    | **Colecciones MongoDB** | `room_types` (escritura), `hotel_rooms` (escritura) | | **Endpoints** | `GET /partner/hotels/{prop_id}/rooms/new` — Formulario HTML.<br>`POST /partner/hotels/{prop_id}/rooms/new` — Crear desde formulario.<br>`POST /api/management/rooms` — Crear vía API. |
---

## 6.16 CU-O15: Actualizar Inventario por Fecha

| Elemento | Detalle | |----------|---------| | **Código** | CU-O15 | | **Nombre** | Actualizar inventario por fecha | | **Objetivo** | Permitir que el gerente de hotel actualice el inventario diario de habitaciones disponible por fecha y tipo de habitación, con control de concurrencia mediante optimistic locking | | **Actor Principal** | Gerente de hotel | | **Actores Secundarios** | Sistema | | **Disparador** | El gerente necesita ajustar la cantidad de habitaciones disponibles para una fecha específica |    | **Reglas de Negocio** | **RN-O15-01:** El inventario disponible no puede exceder el inventario total.<br>**RN-O15-02:** El inventario disponible no puede ser negativo.<br>**RN-O15-03:** El inventario bloqueado + reservado no puede exceder el inventario total.<br>**RN-O15-04:** El control de concurrencia usa optimistic locking con campo `version`. |    | **Colecciones MongoDB** | `room_inventory_calendar` (actualización/creación) | | **Endpoints** | `GET /partner/hotels/{prop_id}/inventory` — Vista de inventario HTML.<br>`POST /partner/hotels/{prop_id}/inventory` — Actualizar desde formulario.<br>`POST /api/management/availability` — Actualizar vía API. |
---

## 6.17 CU-O16: Registrar Bloqueo de Disponibilidad

| Elemento | Detalle | |----------|---------| | **Código** | CU-O16 | | **Nombre** | Registrar bloqueo de disponibilidad | | **Objetivo** | Permitir que el gerente de hotel bloquee rangos de fecha completos para ciertos tipos de habitación (mantenimiento, temporada baja, eventos privados), impidiendo reservas en esas fechas | | **Actor Principal** | Gerente de hotel | | **Actores Secundarios** | Sistema | | **Disparador** | El gerente necesita bloquear disponibilidad para un rango de fechas por mantenimiento o cierre temporal |   | **Reglas de Negocio** | **RN-O16-01:** Un bloqueo impide que se realicen nuevas reservas en esas fechas.<br>**RN-O16-02:** Las reservas existentes en el rango de fechas no se ven afectadas.<br>**RN-O16-03:** Un bloqueo puede ser parcial (solo algunos tipos de habitación) o total (toda la propiedad). |    | **Colecciones MongoDB** | `blackout_dates` (escritura), `room_inventory_calendar` (actualización), `room_availability_blocks` (escritura) | | **Endpoints** | `POST /partner/hotels/{prop_id}/blackout-dates` — Crear bloqueo desde HTML.<br>`POST /api/management/availability/blackouts` — Crear bloqueo vía API. |
---

## 6.18 CU-O17: Crear Plan Tarifario

| Elemento | Detalle | |----------|---------| | **Código** | CU-O17 | | **Nombre** | Crear plan tarifario | | **Objetivo** | Permitir que el revenue manager cree planes tarifarios (tarifa estándar, tarifa corporativa, tarifa de fin de semana, tarifa no reembolsable, etc.) con reglas de precio base, restricciones de estadía mínima y condiciones de cancelación | | **Actor Principal** | Revenue manager | | **Actores Secundarios** | Sistema | | **Disparador** | El revenue manager necesita definir un nuevo plan de precios para los tipos de habitación de una propiedad |   | **Reglas de Negocio** | **RN-O17-01:** El nombre del plan tarifario debe ser único por propiedad.<br>**RN-O17-02:** El precio base por noche debe ser mayor que 0.<br>**RN-O17-03:** Un plan tarifario puede asociarse a uno o varios tipos de habitación.<br>**RN-O17-04:** Las reglas de tarifa (rate_rules) definen variaciones sobre el precio base. |    | **Colecciones MongoDB** | `rate_plans` (escritura), `rate_rules` (lectura), `user_activity_logs` (escritura) | | **Endpoints** | `GET /revenue/rate-plans/new` — Formulario HTML.<br>`POST /revenue/rate-plans/new` — Crear desde HTML.<br>`POST /api/management/rates/plans` — Crear vía API. |
---

## 6.19 CU-O18: Configurar Tarifa por Fecha

| Elemento | Detalle | |----------|---------| | **Código** | CU-O18 | | **Nombre** | Configurar tarifa por fecha | | **Objetivo** | Permitir que el revenue manager configure precios específicos por fecha y plan tarifario en el calendario de tarifas, aplicando precios dinámicos según temporada, demanda o eventos especiales | | **Actor Principal** | Revenue manager | | **Actores Secundarios** | Sistema | | **Disparador** | El revenue manager necesita ajustar el precio de un plan tarifario para una fecha o rango de fechas específico |   | **Reglas de Negocio** | **RN-O18-01:** El precio por noche debe ser mayor que 0.<br>**RN-O18-02:** Un precio configurado en el calendario sobreescribe el precio base del plan para esa fecha.<br>**RN-O18-03:** Se pueden configurar precios diferentes por tipo de habitación y plan tarifario para la misma fecha. |    | **Colecciones MongoDB** | `hotel_rate_calendar` (actualización/creación) | | **Endpoints** | `GET /revenue/hotel/{prop_id}/rates` — Calendario HTML.<br>`POST /revenue/hotel/{prop_id}/rates` — Guardar desde HTML.<br>`POST /api/management/rates/calendar` — Guardar vía API. |
---

## 6.20 CU-O19: Crear Promoción y Cupón

| Elemento | Detalle | |----------|---------| | **Código** | CU-O19 | | **Nombre** | Crear promoción y cupón | | **Objetivo** | Permitir que marketing o revenue manager cree campañas promocionales con descuento porcentual sobre las tarifas, generando códigos de cupón asociados para incentivar reservas en períodos de baja demanda | | **Actor Principal** | Marketing hotelero, Revenue manager | | **Actores Secundarios** | Sistema | | **Disparador** | El equipo de marketing desea lanzar una promoción por temporada baja con código de descuento |   | **Reglas de Negocio** | **RN-O19-01:** Un descuento porcentual no puede exceder 100%.<br>**RN-O19-02:** Un código de cupón puede tener un límite de usos máximos (si no se especifica, es ilimitado dentro de la vigencia).<br>**RN-O19-03:** Una promoción puede aplicarse a uno o varios hoteles y tipos de habitación.<br>**RN-O19-04:** El código de cupón debe ser único en el sistema. |    | **Colecciones MongoDB** | `promotion_campaigns` (escritura), `coupon_codes` (escritura) | | **Endpoints** | `GET /revenue/promotions/new` — Formulario HTML.<br>`POST /revenue/promotions/new` — Crear desde HTML.<br>`POST /api/management/rates/plans` — Las promociones se gestionan desde revenue module. |
---

## 6.21 CU-O20: Editar Política Hotelera

| Elemento | Detalle | |----------|---------| | **Código** | CU-O20 | | **Nombre** | Editar política hotelera | | **Objetivo** | Permitir que el hotel partner configure las políticas de la propiedad: horarios de check-in/check-out, política de cancelación, admisión de mascotas, política de niños y condiciones de uso | | **Actor Principal** | Hotel partner | | **Actores Secundarios** | Sistema | | **Disparador** | El hotel partner necesita actualizar las políticas operativas de su propiedad |   | **Reglas de Negocio** | **RN-O20-01:** El horario de check-out debe ser posterior al horario de check-in.<br>**RN-O20-02:** La política de cancelación debe especificar días de anticipación y porcentaje de cargo.<br>**RN-O20-03:** Si se permite mascotas, debe especificarse el peso máximo y costo adicional (si aplica). |    | **Colecciones MongoDB** | `hotel_policies` (actualización), `hotel_content_changes` (escritura) | | **Endpoints** | `GET /partner/hotels/{prop_id}/policies` — Formulario HTML.<br>`POST /partner/hotels/{prop_id}/policies` — Guardar desde HTML.<br>`PUT /api/management/policies` — Guardar vía API. |
---

## 6.22 CU-O21: Actualizar Amenities, Imágenes y Contenido

| Elemento | Detalle | |----------|---------| | **Código** | CU-O21 | | **Nombre** | Actualizar amenities, imágenes y contenido | | **Objetivo** | Permitir que el marketing hotelero administre el contenido comercial de la propiedad: galería de imágenes, lista de amenities (WiFi, piscina, gimnasio, restaurante), descripciones extendidas y highlights para mejorar la presentación ante clientes | | **Actor Principal** | Marketing hotelero | | **Actores Secundarios** | Sistema | | **Disparador** | El equipo de marketing necesita actualizar las imágenes o amenities de una propiedad para mejorar su atractivo comercial |   | **Reglas de Negocio** | **RN-O21-01:** Las imágenes deben estar en formato JPEG o PNG, tamaño máximo 5MB cada una.<br>**RN-O21-02:** Las amenities se seleccionan de un catálogo predefinido (`system_catalogs`).<br>**RN-O21-03:** Cada propiedad debe tener al menos una imagen principal (portada). |    | **Colecciones MongoDB** | `hotel_content_pages` (actualización), `hotel_images` (actualización), `hotel_content_changes` (escritura), `system_catalogs` (lectura) | | **Endpoints** | `GET /partner/hotels/{prop_id}/content` — Gestor de contenido HTML.<br>`POST /partner/hotels/{prop_id}/content/edit` — Guardar contenido.<br>`POST /partner/hotels/{prop_id}/images` — Subir imagen.<br>`DELETE /api/management/properties/{prop_id}/images` — Eliminar imagen.<br>`PUT /api/management/properties/{prop_id}/content` — Guardar vía API.<br>`PUT /api/management/amenities` — Guardar amenities vía API. |
---

## 6.23 CU-O22: Registrar Reseña de Estancia

| Elemento | Detalle | |----------|---------| | **Código** | CU-O22 | | **Nombre** | Registrar reseña de estancia | | **Objetivo** | Permitir que el cliente registre una reseña después de su estancia, con calificación general (1-5), calificaciones por categoría (limpieza, ubicación, servicio, confort), comentario escrito y fotos opcionales, con dual-write a la fact table analítica | | **Actor Principal** | Cliente | | **Actores Secundarios** | Sistema (moderación automática, dual-write a fact_reviews) | | **Disparador** | El cliente ha completado su estancia (check-out realizado) y desea dejar una reseña |    | **Reglas de Negocio** | **RN-O22-01:** Solo clientes con reserva completada (checked_out) pueden reseñar.<br>**RN-O22-02:** Una reseña por reserva (no se pueden reseñar múltiples veces la misma estancia).<br>**RN-O22-03:** Las reseñas se crean en estado "pending" y deben ser moderadas (CU-O23) antes de ser públicas.<br>**RN-O22-04:** El dual-write a `fact_reviews` garantiza que las métricas de satisfacción estén disponibles para reportes. |     | **Colecciones MongoDB** | `reviews` (escritura), `fact_reviews` (escritura) | | **Endpoints** | `POST /api/reviews/` — Crear reseña vía API. |
---

## 6.24 CU-O23: Moderar y Responder Reseña

| Elemento | Detalle | |----------|---------| | **Código** | CU-O23 | | **Nombre** | Moderar y responder reseña | | **Objetivo** | Permitir que marketing hotelero o super admin modere las reseñas recibidas (aprobar o rechazar), y responder a las reseñas aprobadas para gestionar la reputación online del hotel | | **Actor Principal** | Marketing hotelero, Super Admin | | **Actores Secundarios** | Sistema | | **Disparador** | Hay reseñas pendientes de moderación o se necesita responder a una reseña existente |    | **Reglas de Negocio** | **RN-O23-01:** Las reseñas deben ser moderadas antes de hacerse públicas.<br>**RN-O23-02:** Una reseña aprobada no puede eliminarse (solo desactivarse como "hidden").<br>**RN-O23-03:** Una reseña rechazada no es visible para el público ni para el cliente que la escribió.<br>**RN-O23-04:** La respuesta a una reseña queda visible públicamente junto con la reseña. |    | **Colecciones MongoDB** | `reviews` (actualización), `fact_reviews` (actualización) | | **Endpoints** | `PATCH /api/reviews/{review_id}/moderate` — Moderar reseña.<br>`PATCH /api/reviews/{review_id}/respond` — Responder reseña.<br>`GET /api/reviews/` — Listar reseñas con filtros. |
---

## 6.25 CU-O24: Generar Comprobante o Factura de Reserva

| Elemento | Detalle | |----------|---------| | **Código** | CU-O24 | | **Nombre** | Generar comprobante o factura de reserva | | **Objetivo** | Generar un comprobante o factura asociada a una reserva confirmada o finalizada, con desglose de cargos (habitación, impuestos, cargos adicionales), estado de pago y número de factura único, con dual-write a fact_invoices | | **Actor Principal** | Sistema (generación automática), Recepcionista (generación manual) | | **Actores Secundarios** | Sistema | | **Disparador** | La reserva cambia a estado "checked_out" (generación automática) o el recepcionista solicita generar una factura |   | **Reglas de Negocio** | **RN-O24-01:** Una reserva puede tener una o más facturas (si hay rectificaciones).<br>**RN-O24-02:** El número de factura debe ser único en el sistema.<br>**RN-O24-03:** La factura incluye: subtotal (habitación), impuestos, cargos adicionales, total.<br>**RN-O24-04:** El dual-write a `fact_invoices` garantiza disponibilidad para reportes financieros. |     | **Colecciones MongoDB** | `reservation_invoices` (escritura), `fact_invoices` (escritura), `booking_orders` (lectura) | | **Endpoints** | `POST /api/billing/invoices` — Crear factura.<br>`GET /api/billing/invoices` — Listar facturas.<br>`GET /api/billing/invoices/{invoice_id}` — Detalle de factura. |
---

## 6.26 CU-O25: Registrar Pago Asociado a Reserva

| Elemento | Detalle | |----------|---------| | **Código** | CU-O25 | | **Nombre** | Registrar pago asociado a reserva | | **Objetivo** | Registrar un pago asociado a una factura de reserva, especificando método de pago (efectivo, tarjeta, transferencia), monto, fecha y referencia externa, con dual-write a fact_payments | | **Actor Principal** | Recepcionista | | **Actores Secundarios** | Sistema | | **Disparador** | El huésped realiza el pago de su factura al momento del check-out o durante su estancia |    | **Reglas de Negocio** | **RN-O25-01:** El monto del pago debe ser mayor que 0.<br>**RN-O25-02:** La suma de pagos no puede exceder el total de la factura.<br>**RN-O25-03:** Los pagos son simulados (no hay integración real con pasarela de pagos).<br>**RN-O25-04:** El dual-write a `fact_payments` garantiza disponibilidad para reportes financieros. |     | **Colecciones MongoDB** | `reservation_payments` (escritura), `fact_payments` (escritura), `reservation_invoices` (actualización) | | **Endpoints** | `POST /api/billing/payments` — Registrar pago.<br>`POST /api/billing/payments/{payment_id}/refund` — Reembolsar pago.<br>`GET /api/billing/payments` — Listar pagos.<br>`GET /api/billing/payments/{payment_id}` — Detalle de pago. |
---

## 6.27 CU-O26: Consultar Reportes de Revenue y Mercado

| Elemento | Detalle | |----------|---------| | **Código** | CU-O26 | | **Nombre** | Consultar reportes de revenue y mercado | | **Objetivo** | Permitir que gerentes y revenue managers consulten dashboards y reportes con métricas clave de negocio: eventos totales, reservas, conversión, revenue bruto, precio promedio, top hoteles, top destinos, top países visitantes | | **Actor Principal** | Gerente de hotel, Revenue manager | | **Actores Secundarios** | Sistema (cálculo de agregaciones desde fact tables) | | **Disparador** | El usuario necesita visualizar indicadores de rendimiento para tomar decisiones |    | **Reglas de Negocio** | **RN-O26-01:** La tasa de conversión se calcula como reservas / eventos totales × 100.<br>**RN-O26-02:** El revenue bruto se calcula como suma de price_usd donde reserva_bool = true.<br>**RN-O26-03:** El precio promedio se calcula como AVG(price_usd) sobre todos los eventos. |    | **Colecciones MongoDB** | `fact_hotel_reservations`, `dim_hotels`, `dim_destinations`, `dim_visitor_countries`, `dim_sites`, `dim_dates` | | **Endpoints** | `GET /analytics/revenue` — Reporte de revenue HTML.<br>`GET /analytics/conversion` — Reporte de conversión HTML.<br>`GET /analytics/promotions` — Reporte de promociones HTML.<br>`GET /analytics/visitor-markets` — Reporte de mercados HTML.<br>`GET /api/management/reports` — API de reportes. |
---

## 6.28 CU-O27: Consultar Reporte de Calidad y Registros Rechazados

| Elemento | Detalle | |----------|---------| | **Código** | CU-O27 | | **Nombre** | Consultar reporte de calidad y registros rechazados | | **Objetivo** | Permitir que el auditor de datos consulte los reportes de calidad de cada ejecución ETL, incluyendo total de registros procesados, aceptados, rechazados, completitud de datos y detalle de cada registro rechazado con la razón exacta | | **Actor Principal** | Auditor de Datos | | **Actores Secundarios** | Sistema | | **Disparador** | El auditor necesita verificar la calidad de la última ejecución ETL o investigar registros rechazados |    | **Reglas de Negocio** | **RN-O27-01:** Cada ejecución ETL debe producir un reporte de calidad en `data_quality_reports` y en `data/reports/` (JSON filesystem).<br>**RN-O27-02:** Ningún registro debe ser descartado silenciosamente — todos los rechazos van a `rejected_records` con la razón exacta. |    | **Colecciones MongoDB** | `data_quality_reports` (lectura), `etl_executions` (lectura), `rejected_records` (lectura), `data/reports/*.json` (filesystem) | | **Endpoints** | `GET /quality` — Página de calidad HTML.<br>`GET /api/etl-status/reports` — API de reportes.<br>`GET /api/etl-status/execution` — API de estado de ejecución. |
---

## 6.29 CU-O28: Administrar Cuenta, Sesión y Cierre Seguro

| Elemento | Detalle | |----------|---------| | **Código** | CU-O28 | | **Nombre** | Administrar cuenta, sesión y cierre seguro | | **Objetivo** | Permitir que cualquier usuario autenticado cierre su sesión de forma segura (logout) invalidando el token en servidor, consultar el estado de su sesión actual, y gestionar su cuenta | | **Actor Principal** | Todos los usuarios autenticados | | **Actores Secundarios** | Sistema | | **Disparador** | El usuario desea cerrar su sesión o verificar su estado de autenticación |    | **Reglas de Negocio** | **RN-O28-01:** El logout invalida la sesión en el servidor (no solo borra la cookie del lado cliente).<br>**RN-O28-02:** Una sesión expirada (TTL de 8 horas) se limpia automáticamente por MongoDB TTL index.<br>**RN-O28-03:** Si un usuario inicia sesión con una sesión previa activa, la sesión anterior se invalida automáticamente. |     | **Colecciones MongoDB** | `user_sessions` (eliminación), `user_activity_logs` (escritura) | | **Endpoints** | `GET /auth/logout` — Logout web (HTML).<br>`GET /api/auth/me` — Consultar sesión actual (JSON).<br>`GET /auth/me` — Homepage según rol. |
---

## 6.30 CU-O29: Cambiar Contraseña y Actualizar Perfil de Usuario

| Elemento | Detalle | |----------|---------| | **Código** | CU-O29 | | **Nombre** | Cambiar contraseña y actualizar perfil de usuario | | **Objetivo** | Permitir que cualquier usuario autenticado cambie su contraseña (verificando la actual), actualice su perfil (display_name, email, teléfono, preferencias), y suba un avatar, registrando toda modificación en auditoría | | **Actor Principal** | Todos los usuarios autenticados | | **Actores Secundarios** | Sistema | | **Disparador** | El usuario desea cambiar su contraseña por seguridad, o actualizar sus datos personales |  |  |   | **Reglas de Negocio** | **RN-O29-01:** La nueva contraseña debe tener al menos 8 caracteres.<br>**RN-O29-02:** La nueva contraseña no puede ser igual a la actual.<br>**RN-O29-03:** El cambio de contraseña invalida todas las sesiones activas (obliga a re-login).<br>**RN-O29-04:** El email debe ser único en el sistema.<br>**RN-O29-05:** Las contraseñas siempre se almacenan con bcrypt, nunca en texto plano. |     | **Colecciones MongoDB** | `users` (actualización: password_hash, profile), `user_sessions` (eliminación), `user_activity_logs` (escritura) | | **Endpoints** | `PUT /api/settings/password` — Cambiar contraseña.<br>`GET /api/account/profile` — Obtener perfil.<br>`PUT /api/account/profile` — Actualizar perfil.<br>`POST /api/account/profile/avatar` — Subir avatar.<br>`PUT /api/settings` — Actualizar configuración. |
---

## 6.31 CU-O30: Consultar Estado Actual de Habitaciones

| Elemento | Detalle | |----------|---------| | **Código** | CU-O30 | | **Nombre** | Consultar Estado Actual de Habitaciones | | **Objetivo** | Permitir que el recepcionista o gerente consulte el estado operativo de todas las habitaciones del hotel: ocupadas, disponibles, en limpieza, en mantenimiento, bloqueadas, con check-in/out pendiente | | **Actor Principal** | Recepcionista / Gerente de hotel | | **Actores Secundarios** | Sistema (consulta a MongoDB) | | **Disparador** | El recepcionista accede al panel de estado de habitaciones |    | **Reglas de Negocio** | **RN-O30-01:** El estado de una habitación se determina por el registro más reciente en `room_status_log`. **RN-O30-02:** Una habitación con booking activo (checked_in) se marca como "occupied" automáticamente aunque no tenga registro en room_status_log. |     | **Colecciones MongoDB** | `hotel_rooms` (lectura), `room_status_log` (lectura), `room_inventory_calendar` (lectura), `booking_orders` (lectura) | | **Endpoints** | `GET /api/housekeeping/rooms/status?prop_id=X` - API JSON. `GET /housekeeping/rooms/status` - Página HTML. |
---

## 6.32 CU-O31: Asignar Tipo de Habitación a Habitación Individual

| Elemento | Detalle | |----------|---------| | **Código** | CU-O31 | | **Nombre** | Asignar tipo de habitación a habitación individual | | **Objetivo** | Permitir que el recepcionista o gerente asigne o cambie el tipo de habitación (room_type_id) a una habitación física individual, permitiendo reclasificar habitaciones según necesidad operativa | | **Actor Principal** | Recepcionista / Gerente de hotel | | **Actores Secundarios** | Sistema (actualización de hotel_rooms) | | **Disparador** | El usuario selecciona una habitación individual desde la matriz de estado y hace clic en "Asignar tipo" |    | **Reglas de Negocio** | **RN-O31-01:** Solo se puede cambiar el tipo si la habitación está en estado "available", "cleaning" o "maintenance". **RN-O31-02:** El cambio se registra en `room_status_log` para trazabilidad. |     | **Colecciones MongoDB** | `hotel_rooms` (lectura/escritura), `room_types` (lectura), `room_status_log` (escritura) | | **Endpoints** | `PUT /api/housekeeping/rooms/{room_id}/assign-type` - API JSON |
---

## 6.33 CU-O32: Consultar Disponibilidad por Habitación Individual

| Elemento | Detalle | |----------|---------| | **Código** | CU-O32 | | **Nombre** | Consultar disponibilidad por habitación individual | | **Objetivo** | Permitir que el recepcionista consulte la disponibilidad de una habitación específica en un rango de fechas, viendo el calendario de ocupación, bloqueos y mantenimiento programado para esa unidad | | **Actor Principal** | Recepcionista / Gerente de hotel | | **Actores Secundarios** | Sistema (consulta calendarios) | | **Disparador** | El usuario selecciona una habitación desde la matriz de estado y hace clic en "Ver disponibilidad" |    | **Reglas de Negocio** | **RN-O32-01:** Una habitación se considera disponible si no tiene booking en estado confirmed/checked_in para esa noche. **RN-O32-02:** Los bloqueos administrativos tienen prioridad sobre la disponibilidad. |     | **Colecciones MongoDB** | `hotel_rooms` (lectura), `room_inventory_calendar` (lectura), `booking_orders` (lectura), `room_availability_blocks` (lectura) | | **Endpoints** | `GET /api/housekeeping/rooms/{room_id}/availability` - API JSON |
---

## 6.34 CU-O33: Gestionar Amenities por Tipo de Habitación

| Elemento | Detalle | |----------|---------| | **Código** | CU-O33 | | **Nombre** | Gestionar amenities por tipo de habitación | | **Objetivo** | Permitir que el hotel partner o marketing configure los amenities específicos por tipo de habitación (no solo a nivel de hotel), como TV, aire acondicionado, minibar, vista al mar, etc. | | **Actor Principal** | Hotel partner / Marketing hotelero | | **Actores Secundarios** | Sistema (actualización de room_types) | | **Disparador** | El usuario navega a la sección de tipos de habitación y selecciona "Editar amenities" |    | **Reglas de Negocio** | **RN-O33-01:** Los amenities de tipo de habitación son independientes de los amenities del hotel. **RN-O33-02:** Máximo 20 amenities por tipo de habitación. |     | **Colecciones MongoDB** | `room_types` (lectura/escritura), `hotel_edit_history` (escritura) | | **Endpoints** | `PUT /api/partner/room-types/{room_type_id}/amenities` - API JSON. `GET /api/partner/room-types/{room_type_id}/amenities` - Consultar amenities actuales. |
---

## 6.35 CU-O34: Registrar Cargos Adicionales a Reserva

| Elemento | Detalle | |----------|---------| | **Código** | CU-O34 | | **Nombre** | Registrar cargos adicionales a reserva | | **Objetivo** | Permitir que el recepcionista registre cargos adicionales asociados a una reserva activa (room service, consumo de minibar, daños, servicios extra, estacionamiento) para que se reflejen en la factura final | | **Actor Principal** | Recepcionista / Gerente de hotel | | **Actores Secundarios** | Sistema (creación de cargo, actualización de total) | | **Disparador** | El usuario identifica un cargo adicional durante la estancia del huésped |    | **Reglas de Negocio** | **RN-O34-01:** Los cargos adicionales se suman al total de la factura final. **RN-O34-02:** Tipos de cargo predefinidos: room_service, minibar, damages, parking, laundry, other. **RN-O34-03:** El monto debe ser mayor a cero. |     | **Colecciones MongoDB** | `additional_charges` (escritura), `booking_orders` (lectura/escritura) | | **Endpoints** | `POST /api/billing/additional-charges` - Crear cargo. `GET /api/billing/additional-charges/{booking_id}` - Listar cargos de una reserva. |
---

## 6.36 CU-O35: Editar Metadata de Destino

| Elemento | Detalle | |----------|---------| | **Código** | CU-O35 | | **Nombre** | Editar metadata de destino | | **Objetivo** | Permitir que el auditor de datos edite la metadata de un destino hotelero (nombre visible, coordenadas geográficas, país, ciudad, descripción) para corregir nombres genéricos o numéricos provenientes del dataset original | | **Actor Principal** | Auditor de Datos | | **Actores Secundarios** | Sistema (actualización en MongoDB) | | **Disparador** | El usuario identifica un destino con nombre genérico o numérico (ej. "Destination 8250") y necesita asignarle un nombre real |    | **Reglas de Negocio** | **RN-O35-01:** El nombre visible del destino no puede estar vacío. **RN-O35-02:** Las coordenadas deben ser válidas (lat: -90 a 90, lng: -180 a 180). **RN-O35-03:** Se conserva el ID original del destino para mantener trazabilidad con el dataset. |     | **Colecciones MongoDB** | `dim_destinations` (lectura/escritura), `locations` (lectura/escritura), `hotel_edit_history` (escritura) | | **Endpoints** | `GET /api/admin/destinations` - Listar destinos. `PUT /api/admin/destinations/{destination_id}` - Actualizar metadata. `GET /api/admin/destinations/{destination_id}` - Ver detalle. |
---

## 6.37 CU-O36: Editar Nombre Visible de Hotel (Manual Override)

| Elemento | Detalle | |----------|---------| | **Código** | CU-O36 | | **Nombre** | Editar nombre visible de hotel (Manual Override) | | **Objetivo** | Permitir que el auditor de datos o marketing edite el nombre comercial visible de un hotel cuyo nombre original en el dataset es un ID numérico (ej. "Property 14239"), asignando un nombre real para mejorar la experiencia de búsqueda | | **Actor Principal** | Auditor de Datos / Marketing hotelero | | **Actores Secundarios** | Sistema (actualización de dim_hotels y hotels) | | **Disparador** | El usuario identifica un hotel con nombre numérico genérico en el catálogo |    | **Reglas de Negocio** | **RN-O36-01:** El nombre override se usa en todas las interfaces visibles (búsqueda, detalle, factura). **RN-O36-02:** El nombre original siempre se conserva en un campo `original_name` para referencia. **RN-O36-03:** Solo data_auditor y marketing pueden modificar este campo. |     | **Colecciones MongoDB** | `dim_hotels` (lectura/escritura), `hotels` (lectura/escritura), `hotel_edit_history` (escritura) | | **Endpoints** | `PUT /api/admin/hotels/{prop_id}/override-name` - Actualizar nombre. `GET /api/admin/hotels/{prop_id}` - Ver datos actuales. |
---

## 6.38 CU-O37: Visualizar Mapa Mundial de Destinos con Hoteles

| Elemento | Detalle | |----------|---------| | **Código** | CU-O37 | | **Nombre** | Visualizar mapa mundial de destinos con hoteles | | **Objetivo** | Permitir que el usuario visualice un mapa mundial interactivo (Leaflet.js/OpenLayers) con marcadores de destinos turísticos y hoteles, donde los hoteles se muestran con colores según su estado (disponibilidad, precio, rating) | | **Actor Principal** | Auditor de Datos / Marketing hotelero | | **Actores Secundarios** | Sistema (carga de datos geoespaciales desde MongoDB), Leaflet.js (renderizado de mapa, requiere conexión a internet para tiles) | | **Disparador** | El usuario navega a la sección "Mapa Mundial" desde el panel de administración o marketing |    | **Reglas de Negocio** | **RN-O37-01:** Los destinos sin coordenadas no se muestran en el mapa. **RN-O37-02:** Los colores de hoteles siguen la escala de precios configurable. **RN-O37-03:** Máximo 500 marcadores visibles simultáneamente (clustering automático). |     | **Colecciones MongoDB** | `dim_destinations` (lectura), `dim_hotels` (lectura), `hotels` (lectura) | | **Endpoints** | `GET /map/world` - Página del mapa HTML. `GET /api/map/destinations?format=geojson` - Datos geoespaciales formato GeoJSON. `GET /api/map/hotels?lat=X&lng=Y&radius=Z` - Hoteles por radio. |
---

## 6.39 CU-O38: Seleccionar Ubicación de Destino en Mapa Interactivo

| Elemento | Detalle | |----------|---------| | **Código** | CU-O38 | | **Nombre** | Seleccionar ubicación de destino en mapa interactivo | | **Objetivo** | Permitir que el auditor de datos seleccione la ubicación geográfica de un destino haciendo clic en un mapa mundial interactivo, capturando automáticamente las coordenadas (lat, lng), nombre del país y ciudad desde las coordenadas seleccionadas | | **Actor Principal** | Auditor de Datos | | **Actores Secundarios** | Sistema (reverse geocoding opcional), Leaflet.js (mapa interactivo) | | **Disparador** | El usuario está editando la metadata de un destino (CU-O35) y hace clic en "Seleccionar en mapa" |    | **Reglas de Negocio** | **RN-O38-01:** Las coordenadas se capturan con precisión de 6 decimales. **RN-O38-02:** El reverse geocoding es una funcionalidad de ayuda, no obligatoria. **RN-O38-03:** El usuario puede ajustar manualmente las coordenadas después de la selección. |     | **Colecciones MongoDB** | Ninguna directamente (usa datos en memoria, se persisten al guardar en CU-O35) | | **Endpoints** | `GET /api/map/select-location` - Página/modal del selector de mapa. `GET /api/map/reverse-geocode?lat=X&lng=Y` - Reverse geocoding (proxy a Nominatim). |
---

## 6.40 CU-O39: Gestionar Limpieza y Rotación de Habitaciones

| Elemento | Detalle | |----------|---------| | **Código** | CU-O39 | | **Nombre** | Gestionar limpieza y rotación de habitaciones | | **Objetivo** | Permitir que el recepcionista o gerente gestione el flujo de limpieza de habitaciones: marcar habitación para limpiar después del check-out, asignar tarea de limpieza a personal, registrar inicio/fin de limpieza, y actualizar estado a disponible | | **Actor Principal** | Recepcionista / Gerente de hotel | | **Actores Secundarios** | Sistema (creación de tareas, actualización de estado) | | **Disparador** | Un huésped completa el check-out (CU-O11) o el recepcionista identifica una habitación que necesita limpieza |    | **Reglas de Negocio** | **RN-O39-01:** El tiempo de rotación (check-out a disponible) se registra para métricas de eficiencia. **RN-O39-02:** Una habitación no puede ser asignada hasta que esté "available". **RN-O39-03:** Estados: available, cleaning_needed, cleaning_in_progress, occupied, maintenance, blocked. |     | **Colecciones MongoDB** | `room_status_log` (lectura/escritura), `housekeeping_tasks` (lectura/escritura), `hotel_rooms` (lectura) | | **Endpoints** | `POST /api/housekeeping/cleaning/assign` - Asignar limpieza. `POST /api/housekeeping/cleaning/{room_id}/start` - Iniciar limpieza. `POST /api/housekeeping/cleaning/{room_id}/complete` - Completar limpieza. `GET /api/housekeeping/cleaning/pending` - Tareas pendientes. |
---

## 6.41 CU-O40: Gestionar Mantenimiento Preventivo de Habitaciones

| Elemento | Detalle | |----------|---------| | **Código** | CU-O40 | | **Nombre** | Gestionar mantenimiento preventivo de habitaciones | | **Objetivo** | Permitir que el gerente de hotel programe y registre mantenimiento preventivo de habitaciones e instalaciones, incluyendo fecha programada, tipo de mantenimiento, habitación afectada, estado de ejecución y observaciones | | **Actor Principal** | Gerente de hotel | | **Actores Secundarios** | Sistema (programación de mantenimiento) | | **Disparador** | El gerente identifica la necesidad de mantenimiento programado (preventivo) o correctivo (avería reportada) |    | **Reglas de Negocio** | **RN-O40-01:** Una habitación en mantenimiento no está disponible para reservas. **RN-O40-02:** El mantenimiento preventivo se programa con al menos 7 días de anticipación. **RN-O40-03:** Mantenimiento crítico (avería) se puede programar inmediato con prioridad "crítica". |     | **Colecciones MongoDB** | `maintenance_schedule` (lectura/escritura), `maintenance_tasks` (lectura/escritura), `hotel_rooms` (lectura/escritura), `room_status_log` (escritura) | | **Endpoints** | `POST /api/housekeeping/maintenance` - Crear mantenimiento. `GET /api/housekeeping/maintenance/schedule` - Calendario. `PUT /api/housekeeping/maintenance/{id}/status` - Actualizar estado. `GET /api/housekeeping/maintenance/history` - Historial. |
---

## 6.42 CU-T14: Gestionar Rotación y Limpieza de Habitaciones (Táctico)

| Elemento | Detalle | |----------|---------| | **Código** | CU-T14 | | **Nombre** | Gestionar rotación y limpieza de habitaciones | | **Nivel** | Táctico | | **Objetivo** | Optimizar el tiempo de rotación de habitaciones entre check-out y check-in, estableciendo métricas objetivo de eficiencia de limpieza, asignación de personal y reducción de tiempos muertos | | **Actor Principal** | Gerente de hotel | | **Disparador** | Reporte mensual de eficiencia de rotación muestra tiempos por encima del objetivo |   | **Reglas de Negocio** | RN-T14-01: El tiempo de rotación se mide desde check-out hasta disponible. RN-T14-02: El objetivo por defecto es 4 horas para hoteles urbanos, 6 horas para resorts. | | **Colecciones MongoDB** | `room_status_log`, `housekeeping_tasks`, `booking_orders` | | **Endpoints** | `GET /api/management/rotation-report` |
---

## 6.43 CU-T15: Programar Mantenimiento Preventivo Proactivo (Táctico)

| Elemento | Detalle | |----------|---------| | **Código** | CU-T15 | | **Nombre** | Programar mantenimiento preventivo proactivo | | **Nivel** | Táctico | | **Objetivo** | Establecer un plan de mantenimiento preventivo recurrente basado en histórico, estacionalidad y uso de habitaciones, minimizando interrupciones operativas | | **Actor Principal** | Gerente de hotel | | **Disparador** | Inicio de temporada baja o revisión trimestral de plan de mantenimiento |   | **Reglas de Negocio** | RN-T15-01: Mantenimiento eléctrico cada 6 meses. RN-T15-02: Mantenimiento HVAC cada 3 meses. RN-T15-03: Pintura general cada 12 meses. | | **Colecciones MongoDB** | `maintenance_schedule`, `maintenance_tasks`, `hotel_rooms` | | **Endpoints** | `POST /api/management/maintenance-plan` |
---

## 6.44 : Monitorear Eficiencia Operativa del Hotel ()

| Elemento | Detalle | |----------|---------| | **Código** | | | **Nombre** | Monitorear eficiencia operativa del hotel | | **Nivel** | | | **Objetivo** | Proporcionar a la gerencia general y super admin una visión consolidada de la eficiencia operativa del hotel: tiempo de rotación, cumplimiento de limpieza, cumplimiento de mantenimiento, ocupación real vs disponible, cargos adicionales por reserva | | **Actor Principal** | Gerente general / Super Admin | | **Disparador** | Necesidad de evaluar el rendimiento operativo del hotel a nivel  |   | **Reglas de Negocio** | RN-E09-01: Los KPIs se calculan con datos de los últimos 30 días por defecto. RN-E09-02: Tiempo de rotación objetivo: < 4 horas. RN-E09-03: Cumplimiento de limpieza objetivo: > 95%. | | **Colecciones MongoDB** | `room_status_log`, `housekeeping_tasks`, `maintenance_schedule`, `maintenance_tasks`, `additional_charges`, `booking_orders` | | **Endpoints** | `GET /api/management/efficiency-dashboard` |
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

## 7.30 CU-O30: Consultar Estado Actual de Habitaciones

```gherkin
Feature: Consulta de estado de habitaciones
  Como recepcionista o gerente de hotel
  Quiero consultar el estado operativo de todas las habitaciones del hotel en una matriz visual
  Para gestionar la asignación y conocer la disponibilidad en tiempo real

  Background:
    Given el usuario está autenticado con rol "recepcionista" o "hotel_manager"
    And el hotel tiene habitaciones configuradas en "hotel_rooms"

  Scenario: Consulta exitosa de matriz de estados
    When el usuario navega al panel de estado de habitaciones
    Then el sistema muestra una matriz visual con todas las habitaciones
    And cada habitación muestra su número, piso, tipo y estado con código de colores
    And los estados visibles incluyen: disponible (verde), ocupada (rojo), limpieza (amarillo), mantenimiento (gris), bloqueada (azul)

  Scenario: Hotel sin habitaciones configuradas
    Given el hotel no tiene habitaciones en "hotel_rooms"
    When el usuario navega al panel de estado
    Then el sistema muestra "No hay habitaciones configuradas para este hotel"

  Scenario: Acceso a hotel no asignado
    When el usuario intenta consultar un hotel al que no está asignado
    Then el sistema muestra error de acceso denegado
```

## 7.31 CU-O31: Asignar Tipo de Habitación

```gherkin
Feature: Asignación de tipo de habitación
  Como recepcionista o gerente
  Quiero asignar o cambiar el tipo de habitación a una habitación individual
  Para reclasificar habitaciones según necesidad operativa

  Background:
    Given el usuario está autenticado con rol "recepcionista" o "hotel_manager"
    And la habitación existe en "hotel_rooms"
    And existen tipos de habitación en "room_types"

  Scenario: Asignación exitosa de tipo de habitación
    When el usuario selecciona una habitación disponible
    And selecciona un nuevo tipo de habitación del selector
    And confirma el cambio
    Then el sistema actualiza "hotel_rooms.room_type_id"
    And el sistema registra el cambio en "room_status_log"
    And el sistema muestra "Tipo de habitación asignado exitosamente"

  Scenario: Intento de cambio en habitación ocupada
    Given la habitación está ocupada con un booking activo
    When el usuario intenta cambiar el tipo de habitación
    Then el sistema muestra "No se puede cambiar el tipo de una habitación ocupada"
    And el sistema no realiza el cambio
```

## 7.32 CU-O32: Consultar Disponibilidad por Habitación

```gherkin
Feature: Consulta de disponibilidad por habitación
  Como recepcionista
  Quiero consultar la disponibilidad de una habitación específica en un calendario
  Para conocer la ocupación futura y planificar asignaciones

  Background:
    Given el usuario está autenticado con rol "recepcionista"
    And la habitación existe en "hotel_rooms"

  Scenario: Consulta exitosa de calendario de disponibilidad
    When el usuario selecciona una habitación y hace clic en "Ver disponibilidad"
    Then el sistema muestra un calendario de 90 días
    And cada noche se muestra con color: verde (disponible), rojo (ocupada), gris (mantenimiento)
    And el sistema muestra las reservas activas en el período

  Scenario: Habitación sin configuración de inventario
    When el usuario consulta una habitación sin registros en "room_inventory_calendar"
    Then el sistema muestra "Sin configuración de inventario para esta habitación"
```

## 7.33 CU-O33: Gestionar Amenities por Tipo de Habitación

```gherkin
Feature: Gestión de amenities por tipo de habitación
  Como hotel partner o marketing
  Quiero configurar los amenities específicos por tipo de habitación
  Para que los clientes vean el equipamiento exacto de cada categoría

  Background:
    Given el usuario está autenticado con rol "hotel_partner" o "marketing"
    And el tipo de habitación existe en "room_types"

  Scenario: Agregar amenities exitosamente
    When el usuario selecciona un tipo de habitación
    And agrega los amenities "WiFi", "TV", "A/C" y "Minibar"
    And guarda los cambios
    Then el sistema actualiza "room_types.amenities" con la nueva lista
    And el sistema registra el cambio en "hotel_edit_history"
    And el sistema muestra "Amenities actualizados exitosamente"

  Scenario: Agregar amenity personalizado
    When el usuario escribe un amenity personalizado "Vista al jardín"
    Then el sistema permite agregarlo como amenity personalizado
    And el sistema lo muestra en la lista de amenities del tipo de habitación
```

## 7.34 CU-O34: Registrar Cargos Adicionales

```gherkin
Feature: Registro de cargos adicionales a reserva
  Como recepcionista
  Quiero registrar cargos adicionales asociados a una reserva activa
  Para que se reflejen en la factura final del huésped

  Background:
    Given el recepcionista está autenticado con rol "recepcionista"
    And existe una reserva en estado "confirmed" o "checked_in"

  Scenario: Registro exitoso de cargo adicional
    When el recepcionista busca la reserva por booking_id
    And selecciona tipo de cargo "room_service"
    And ingresa descripción "Cena habitación" y monto $450
    And confirma el cargo
    Then el sistema crea el registro en "additional_charges"
    And el sistema actualiza el total pendiente de la reserva
    And el sistema muestra "Cargo registrado exitosamente"

  Scenario: Cargo en reserva finalizada
    Given la reserva está en estado "checked_out"
    When el recepcionista intenta registrar un cargo
    Then el sistema muestra "No se pueden agregar cargos a una reserva finalizada"
```

## 7.35 CU-O35: Editar Metadata de Destino

```gherkin
Feature: Edición de metadata de destino
  Como auditor de datos
  Quiero editar la metadata de los destinos hoteleros (nombre, coordenadas, país, ciudad)
  Para corregir nombres genéricos o numéricos del dataset original

  Background:
    Given el auditor está autenticado con rol "data_auditor"
    And el destino existe en "dim_destinations"

  Scenario: Edición exitosa de metadata de destino
    When el auditor busca un destino por código
    And modifica el nombre visible a "Cancún"
    And asigna coordenadas 21.1619, -86.8515
    And ingresa país "México" y ciudad "Cancún"
    And guarda los cambios
    Then el sistema actualiza "dim_destinations" con la nueva metadata
    And el sistema registra el cambio en "hotel_edit_history"
    And el sistema muestra "Destino actualizado exitosamente"

  Scenario: Coordenadas inválidas
    When el auditor ingresa latitud 100 y longitud 200
    Then el sistema muestra "Coordenadas geográficas inválidas"
    And el sistema no actualiza el destino
```

## 7.36 CU-O36: Editar Nombre Visible de Hotel

```gherkin
Feature: Edición de nombre visible de hotel
  Como auditor de datos o marketing
  Quiero editar el nombre comercial visible de hoteles con ID numérico
  Para mejorar la experiencia de búsqueda con nombres reales

  Background:
    Given el usuario está autenticado con rol "data_auditor" o "marketing"
    And el hotel existe en "dim_hotels"

  Scenario: Edición exitosa de nombre visible
    When el usuario busca un hotel por prop_id "14239"
    And el sistema muestra nombre actual "Property 14239"
    And el usuario ingresa nuevo nombre "Hotel Paraíso Caribe"
    And guarda el cambio
    Then el sistema actualiza "dim_hotels.hotel_name" a "Hotel Paraíso Caribe"
    And el sistema establece "dim_hotels.name_is_manual_override = true"
    And el sistema registra el cambio en "hotel_edit_history"
    And el sistema muestra "Nombre de hotel actualizado exitosamente"
    And el hotel aparece con el nuevo nombre en búsquedas

  Scenario: Nombre muy corto
    When el usuario intenta guardar un nombre de 1 carácter
    Then el sistema muestra "El nombre debe tener al menos 3 caracteres"
```

## 7.37 CU-O37: Visualizar Mapa Mundial de Destinos

```gherkin
Feature: Visualización de mapa mundial de destinos con hoteles
  Como usuario de marketing o datos
  Quiero visualizar un mapa mundial interactivo con destinos y hoteles geolocalizados
  Para explorar la cobertura geográfica y filtrar hoteles por ubicación y precio

  Background:
    Given el usuario está autenticado
    And existen destinos con coordenadas en "dim_destinations"
    And existe conexión a internet para tiles de mapa

  Scenario: Visualización exitosa del mapa mundial
    When el usuario navega a la sección "Mapa Mundial"
    Then el sistema carga un mapa Leaflet.js centrado en vista mundial
    And el sistema muestra marcadores de destinos con nombre visible
    And los hoteles se muestran como marcadores coloreados por rango de precio
    And el usuario puede hacer zoom y hacer clic en marcadores para ver detalle

  Scenario: Sin internet para tiles
    When el navegador no puede cargar los tiles de OpenStreetMap
    Then el sistema muestra "Se requiere conexión a internet para visualizar el mapa"

  Scenario: Sin destinos con coordenadas
    Given ningún destino tiene coordenadas configuradas
    When el usuario navega al mapa
    Then el sistema muestra "No hay destinos con coordenadas configuradas"
    And el sistema sugiere usar CU-O35/CU-O38 para asignar coordenadas
```

## 7.38 CU-O38: Seleccionar Ubicación en Mapa Interactivo

```gherkin
Feature: Selección de ubicación en mapa interactivo
  Como auditor de datos
  Quiero seleccionar la ubicación de un destino haciendo clic en un mapa mundial
  Para capturar coordenadas geográficas precisas sin calcularlas manualmente

  Background:
    Given el usuario está autenticado con rol "data_auditor"
    And el destino existe en "dim_destinations"
    And existe conexión a internet

  Scenario: Selección exitosa de ubicación en mapa
    When el usuario está editando un destino y hace clic en "Seleccionar en mapa"
    Then el sistema abre un modal con mapa Leaflet.js interactivo
    When el usuario navega al destino deseado y hace clic en el punto exacto
    Then el sistema captura las coordenadas (lat, lng) del clic
    And el sistema muestra previsualización de coordenadas
    When el usuario confirma la selección
    Then el sistema cierra el modal y rellena los campos de coordenadas

  Scenario: Sin conexión a internet
    When el usuario intenta abrir el selector de mapa sin conexión
    Then el sistema muestra "Se requiere conexión a internet para el mapa interactivo"
```

## 7.39 CU-O39: Gestionar Limpieza y Rotación de Habitaciones

```gherkin
Feature: Gestión de limpieza y rotación de habitaciones
  Como recepcionista o gerente
  Quiero gestionar el flujo de limpieza post-checkout
  Para que las habitaciones estén disponibles para el próximo huésped

  Background:
    Given el usuario está autenticado con rol "recepcionista" o "hotel_manager"
    And existe una habitación en "hotel_rooms"

  Scenario: Rotación post-checkout exitosa
    When un huésped completa el check-out
    Then el sistema marca automáticamente la habitación como "cleaning_needed"
    When el recepcionista asigna la tarea de limpieza
    And el personal completa la limpieza
    Then el sistema actualiza el estado a "available"
    And el sistema registra el tiempo de rotación

  Scenario: Lista de tareas de limpieza pendientes
    When el recepcionista abre la lista de tareas de limpieza
    Then el sistema muestra las habitaciones pendientes con: número, tipo, tiempo desde check-out
```

## 7.40 CU-O40: Gestionar Mantenimiento Preventivo

```gherkin
Feature: Gestión de mantenimiento preventivo de habitaciones
  Como gerente de hotel
  Quiero programar y registrar mantenimiento preventivo de habitaciones
  Para mantener las instalaciones en óptimas condiciones

  Background:
    Given el gerente está autenticado con rol "hotel_manager"
    And la habitación existe en "hotel_rooms"

  Scenario: Programación exitosa de mantenimiento preventivo
    When el gerente navega al calendario de mantenimiento
    And hace clic en "Nuevo mantenimiento"
    And selecciona tipo "preventivo - HVAC", habitación "101", fecha "2026-07-15"
    And asigna prioridad "media"
    And guarda el programa
    Then el sistema crea el documento en "maintenance_schedule"
    And el sistema muestra la tarea en el calendario

  Scenario: Mantenimiento en habitación ocupada
    When el gerente intenta programar mantenimiento en una habitación con reserva activa
    Then el sistema muestra conflicto de fechas
    And el sistema sugiere fechas alternativas donde la habitación esté disponible
```

## 7.41 CU-O41: Gestionar Notificaciones y Alertas del Sistema

```gherkin
Feature: Gestión de notificaciones y alertas del sistema
  Como super admin
  Quiero gestionar plantillas, canales y reglas de notificación del sistema
  Para automatizar las comunicaciones con huéspedes y personal del hotel

  Background:
    Given el usuario está autenticado con rol "super_admin"
    And el módulo de notificaciones está disponible

  Scenario: Crear plantilla de notificación
    When el usuario navega al gestor de plantillas
    And hace clic en "Nueva plantilla"
    And selecciona tipo "email", nombre "Confirmación de reserva"
    And ingresa asunto "Reserva confirmada en {hotel_name}"
    And ingresa cuerpo "Estimado {guest_name}, su reserva {booking_id} ha sido confirmada para el {check_in}."
    And guarda la plantilla
    Then el sistema crea el documento en "notification_templates"
    And el sistema muestra "Plantilla creada exitosamente"

  Scenario: Configurar canal de notificación
    When el usuario navega a configuración de canales
    And selecciona tipo de evento "booking_confirmed"
    And activa los canales "email" y "in-app"
    And guarda la configuración
    Then el sistema actualiza "notification_channels"
    And el sistema muestra "Canales configurados exitosamente"

  Scenario: Envío automático al confirmar reserva
    Given existe una plantilla activa para "booking_confirmed" en "notification_templates"
    And existe configuración de canal para "booking_confirmed" en "notification_channels"
    When un cliente completa una reserva exitosamente
    Then el sistema consulta la plantilla correspondiente
    And el sistema reemplaza las variables con los datos de la reserva
    And el sistema envía la notificación por los canales configurados
    And el sistema registra el envío en "notification_history"
```

## 7.42 CU-O42: Validar Ciclo de Vida de la Reserva

```gherkin
Feature: Validación del ciclo de vida de la reserva
  Como sistema
  Quiero validar que cada reserva complete su ciclo de vida sin anomalías
  Para detectar y alertar sobre estados bloqueados o acciones pendientes

  Background:
    Given existen reservas en "booking_orders" con estados del ciclo de vida
    And el sistema tiene programada la tarea de validación cada hora

  Scenario: Detección de reserva pendiente por más de 24h
    Given existe una reserva en estado "pending" creada hace más de 24 horas
    When el sistema ejecuta la validación programada
    Then el sistema detecta la anomalía en la reserva
    And el sistema genera una alerta en "alerts"
    And el sistema envía notificación al gerente del hotel
    And el sistema muestra la alerta en el panel de notificaciones

  Scenario: Check-in no completado en fecha programada
    Given existe una reserva en estado "confirmed" con check_in programado para hoy
    And la hora actual es posterior a las 18:00
    When el sistema ejecuta la validación programada
    Then el sistema detecta el check-in no completado
    And el sistema genera una alerta en "alerts"
    And el sistema notifica al recepcionista del hotel

  Scenario: Ciclo de vida completado sin anomalías
    Given una reserva ha pasado por pending → confirmed → checked_in → checked_out
    When el sistema ejecuta la validación programada
    Then el sistema no genera ninguna alerta para la reserva
    And el sistema registra la validación exitosa en el log interno
```

---

# 8. TRAZABILIDAD OE → OT → OO → CU → HISTORIA DE USUARIO

## 8.1 Matriz de Trazabilidad Completa

La siguiente matriz conecta los objetivos s (OE) con los objetivos tácticos (OT), operativos (OO), casos de uso operativos (CU-O) y sus historias de usuario Gherkin correspondientes.

| OT | OO | CU | Historia Gherkin | |----|----|----|----|-----------------| | OT1.1: Automatizar captación digital internacional | OO1.1.1: Registrar eventos de búsqueda y reserva | CU-O02: Buscar hoteles | HU-02: Búsqueda de hoteles | | OT1.1 | OO1.1.1 | CU-O03: Filtrar y comparar hoteles | HU-03: Filtrado y comparación de hoteles | | OT1.1 | OO1.1.1 | CU-O04: Ver detalle de hotel | HU-04: Detalle de hotel | | OT1.1 | OO1.1.1 | CU-O05: Solicitar reserva | HU-05: Solicitud de reserva | | OT1.1 | OO1.1.2: Medir conversión del embudo digital | CU-O26: Consultar reportes de revenue y mercado | HU-26: Consulta de reportes de revenue y mercado | | OT1.2: Fortalecer reputación del huésped | OO1.2.1: Registrar reseñas de estancia | CU-O22: Registrar reseña de estancia | HU-22: Registro de reseña de estancia | | OT1.2 | OO1.2.1 | CU-O23: Moderar y responder reseña | HU-23: Moderación y respuesta de reseñas | | OT1.2 | OO1.2.2: Generar comprobantes/facturación | CU-O24: Generar comprobante o factura | HU-24: Generación de comprobante o factura | | OT1.2 | OO1.2.2 | CU-O25: Registrar pago asociado a reserva | HU-25: Registro de pago asociado a reserva | | OT2.1: Estandarizar servicios por API | OO2.1.2: Validar JWT y roles por endpoint | CU-O01: Iniciar sesión con JWT | HU-01: Inicio de sesión con JWT | | OT2.1 | OO2.1.2 | CU-O28: Administrar cuenta, sesión y cierre seguro | HU-28: Administración de cuenta y cierre seguro | | OT2.2: Integrar módulos comerciales | OO2.2.1: Administrar perfil comercial de hotel | CU-O12: Editar nombre comercial del hotel | HU-12: Edición de nombre comercial del hotel | | OT2.2 | OO2.2.2: Conectar habitaciones, tarifas, disponibilidad | CU-O14: Crear tipo de habitación | HU-14: Creación de tipo de habitación | | OT2.2 | OO2.2.2 | CU-O15: Actualizar inventario por fecha | HU-15: Actualización de inventario por fecha | | OT2.2 | OO2.2.2 | CU-O16: Registrar bloqueo de disponibilidad | HU-16: Bloqueo de disponibilidad | | OT2.2 | OO2.2.2 | CU-O17: Crear plan tarifario | HU-17: Creación de plan tarifario | | OT2.2 | OO2.2.2 | CU-O18: Configurar tarifa por fecha | HU-18: Configuración de tarifa por fecha | | OT2.2 | OO2.2.2 | CU-O20: Editar política hotelera | HU-20: Edición de política hotelera | | OT3.1: Mantener infraestructura portable | OO3.1.1-Ejecutar servicios Docker | *(Infraestructura — sin CU operativo directo)* | — | | OT3.1 | OO3.1.2-Monitorear servicios | *(Infraestructura — sin CU operativo directo)* | — | | OT3.2: Automatizar gobierno de datos | OO3.2.1: Ejecutar pipeline ETL | CU-O27: Consultar reporte de calidad de datos | HU-27: Consulta de reporte de calidad y registros rechazados | | OT3.2 | OO3.2.2: Registrar auditoría y trazabilidad | CU-O13: Consultar historial de cambios de propiedad | HU-13: Consulta de historial de cambios de propiedad | | OT3.2 | OO3.2.2 | CU-O28: Administrar cuenta y sesión | HU-28: Administración de cuenta y cierre seguro | | OT3.2 | OO3.2.3: Gestionar notificaciones automáticas | CU-O41: Gestionar notificaciones y alertas | HU-41: Gestión de notificaciones y alertas | | OT4.1: Consolidar analítica global | OO4.1.1: Consultar dashboard ejecutivo | CU-O26: Consultar reportes de revenue y mercado | HU-26: Consulta de reportes de revenue y mercado | | OT4.1 | OO4.1.2: Analizar mercados y destinos | CU-O26: Consultar reportes de revenue y mercado | HU-26: Consulta de reportes de revenue y mercado | | OT4.2: Aplicar BI y ML | OO4.2.1: Proyectar demanda y revenue | CU-O26: Consultar reportes de revenue y mercado | HU-26: Consulta de reportes de revenue y mercado | | OT4.2 | OO4.2.2: Detectar anomalías y calidad | CU-O27: Consultar reporte de calidad de datos | HU-27: Consulta de reporte de calidad y registros rechazados | | OT2.3: Enriquecer catálogo geoespacial | OO2.3.1: Editar metadata de destinos | CU-O35: Editar metadata de destino | HU-35: Edición de metadata de destino | | OT2.3 | OO2.3.2: Editar nombre visible de hotel | CU-O36: Editar nombre visible de hotel | HU-36: Edición de nombre visible de hotel | | OT2.3 | OO2.3.3: Visualizar destinos en mapa interactivo | CU-O37: Visualizar mapa mundial | HU-37: Visualización de mapa mundial | | OT2.3 | OO2.3.3 | CU-O38: Seleccionar ubicación en mapa | HU-38: Selección de ubicación en mapa | | OT3.3: Automatizar gestión habitaciones | OO3.3.1: Consultar estado de habitaciones | CU-O30: Consultar estado de habitaciones | HU-30: Consulta de estado de habitaciones | | OT3.3 | OO3.3.1 | CU-O31: Asignar tipo de habitación | HU-31: Asignación de tipo de habitación | | OT3.3 | OO3.3.1 | CU-O32: Consultar disponibilidad por habitación | HU-32: Consulta de disponibilidad por habitación | | OT3.3 | OO3.3.2: Gestionar limpieza y rotación | CU-O39: Gestionar limpieza y rotación | HU-39: Gestión de limpieza y rotación | | OT3.3 | OO3.3.2 | CU-T14: Gestionar rotación y limpieza | HU-T14: Gestión de rotación y limpieza | | OT3.3 | OO3.3.3: Programar mantenimiento preventivo | CU-O40: Gestionar mantenimiento preventivo | HU-40: Gestión de mantenimiento preventivo | | OT3.3 | OO3.3.3 | CU-T15: Programar mantenimiento preventivo proactivo | HU-T15: Programación de mantenimiento preventivo | | OT3.3 | OO3.3.4: Registrar cargos adicionales | CU-O34: Registrar cargos adicionales | HU-34: Registro de cargos adicionales | | OT3.3 | OO3.3.1 | CU-O33: Gestionar amenities por tipo habitación | HU-33: Gestión de amenities por tipo habitación | | OT3.3 | OO3.3.5: Validar ciclo de vida de reservas | CU-O42: Validar ciclo de vida reserva | HU-42: Validación de ciclo de vida de reserva | | OT5.1: Monitorear eficiencia operativa | OO5.1.1: Monitorear eficiencia | : Monitorear eficiencia operativa | HU-E09: Monitoreo de eficiencia operativa |
## 8.2 Trazabilidad por Caso de Uso

| Código CU | Nombre CU | OO Asociado | OE | Historia Gherkin (Sección 7) | |-----------|-----------|-------------|----|------------------------------| | CU-O01 | Iniciar sesión con JWT | OO2.1.2 | §7.1 HU-O01 | | CU-O02 | Buscar hoteles | OO1.1.1 | §7.2 HU-O02 | | CU-O03 | Filtrar y comparar hoteles | OO1.1.1 | §7.3 HU-O03 | | CU-O04 | Ver detalle de hotel | OO1.1.1 | §7.4 HU-O04 | | CU-O05 | Solicitar reserva | OO1.1.1 | §7.5 HU-O05 | | CU-O06 | Consultar mis reservas | OO1.1.1 | §7.6 HU-O06 | | CU-O07 | Cancelar reserva según política | OO1.1.1 | §7.7 HU-O07 | | CU-O08 | Registrar reserva manual | OO2.2.2 | §7.8 HU-O08 | | CU-O09 | Consultar solicitudes de reserva | OO2.2.2 | §7.9 HU-O09 | | CU-O10 | Completar check-in | OO2.2.2 | §7.10 HU-O10 | | CU-O11 | Completar check-out | OO2.2.2 | §7.11 HU-O11 | | CU-O12 | Editar nombre comercial del hotel | OO2.2.1 | §7.12 HU-O12 | | CU-O13 | Consultar historial de cambios | OO3.2.2 | §7.13 HU-O13 | | CU-O14 | Crear tipo de habitación | OO2.2.2 | §7.14 HU-O14 | | CU-O15 | Actualizar inventario por fecha | OO2.2.2 | §7.15 HU-O15 | | CU-O16 | Registrar bloqueo de disponibilidad | OO2.2.2 | §7.16 HU-O16 | | CU-O17 | Crear plan tarifario | OO2.2.2 | §7.17 HU-O17 | | CU-O18 | Configurar tarifa por fecha | OO2.2.2 | §7.18 HU-O18 | | CU-O19 | Crear promoción y cupón | OO1.1.2 | §7.19 HU-O19 | | CU-O20 | Editar política hotelera | OO2.2.2 | §7.20 HU-O20 | | CU-O21 | Actualizar amenities, imágenes y contenido | OO2.2.2 | §7.21 HU-O21 | | CU-O22 | Registrar reseña de estancia | OO1.2.1 | §7.22 HU-O22 | | CU-O23 | Moderar y responder reseña | OO1.2.1 | §7.23 HU-O23 | | CU-O24 | Generar comprobante o factura | OO1.2.2 | §7.24 HU-O24 | | CU-O25 | Registrar pago asociado a reserva | OO1.2.2 | §7.25 HU-O25 | | CU-O26 | Consultar reportes de revenue y mercado | OO1.1.2, OO4.1.1, OO4.1.2, OO4.2.1 | §7.26 HU-O26 | | CU-O27 | Consultar reporte de calidad de datos | OO3.2.1, OO4.2.2 | §7.27 HU-O27 | | CU-O28 | Administrar cuenta, sesión y cierre seguro | OO2.1.2, OO3.2.2 | §7.28 HU-O28 | | CU-O29 | Cambiar contraseña y actualizar perfil | OO2.1.2 | §7.29 HU-O29 | | CU-O30 | Consultar estado actual de habitaciones | OO3.3.1 | §7.30 HU-O30 | | CU-O31 | Asignar tipo de habitación | OO3.3.1 | §7.31 HU-O31 | | CU-O32 | Consultar disponibilidad por habitación | OO3.3.1 | §7.32 HU-O32 | | CU-O33 | Gestionar amenities por tipo de habitación | OO3.3.1 | §7.33 HU-O33 | | CU-O34 | Registrar cargos adicionales | OO3.3.4 | §7.34 HU-O34 | | CU-O35 | Editar metadata de destino | OO2.3.1 | §7.35 HU-O35 | | CU-O36 | Editar nombre visible de hotel | OO2.3.2 | §7.36 HU-O36 | | CU-O37 | Visualizar mapa mundial de destinos | OO2.3.3 | §7.37 HU-O37 | | CU-O38 | Seleccionar ubicación en mapa interactivo | OO2.3.3 | §7.38 HU-O38 | | CU-O39 | Gestionar limpieza y rotación | OO3.3.2 | §7.39 HU-O39 | | CU-O40 | Gestionar mantenimiento preventivo | OO3.3.3 | §7.40 HU-O40 | | CU-O41 | Gestionar notificaciones y alertas | OO3.2.3 | §7.41 HU-O41 | | CU-O42 | Validar ciclo de vida de reserva | OO3.3.5 | §7.42 HU-O42 | | CU-T14 | Gestionar rotación y limpieza (Táctico) | OO3.3.2 | §6.42 HU-T14 | | CU-T15 | Programar mantenimiento preventivo (Táctico) | OO3.3.3 | §6.43 HU-T15 |
