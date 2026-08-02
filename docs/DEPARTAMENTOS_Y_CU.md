# HotelData — Departamentos, Casos de Uso y Colecciones MongoDB

**Documento**: Arquitectura Organizacional y Funcional  
**Sistema**: HotelData — Plataforma de gestión hotelera y analítica  
**Versión**: 2.0 | **Fecha**: 2026-07-04  
**Base**: Backend FastAPI + Frontend Angular + MongoDB

---

## Tabla Resumen de Departamentos

| # | Departamento | Módulos Backend | Módulos Frontend | Colecciones MongoDB |
|---|-------------|-----------------|------------------|---------------------|
| 1 | **Comercial / Experiencia Cliente** | hotels, reservations (guest) | hotel-search, hotel-compare, hotel-detail, reservations | 12 |
| 2 | **Revenue Management** | revenue, partner/rates | rates, revenue | 8 |
| 3 | **Marketing Hotelero / Partner** | partner, amenities, reviews (public), partner/rates | properties, policies, rooms, amenities | 16 |
| 4 | **Operaciones Hoteleras** | reservations (mgmt, incluye API del Timeline), housekeeping, reception | management, check-ins, check-outs, manual-reservations, housekeeping, reception, shifts, availability | 19 |
| 5 | **Facturación, Pagos y Gastos** | billing, expenses | billing, expenses | 13 |
| 6 | **Recursos Humanos** | hr | hr | 6 |
| 7 | **Administración del Sistema** | admin, auth, account, users, settings, global_settings, notifications | admin, account, system-admin, ownership, settings, notifications | 16 |
| 8 | **Datos, Analítica y Geolocalización** | kpi, audit, map, geo_catalog, reports | map, geo-catalog | 14 |
| 9 | **Servicios al Huésped (In-Stay)** | instay, amenities (guest), lost_and_found | in-stay, lost-and-found | 8 |

**Total: 9 departamentos | 110 colecciones MongoDB**

---

# 1. DEPARTAMENTO: COMERCIAL / EXPERIENCIA CLIENTE

## 1.1 Descripción
Gestiona la experiencia del cliente desde la búsqueda hasta la reserva, maximizando la conversión y satisfacción del viajero.

## 1.2 Secciones / Módulos
- **Búsqueda de hoteles** (`hotel-search`, `hotel-compare`, `hotel-detail`)
- **Reservas del cliente** (`reservations` — flujo guest)
- **Reseñas públicas** (`reviews` — vista pública)
- **Catálogo de amenities** (`amenities` — vista guest)

## 1.3 Actores
| Actor | Descripción |
|-------|-------------|
| **Cliente / Viajero** | Usuario final que busca, compara, reserva y gestiona sus reservas |
| **Sistema** | Motor de búsqueda, cálculo de disponibilidad, persistencia de reservas |

## 1.4 Casos de Uso

### CU-C01: Buscar Hoteles
> **Actor**: Cliente  
> **Descripción**: Buscar hoteles por destino, fechas y número de huéspedes  
> **Precondición**: Cliente accede a la página de búsqueda  
> **Flujo principal**:
> 1. Cliente ingresa destino, fechas de entrada/salida, huéspedes
> 2. Sistema consulta `dim_hotels`, `room_inventory_calendar`, `hotel_rate_calendar`
> 3. Sistema filtra hoteles con disponibilidad en todas las noches
> 4. Sistema devuelve lista ordenada por precio ascendente
> 5. Cliente visualiza resultados

**Relaciones**:
- `<<include>>` CU-C02: Calcular Tarifa en Tiempo Real *(cada hotel necesita su precio mínimo)*
- `<<include>>` CU-C03: Validar Disponibilidad *(solo muestra hoteles con al menos 1 tipo disponible)*

### CU-C02: Calcular Tarifa en Tiempo Real *(abstracto)*
> **Actor**: Sistema  
> **Descripción**: Calcular precio mínimo por noche desde `hotel_rate_calendar`

### CU-C03: Validar Disponibilidad *(abstracto)*
> **Actor**: Sistema  
> **Descripción**: Verificar disponibilidad en `room_inventory_calendar`

### CU-C04: Filtrar y Comparar Hoteles
> **Actor**: Cliente  
> **Descripción**: Aplicar filtros comerciales y comparar hasta 3 hoteles lado a lado  
> **Flujo principal**:
> 1. Cliente aplica filtros (precio, rating, amenities)
> 2. Sistema actualiza lista
> 3. Cliente selecciona 2-3 hoteles y hace clic en "Comparar"
> 4. Sistema muestra vista comparativa

**Relaciones**:
- `<<extend>>` CU-C01: Buscar Hoteles *(el filtrado extiende la búsqueda base)*
- `<<include>>` CU-C02: Calcular Tarifa en Tiempo Real

### CU-C05: Ver Detalle de Hotel
> **Actor**: Cliente  
> **Descripción**: Visualizar galería, descripción, amenities, políticas, tarifas y reseñas  
> **Flujo principal**:
> 1. Cliente hace clic en un hotel de la lista
> 2. Sistema carga `hotel_images`, `hotel_content_pages`, `hotel_policies`, `reviews`
> 3. Sistema calcula tarifas por tipo de habitación desde `hotel_rate_calendar`
> 4. Cliente visualiza detalle completo

**Relaciones**:
- `<<include>>` CU-C06: Consultar Reseñas Públicas *(las reseñas son parte del detalle)*

### CU-C06: Consultar Reseñas Públicas *(abstracto)*
> **Actor**: Sistema  
> **Descripción**: Cargar reseñas aprobadas de `reviews` / `fact_reviews`

### CU-C07: Solicitar Reserva
> **Actor**: Cliente  
> **Descripción**: Solicitar reserva seleccionando habitación, fechas y datos de huéspedes  
> **Precondición**: Cliente autenticado (JWT)  
> **Flujo principal**:
> 1. Cliente selecciona tipo de habitación y fechas
> 2. Sistema valida disponibilidad (`room_inventory_calendar`)
> 3. Sistema calcula total (`hotel_rate_calendar`)
> 4. Cliente ingresa datos de huéspedes
> 5. Sistema crea `booking_orders` en estado `"pending"`
> 6. Sistema crea `booking_guests`
> 7. Sistema registra en `booking_status_history`

**Relaciones**:
- `<<include>>` CU-C02: Calcular Tarifa en Tiempo Real
- `<<include>>` CU-C03: Validar Disponibilidad
- `<<include>>` CU-C08: Validar Cliente Autenticado *(abstracto)*

### CU-C08: Validar Cliente Autenticado *(abstracto)*
> **Actor**: Sistema  
> **Descripción**: Verificar JWT válido antes de permitir reserva

### CU-C09: Consultar Mis Reservas
> **Actor**: Cliente  
> **Descripción**: Ver listado de reservas propias con estado, fechas y acciones  
> **Flujo principal**:
> 1. Cliente navega a "Mis Reservas"
> 2. Sistema consulta `booking_orders` filtrado por `user_id`
> 3. Cliente visualiza lista con estados y totales

### CU-C10: Cancelar Reserva
> **Actor**: Cliente  
> **Descripción**: Cancelar una reserva validando políticas del hotel  
> **Precondición**: Reserva en estado `"pending"` o `"confirmed"`  
> **Flujo principal**:
> 1. Cliente selecciona reserva y hace clic en "Cancelar"
> 2. Sistema carga política de cancelación desde `hotel_policies`
> 3. Sistema muestra diálogo con posibles cargos
> 4. Cliente confirma cancelación
> 5. Sistema actualiza `booking_orders` a `"cancelled"`
> 6. Sistema libera inventario (si estaba confirmed)
> 7. Sistema registra en `booking_status_history`

**Relaciones**:
- `<<extend>>` CU-C09: Consultar Mis Reservas *(la cancelación extiende la consulta)*

### CU-C11: Registrar Reseña
> **Actor**: Cliente  
> **Descripción**: Dejar reseña después del check-out  
> **Precondición**: Reserva en estado `"checked_out"`  
> **Flujo principal**:
> 1. Cliente accede a reseñas desde reserva completada
> 2. Cliente ingresa calificación y comentario
> 3. Sistema crea `review` en estado `"pending"`
> 4. Sistema realiza dual-write a `fact_reviews`
> 5. Si calificación ≥ 4: aprobación automática

## 1.5 Diagrama de Casos de Uso (Texto)

```
Cliente
  ├── CU-C01: Buscar Hoteles
  │   ├── <<include>> CU-C02: Calcular Tarifa
  │   └── <<include>> CU-C03: Validar Disponibilidad
  ├── CU-C04: Filtrar y Comparar
  │   ├── <<extend>> CU-C01
  │   └── <<include>> CU-C02
  ├── CU-C05: Ver Detalle
  │   └── <<include>> CU-C06: Consultar Reseñas
  ├── CU-C07: Solicitar Reserva
  │   ├── <<include>> CU-C02
  │   ├── <<include>> CU-C03
  │   └── <<include>> CU-C08: Validar Autenticación
  ├── CU-C09: Consultar Mis Reservas
  │   └── <<extend>> CU-C10: Cancelar Reserva
  └── CU-C11: Registrar Reseña
```

## 1.6 Flujo de Eventos Principal

```
Evento 1: Llegada del Cliente
  └── Cliente accede a /hotels/search
  └── Sistema muestra formulario de búsqueda

Evento 2: Ejecución de Búsqueda (CU-C01)
  └── Cliente ingresa parámetros
  └── Sistema consulta dim_hotels + room_inventory_calendar + hotel_rate_calendar
  └── Sistema devuelve lista ordenada por precio

Evento 3: Refinamiento (CU-C04)
  └── Cliente aplica filtros
  └── Sistema actualiza resultados
  └── Decisión: ¿Comparar? → Sí: vista lado a lado

Evento 4: Detalle (CU-C05)
  └── Cliente hace clic en hotel
  └── Sistema carga imágenes, descripción, políticas, tarifas, reseñas
  └── Decisión: ¿Reservar? → Sí: Evento 5

Evento 5: Solicitud de Reserva (CU-C07)
  └── Cliente selecciona habitación y fechas
  └── Sistema valida disponibilidad y calcula total
  └── Cliente ingresa datos de huéspedes
  └── Sistema crea booking_orders en "pending"

Evento 6: Post-Reserva (CU-C09)
  └── Cliente consulta "Mis reservas"
  └── Decisión: ¿Cancelar? → Sí: CU-C10
```

## 1.7 Colecciones MongoDB

| Colección | Tipo | Propósito | CU Relacionados |
|-----------|------|-----------|-----------------|
| `dim_hotels` | Lectura | Datos básicos de hoteles para búsqueda | CU-C01, CU-C04, CU-C05 |
| `dim_destinations` | Lectura | Destinos para filtrado | CU-C01 |
| `dim_visitor_countries` | Lectura | Países para filtrado | CU-C01 |
| `room_types` | Lectura | Tipos de habitación disponibles | CU-C05, CU-C07 |
| `room_inventory_calendar` | Lectura | Disponibilidad por fecha | CU-C01, CU-C03, CU-C07 |
| `hotel_rate_calendar` | Lectura | Precios por fecha | CU-C01, CU-C02, CU-C05, CU-C07 |
| `hotel_images` | Lectura | Galería de imágenes | CU-C05 |
| `hotel_content_pages` | Lectura | Descripciones, highlights | CU-C05 |
| `hotel_policies` | Lectura | Políticas de cancelación | CU-C05, CU-C10 |
| `hotel_amenities` | Lectura | Amenities del hotel | CU-C05 |
| `booking_orders` | Escritura | Creación de reservas | CU-C07, CU-C09, CU-C10 |
| `booking_guests` | Escritura | Datos de huéspedes | CU-C07 |
| `booking_status_history` | Escritura | Trazabilidad de estados | CU-C07, CU-C10 |
| `reviews` | Escritura | Reseñas de clientes | CU-C11 |
| `fact_reviews` | Escritura | Dual-write analítico | CU-C11 |
| `user_activity_logs` | Escritura | Auditoría | Todos |

---

# 2. DEPARTAMENTO: REVENUE MANAGEMENT

## 2.1 Descripción
Configurar y optimizar tarifas, planes tarifarios, promociones y cupones para maximizar el ingreso por habitación disponible.

## 2.2 Secciones / Módulos
- **Planes tarifarios** (`rate_plans`, `rate_rules`)
- **Calendario de tarifas** (`hotel_rate_calendar`)
- **Promociones y cupones** (`promotion_campaigns`, `coupon_codes`)
- **Reportes de revenue** (`kpi`, `reports`)

## 2.3 Actores
| Actor | Descripción |
|-------|-------------|
| **Revenue Manager** | Define estrategias de precios, planes tarifarios, analiza reportes |
| **Marketing Hotelero** | Crea promociones y cupones para campañas |
| **Gerente de hotel** | Consulta reportes de revenue |

## 2.4 Casos de Uso

### CU-R01: Crear Plan Tarifario
> **Actor**: Revenue Manager  
> **Flujo principal**:
> 1. Revenue manager ingresa nombre, descripción, precio base
> 2. Sistema valida unicidad por propiedad
> 3. Sistema crea `rate_plans`
> 4. Sistema registra en `user_activity_logs`

### CU-R02: Configurar Tarifa por Fecha
> **Actor**: Revenue Manager  
> **Flujo principal**:
> 1. Revenue manager navega al calendario de tarifas
> 2. Sistema muestra precios actuales
> 3. Revenue manager selecciona fecha/rango y asigna precio
> 4. Sistema valida precio > 0
> 5. Sistema crea/actualiza `hotel_rate_calendar`

**Relaciones**:
- `<<include>>` CU-R01: Crear Plan Tarifario *(debe existir un plan para configurar tarifas)*

### CU-R03: Crear Promoción
> **Actor**: Revenue Manager / Marketing  
> **Flujo principal**:
> 1. Usuario crea campaña con nombre, descuento, vigencia
> 2. Sistema genera código de cupón único
> 3. Sistema guarda en `promotion_campaigns` y `coupon_codes`

### CU-R04: Aplicar Cupón en Reserva *(extend)*
> **Actor**: Cliente  
> **Descripción**: Cliente ingresa cupón durante solicitud de reserva  
> **Flujo principal**:
> 1. Cliente ingresa código de cupón
> 2. Sistema valida vigencia y usos restantes
> 3. Sistema aplica descuento sobre tarifa base

**Relaciones**:
- `<<extend>>` CU-C07: Solicitar Reserva *(aplicar cupón extiende la reserva base)*

### CU-R05: Consultar Reportes de Revenue
> **Actor**: Revenue Manager / Gerente  
> **Flujo principal**:
> 1. Usuario consulta dashboard de revenue
> 2. Sistema agrega datos desde `fact_hotel_reservations`
> 3. Sistema calcula ADR, RevPAR, ocupación, precio promedio
> 4. Sistema muestra top hoteles, destinos y países

## 2.5 Diagrama de Casos de Uso (Texto)

```
Revenue Manager
  ├── CU-R01: Crear Plan Tarifario
  ├── CU-R02: Configurar Tarifa por Fecha
  │   └── <<include>> CU-R01
  ├── CU-R03: Crear Promoción
  └── CU-R05: Consultar Reportes Revenue

Marketing
  └── CU-R03: Crear Promoción

Cliente
  └── CU-C07: Solicitar Reserva
      └── <<extend>> CU-R04: Aplicar Cupón
```

## 2.6 Colecciones MongoDB

| Colección | Tipo | Propósito | CU Relacionados |
|-----------|------|-----------|-----------------|
| `rate_plans` | Escritura | Planes tarifarios | CU-R01 |
| `rate_rules` | Escritura | Reglas de variación | CU-R01 |
| `hotel_rate_calendar` | Escritura | Precios por fecha | CU-R02 |
| `promotion_campaigns` | Escritura | Campañas promocionales | CU-R03 |
| `coupon_codes` | Escritura | Códigos de cupón | CU-R03, CU-R04 |
| `fact_hotel_reservations` | Lectura | Datos analíticos | CU-R05 |
| `booking_orders` | Lectura | Reservas con cupón | CU-R04 |
| `user_activity_logs` | Escritura | Auditoría | CU-R01, CU-R02, CU-R03 |

---

# 3. DEPARTAMENTO: MARKETING HOTELERO / PARTNER

## 3.1 Descripción
Gestionar la reputación online, contenido comercial, imágenes, amenities y perfil de las propiedades hoteleras.

## 3.2 Secciones / Módulos
- **Gestión de propiedades** (`partner/properties`)
- **Contenido del hotel** (`partner/content` — descripciones, highlights)
- **Imágenes** (`partner/images`)
- **Amenities** (`partner/amenities`)
- **Políticas hoteleras** (`partner/policies`)
- **Features de habitación** (`partner/room_features`)
- **Historial de cambios** (`partner/audit`, `partner/history`)

## 3.3 Actores
| Actor | Descripción |
|-------|-------------|
| **Marketing Hotelero** | Gestiona contenido, imágenes, amenities, reseñas y nombre comercial |
| **Hotel Partner** | Edita contenido de su propia propiedad |
| **Super Admin** | Moderación avanzada |

## 3.4 Casos de Uso

### CU-M01: Editar Nombre Comercial del Hotel
> **Actor**: Marketing / Hotel Partner  
> **Flujo principal**:
> 1. Usuario navega a edición de perfil
> 2. Sistema muestra formulario con campos editables
> 3. Usuario modifica `display_name` / `hotel_name`
> 4. Sistema activa `manual_override = true`
> 5. Sistema registra en `hotel_profile_changes`

### CU-M02: Actualizar Contenido del Hotel
> **Actor**: Marketing / Hotel Partner  
> **Flujo principal**:
> 1. Usuario navega al gestor de contenido
> 2. Sistema carga `hotel_content_pages`, `hotel_images`, `system_catalogs`
> 3. Usuario edita descripciones, highlights, amenities
> 4. Usuario sube/elimina imágenes (JPEG/PNG, máx 5MB)
> 5. Sistema actualiza `hotel_content_pages`, `hotel_images`
> 6. Sistema registra en `hotel_content_changes`

**Relaciones**:
- `<<include>>` CU-M03: Validar Imágenes *(abstracto)*

### CU-M03: Validar Imágenes *(abstracto)*
> **Actor**: Sistema  
> **Descripción**: Validar formato (JPEG/PNG) y tamaño (≤5MB)

### CU-M04: Editar Políticas Hoteleras
> **Actor**: Hotel Partner  
> **Flujo principal**:
> 1. Usuario edita check-in/out, cancelación, mascotas, niños
> 2. Sistema valida horarios (HH:MM), min_stay ≥ 1, max_stay ≤ 365
> 3. Sistema guarda en `hotel_policies`
> 4. Sistema registra auditoría

### CU-M05: Gestionar Amenities
> **Actor**: Hotel Partner  
> **Flujo principal**:
> 1. Usuario selecciona amenities del catálogo (`system_catalogs`)
> 2. Sistema actualiza `hotel_content_pages.active_amenities`
> 3. Sistema genera `amenities_catalog` con categorías

### CU-M06: Moderar y Responder Reseñas
> **Actor**: Marketing / Super Admin  
> **Flujo principal**:
> 1. Moderador revisa reseñas pendientes (`reviews`)
> 2. Moderador aprueba o rechaza con motivo
> 3. Si aprobada y necesita respuesta: escribe respuesta pública
> 4. Sistema actualiza `reviews.moderation_status`, `staff_response`
> 5. Sistema actualiza `fact_reviews` (dual-write)

## 3.5 Diagrama de Casos de Uso (Texto)

```
Marketing / Partner
  ├── CU-M01: Editar Nombre Comercial
  ├── CU-M02: Actualizar Contenido
  │   └── <<include>> CU-M03: Validar Imágenes
  ├── CU-M04: Editar Políticas
  ├── CU-M05: Gestionar Amenities
  └── CU-M06: Moderar Reseñas
```

## 3.6 Colecciones MongoDB

| Colección | Tipo | Propósito | CU Relacionados |
|-----------|------|-----------|-----------------|
| `dim_hotels` | Actualización | Nombre, manual_override | CU-M01 |
| `hotel_profile` | Escritura | Datos del hotel para Mi Estancia | CU-M01 |
| `hotel_profile_changes` | Escritura | Registro de cambios de perfil | CU-M01 |
| `hotel_content_pages` | Actualización | Descripciones, amenities | CU-M02, CU-M05 |
| `hotel_images` | Actualización | Galería de imágenes | CU-M02 |
| `hotel_content_changes` | Escritura | Registro de cambios de contenido | CU-M02 |
| `hotel_policies` | Escritura | Políticas del hotel | CU-M04 |
| `system_catalogs` | Lectura | Catálogo de amenities | CU-M05 |
| `reviews` | Actualización | Moderación y respuesta | CU-M06 |
| `fact_reviews` | Actualización | Dual-write analítico | CU-M06 |
| `review_reports` | Escritura | Reportes de reseñas | CU-M06 |
| `room_features` | Escritura | Features de habitación | CU-M05 |
| `hotel_amenities` | Escritura | Amenities por propiedad | CU-M05 |
| `corporate_contracts` | Escritura | Contratos corporativos por hotel | CU-M05 |
| `hotels` | Lectura | Master hotel legacy | CU-M01 |
| `user_activity_logs` | Escritura | Auditoría | Todos |

---

# 4. DEPARTAMENTO: OPERACIONES HOTELERAS

## 4.1 Descripción
Ejecutar la operación diaria del hotel: check-in/out, reservas manuales, gestión de habitaciones, inventario, housekeeping, mantenimiento y recepción.

## 4.2 Secciones / Módulos
- **Reservas management** (`reservations` — confirmar, rechazar, check-in/out)
- **Manual reservations** (`manual-reservations`)
- **Check-ins / Check-outs** (`check-ins`, `check-outs`)
- **Disponibilidad** (`availability`, `partner/availability`)
- **Habitaciones** (`rooms`, `partner/rooms`)
- **Housekeeping** (`housekeeping` — room_status, tasks, cleaning)
- **Mantenimiento** (`housekeeping/maintenance`)
- **Recepción** (`reception`, `shifts`)

## 4.3 Actores
| Actor | Descripción |
|-------|-------------|
| **Recepcionista** | Operación diaria de front desk |
| **Gerente de hotel** | Supervisa operaciones, confirma reservas, programa mantenimiento |
| **Hotel Partner** | Define tipos de habitación, políticas |

## 4.4 Casos de Uso

### CU-O01: Crear Reserva Manual (Walk-in)
> **Actor**: Recepcionista  
> **Flujo principal**:
> 1. Recepcionista ingresa datos del huésped
> 2. Sistema crea `booking_orders` en estado `"confirmed"`
> 3. Sistema descuenta inventario inmediatamente
> 4. Sistema registra en `booking_status_history`
> 5. Sistema crea `manual_reservations`

### CU-O02: Consultar Solicitudes de Reserva
> **Actor**: Gerente  
> **Flujo principal**:
> 1. Gerente consulta reservas en estado `"pending"`
> 2. Sistema muestra listado filtrado por `prop_id`

### CU-O03: Confirmar/Rechazar Solicitud
> **Actor**: Gerente  
> **Flujo principal**:
> 1. Gerente selecciona solicitud pendiente
> 2. Decisión: Confirmar → estado `"confirmed"`, descuenta inventario
> 3. Decisión: Rechazar → estado `"cancelled"`, registra motivo
> 4. Sistema actualiza `booking_status_history`

**Relaciones**:
- `<<extend>>` CU-O02: Consultar Solicitudes

### CU-O04: Completar Check-In
> **Actor**: Recepcionista  
> **Precondición**: Reserva en estado `"confirmed"`  
> **Flujo principal**:
> 1. Recepcionista busca reserva
> 2. Verifica identidad del huésped
> 3. Confirma check-in
> 4. Sistema: `booking_orders.status → "checked_in"`
> 5. Sistema: actualiza `room_status_log` a `"occupied"`
> 6. Sistema: registra en `booking_status_history`

**Relaciones**:
- `<<include>>` CU-O08: Validar Estado de Reserva *(abstracto)*

### CU-O05: Completar Check-Out
> **Actor**: Recepcionista  
> **Precondición**: Reserva en estado `"checked_in"`  
> **Flujo principal**:
> 1. Recepcionista busca reserva
> 2. Verifica cargos adicionales
> 3. Genera factura (CU-B01)
> 4. Registra pago (CU-B02)
> 5. Confirma check-out
> 6. Sistema: `booking_orders.status → "checked_out"`
> 7. Sistema: libera inventario de noches futuras
> 8. Sistema: `room_status_log → "cleaning_needed"`

**Relaciones**:
- `<<include>>` CU-B01: Generar Factura
- `<<include>>` CU-B02: Registrar Pago
- `<<include>>` CU-O08: Validar Estado de Reserva

### CU-O06: Crear Tipo de Habitación
> **Actor**: Hotel Partner  
> **Flujo principal**:
> 1. Partner ingresa nombre, capacidad, descripción
> 2. Sistema valida unicidad por propiedad
> 3. Sistema crea `room_types`
> 4. Sistema crea `hotel_rooms` físicas asociadas

### CU-O07: Actualizar Inventario
> **Actor**: Gerente  
> **Flujo principal**:
> 1. Gerente selecciona tipo de habitación y fecha
> 2. Ingresa nuevo inventario disponible
> 3. Sistema aplica optimistic locking (`version`)
> 4. Sistema actualiza `room_inventory_calendar`

### CU-O08: Validar Estado de Reserva *(abstracto)*
> **Actor**: Sistema  
> **Descripción**: Verificar que la reserva esté en el estado correcto para la operación

### CU-O09: Bloquear Disponibilidad
> **Actor**: Gerente  
> **Flujo principal**:
> 1. Gerente selecciona rango de fechas y tipo
> 2. Ingresa motivo (mantenimiento, evento)
> 3. Sistema crea `blackout_dates`
> 4. Sistema actualiza `room_inventory_calendar`

### CU-O10: Consultar Estado de Habitaciones
> **Actor**: Recepcionista / Gerente  
> **Flujo principal**:
> 1. Usuario abre panel de estado
> 2. Sistema consulta `room_status_log`
> 3. Sistema muestra matriz visual con códigos de colores

### CU-O11: Asignar Tarea de Limpieza
> **Actor**: Gerente / Recepcionista  
> **Flujo principal**:
> 1. Post-check-out: habitación en `"cleaning_needed"`
> 2. Usuario asigna tarea a personal de housekeeping
> 3. Sistema crea `housekeeping_tasks`
> 4. Sistema actualiza `room_status_log → "cleaning_in_progress"`

### CU-O12: Completar Limpieza
> **Actor**: Personal de Housekeeping  
> **Flujo principal**:
> 1. Personal marca inicio de limpieza
> 2. Personal completa limpieza
> 3. Sistema registra tiempo de rotación
> 4. Sistema: `room_status_log → "available"`
> 5. Sistema completa `housekeeping_tasks`

### CU-O13: Programar Mantenimiento
> **Actor**: Gerente  
> **Flujo principal**:
> 1. Gerente selecciona habitación y tipo de mantenimiento
> 2. Ingresa fecha programada y prioridad
> 3. Sistema crea `maintenance_tasks`
> 4. Sistema: `room_status_log → "maintenance"`

### CU-O14: Completar Mantenimiento
> **Actor**: Gerente / Técnico  
> **Flujo principal**:
> 1. Técnico completa tarea de mantenimiento
> 2. Sistema actualiza `maintenance_tasks`
> 3. Sistema: `room_status_log → "available"` o `"cleaning_needed"`

### CU-O15: Gestionar Turnos de Recepción
> **Actor**: Recepcionista / Gerente  
> **Flujo principal**:
> 1. Recepcionista abre turno (`reception_shifts`)
> 2. Sistema registra hora de inicio
> 3. Al finalizar: cierra turno, registra transacciones
> 4. Sistema actualiza `reception_shifts`

### CU-O16: Visualizar Calendario de Recepción
> **Actor**: Recepcionista / Gerente  
> **Descripción**: Ver reservas agrupadas por habitación física en una línea de tiempo visual  
> **Flujo principal**:
> 1. Usuario accede al calendario de recepción
> 2. Sistema consulta `hotel_rooms` (habitaciones físicas activas)
> 3. Sistema consulta `booking_orders` que intersectan el rango de fechas
> 4. Sistema asigna cada reserva a su habitación física (`assigned_rooms`)
> 5. Sistema calcula estado visual: `active` | `upcoming` | `past` | `cancelled`
> 6. Sistema devuelve timeline por habitación con fracciones de check-in/out

## 4.5 Diagrama de Casos de Uso (Texto)

```
Recepcionista
  ├── CU-O01: Crear Reserva Manual
  ├── CU-O04: Check-In
  │   └── <<include>> CU-O08: Validar Estado
  ├── CU-O05: Check-Out
  │   ├── <<include>> CU-B01: Generar Factura
  │   ├── <<include>> CU-B02: Registrar Pago
  │   └── <<include>> CU-O08: Validar Estado
  ├── CU-O10: Consultar Estado Habitaciones
  └── CU-O15: Gestionar Turnos

Gerente
  ├── CU-O02: Consultar Solicitudes
  ├── CU-O03: Confirmar/Rechazar Solicitud
  │   └── <<extend>> CU-O02
  ├── CU-O07: Actualizar Inventario
  ├── CU-O09: Bloquear Disponibilidad
  ├── CU-O11: Asignar Limpieza
  ├── CU-O13: Programar Mantenimiento
  └── CU-O15: Gestionar Turnos

Housekeeping
  ├── CU-O12: Completar Limpieza
  └── CU-O14: Completar Mantenimiento

Partner
  ├── CU-O06: Crear Tipo Habitación
  └── CU-M04: Editar Políticas
```

## 4.6 Flujo de Ciclo de Vida de la Reserva

```
stateDiagram-v2
  [*] --> Pending: CU-C07 Solicitar
  Pending --> Confirmed: CU-O03 Confirmar
  Pending --> Cancelled: CU-C10 Cancelar / Rechazar
  Confirmed --> CheckedIn: CU-O04 Check-In
  Confirmed --> Cancelled: CU-C10 Cancelar
  CheckedIn --> CheckedOut: CU-O05 Check-Out
  CheckedIn --> Cancelled: Excepción gerente
  CheckedOut --> Invoiced: CU-B01 Facturar
  CheckedOut --> [*]
  Cancelled --> [*]
  Invoiced --> [*]
```

## 4.7 Colecciones MongoDB

| Colección | Tipo | Propósito | CU Relacionados |
|-----------|------|-----------|-----------------|
| `booking_orders` | Lectura/Escritura | Estado y datos de reserva | CU-O01, CU-O02, CU-O03, CU-O04, CU-O05 |
| `booking_guests` | Escritura | Datos de huéspedes | CU-O01 |
| `booking_room_guests` | Escritura | Huéspedes por habitación | CU-O04 |
| `booking_status_history` | Escritura | Trazabilidad | Todos los CU de reservas |
| `manual_reservations` | Escritura | Reservas manuales | CU-O01 |
| `room_types` | Escritura | Tipos de habitación | CU-O06 |
| `hotel_rooms` | Escritura | Habitaciones físicas | CU-O06, CU-O10 |
| `room_inventory_calendar` | Escritura | Inventario por fecha | CU-O01, CU-O03, CU-O07, CU-O09 |
| `room_availability_blocks` | Escritura | Bloques de disponibilidad | CU-O09 |
| `blackout_dates` | Escritura | Bloqueos por mantenimiento | CU-O09 |
| `room_status_log` | Escritura | Estado actual de habitaciones | CU-O04, CU-O05, CU-O10, CU-O11, CU-O12, CU-O13, CU-O14 |
| `room_status_history` | Escritura | Historial de cambios de estado | CU-O10, CU-O11, CU-O12 |
| `housekeeping_tasks` | Escritura | Tareas de limpieza | CU-O11, CU-O12 |
| `maintenance_tasks` | Escritura | Tareas de mantenimiento | CU-O13, CU-O14 |
| `reception_shifts` | Escritura | Turnos de recepción | CU-O15 |
| `additional_charges` | Escritura | Cargos adicionales | CU-O05 |
| `user_activity_logs` | Escritura | Auditoría | Todos |

---

# 5. DEPARTAMENTO: FACTURACIÓN, PAGOS Y GASTOS

## 5.1 Descripción
Gestionar facturación de reservas, pagos, folios de huésped, cargos adicionales y gastos operativos del hotel.

## 5.2 Secciones / Módulos
- **Facturas** (`billing/invoices`)
- **Pagos** (`billing/payments`)
- **Folios** (`billing/folios`)
- **Cargos adicionales** (`housekeeping/charges`)
- **Gastos** (`expenses` — invoices, categories, budget)
- **Libro mayor** (`expenses/ledger`)
- **Plan de cuentas** (`expenses/chart_of_accounts`)

## 5.3 Actores
| Actor | Descripción |
|-------|-------------|
| **Recepcionista** | Genera facturas, registra pagos, gestiona folios |
| **Gerente** | Aprueba gastos, consulta reportes financieros |
| **Contador** | Gestiona libro mayor, plan de cuentas |

## 5.4 Casos de Uso

### CU-B01: Generar Factura
> **Actor**: Recepcionista  
> **Precondición**: Reserva en estado `"checked_out"` o `"checked_in"`  
> **Flujo principal**:
> 1. Sistema calcula subtotal (noches × tarifa)
> 2. Sistema suma cargos adicionales (`additional_charges`)
> 3. Sistema aplica impuestos (`tax_rates`)
> 4. Sistema genera número de factura único
> 5. Sistema crea `reservation_invoices`

**Relaciones**:
- `<<include>>` CU-B03: Calcular Impuestos *(abstracto)*

### CU-B02: Registrar Pago
> **Actor**: Recepcionista  
> **Flujo principal**:
> 1. Recepcionista selecciona factura
> 2. Ingresa monto, método (efectivo, tarjeta, transferencia), referencia
> 3. Sistema crea `reservation_payments`
> 4. Sistema actualiza estado de factura
> 5. Si pago completo: marca como `"paid"`

**Relaciones**:
- `<<include>>` CU-B01: Generar Factura *(debe existir una factura para pagar)*

### CU-B03: Calcular Impuestos *(abstracto)*
> **Actor**: Sistema  
> **Descripción**: Aplicar IVA y comisiones según configuración

### CU-B04: Consultar Folio
> **Actor**: Recepcionista / Gerente  
> **Flujo principal**:
> 1. Usuario busca folio por booking_id
> 2. Sistema consulta `guest_folios`
> 3. Sistema muestra postings, totales, balance

### CU-B05: Crear Cargo Adicional
> **Actor**: Recepcionista  
> **Flujo principal**:
> 1. Recepcionista selecciona reserva activa
> 2. Ingresa concepto, monto, cantidad
> 3. Sistema valida reserva en estado confirmed/checked_in
> 4. Sistema crea `additional_charges`
> 5. Sistema actualiza folio

### CU-B06: Crear Gasto (Expense)
> **Actor**: Gerente  
> **Flujo principal**:
> 1. Gerente ingresa proveedor, categoría, monto, descripción
> 2. Sistema crea `expense_invoices`
> 3. Sistema actualiza `expense_categories.spent`
> 4. Si aprobado: impacta `ledger_transactions`

### CU-B07: Consultar Libro Mayor
> **Actor**: Contador / Gerente  
> **Flujo principal**:
> 1. Usuario consulta `ledger_transactions`
> 2. Sistema muestra transacciones por período
> 3. Sistema calcula balance (debe - haber)

### CU-B08: Gestionar Presupuesto
> **Actor**: Gerente  
> **Flujo principal**:
> 1. Gerente define presupuesto por departamento y período
> 2. Sistema crea `expense_budget`
> 3. Sistema calcula remaining = amount - spent
> 4. Alerta si spent > 90% del budget

## 5.5 Diagrama de Casos de Uso (Texto)

```
Recepcionista
  ├── CU-B01: Generar Factura
  │   └── <<include>> CU-B03: Calcular Impuestos
  ├── CU-B02: Registrar Pago
  │   └── <<include>> CU-B01
  └── CU-B05: Crear Cargo Adicional

Gerente
  ├── CU-B04: Consultar Folio
  ├── CU-B06: Crear Gasto
  └── CU-B08: Gestionar Presupuesto

Contador
  └── CU-B07: Consultar Libro Mayor
```

## 5.6 Colecciones MongoDB

| Colección | Tipo | Propósito | CU Relacionados |
|-----------|------|-----------|-----------------|
| `reservation_invoices` | Escritura | Facturas de reserva | CU-B01 |
| `reservation_payments` | Escritura | Pagos registrados | CU-B02 |
| `fact_reservation_invoices` | Escritura | Dual-write analítico | CU-B01 |
| `fact_reservation_payments` | Escritura | Dual-write analítico | CU-B02 |
| `guest_folios` | Escritura | Folios de huésped | CU-B04, CU-B05 |
| `additional_charges` | Escritura | Cargos extras | CU-B05 |
| `expense_invoices` | Escritura | Gastos operativos | CU-B06 |
| `expense_categories` | Escritura | Categorías de gasto | CU-B06 |
| `expense_budget` | Escritura | Presupuestos | CU-B08 |
| `ledger_transactions` | Escritura | Libro mayor | CU-B06, CU-B07 |
| `chart_of_accounts` | Escritura | Plan de cuentas | CU-B07 |
| `tax_rates` | Lectura | Tasas de impuesto | CU-B03 |
| `commission_rates` | Lectura | Comisiones | CU-B03 |
| `user_activity_logs` | Escritura | Auditoría | Todos |

---

# 6. DEPARTAMENTO: RECURSOS HUMANOS

## 6.1 Descripción
Gestionar empleados, departamentos, turnos y documentación del personal hotelero.

## 6.2 Secciones / Módulos
- **Empleados** (`hr/employees`)
- **Departamentos** (`hr/departments`)
- **Turnos** (`hr/shifts`)
- **Documentos** (`hr/documents`)
- **Portal del empleado** (`hr/portal`)

## 6.3 Actores
| Actor | Descripción |
|-------|-------------|
| **Gerente HR** | Gestiona empleados, departamentos, turnos |
| **Empleado** | Consulta su portal, registra check-in/out de turno |

## 6.4 Casos de Uso

### CU-HR01: Crear Empleado
> **Actor**: Gerente HR  
> **Flujo principal**:
> 1. Gerente ingresa datos personales, documento, cargo, salario
> 2. Sistema valida unicidad de `id_document`
> 3. Sistema crea `employees`

### CU-HR02: Gestionar Departamentos
> **Actor**: Gerente HR  
> **Flujo principal**:
> 1. Gerente crea/edita departamentos
> 2. Sistema actualiza `employee_departments`
> 3. Sistema recalcula `head_count`

### CU-HR03: Programar Turno
> **Actor**: Gerente HR  
> **Flujo principal**:
> 1. Gerente selecciona empleado y fecha
> 2. Ingresa horario, área, tipo de turno
> 3. Sistema crea `employee_shifts`

### CU-HR04: Registrar Check-In de Turno
> **Actor**: Empleado  
> **Flujo principal**:
> 1. Empleado accede a portal
> 2. Registra llegada al turno
> 3. Sistema: `employee_shifts.actual_check_in = now()`
> 4. Sistema: `status → "active"`

### CU-HR05: Registrar Check-Out de Turno
> **Actor**: Empleado  
> **Flujo principal**:
> 1. Empleado registra salida del turno
> 2. Sistema: `employee_shifts.actual_check_out = now()`
> 3. Sistema: `status → "completed"`
> 4. Sistema calcula horas trabajadas

## 6.5 Colecciones MongoDB

| Colección | Tipo | Propósito | CU Relacionados |
|-----------|------|-----------|-----------------|
| `employees` | Escritura | Datos de empleados | CU-HR01 |
| `employee_departments` | Escritura | Departamentos | CU-HR02 |
| `employee_documents` | Escritura | Documentos de empleados | CU-HR01 |
| `employee_shifts` | Escritura | Turnos programados | CU-HR03, CU-HR04, CU-HR05 |
| `employee_permissions` | Escritura | Permisos transferidos del empleado | CU-HR01 |
| `user_activity_logs` | Escritura | Auditoría | Todos |

---

# 7. DEPARTAMENTO: ADMINISTRACIÓN DEL SISTEMA

## 7.1 Descripción
Administrar usuarios, roles, permisos, autenticación, configuración global del sistema y auditoría.

## 7.2 Secciones / Módulos
- **Autenticación** (`auth` — login, register, password, sessions)
- **Usuarios** (`users`, `admin/users`, `ownership`)
- **Roles y permisos** (`admin/roles`, `admin/permissions`)
- **Configuración** (`settings`, `global_settings`)
- **Notificaciones** (`notifications`)
- **Seguridad** (`security` — JWT, sesiones, contratos)

## 7.3 Actores
| Actor | Descripción |
|-------|-------------|
| **Super Admin** | Administra usuarios, roles, permisos, monitorea servicios |
| **Admin de Sistema** | Gestiona configuración, usuarios |
| **Todos los usuarios** | Login, logout, perfil, contraseña |

## 7.4 Casos de Uso

### CU-A01: Iniciar Sesión (JWT)
> **Actor**: Todos los usuarios  
> **Flujo principal**:
> 1. Usuario ingresa email + contraseña
> 2. Sistema busca en `users`
> 3. Sistema verifica bcrypt
> 4. Sistema verifica `is_active = true`
> 5. Sistema invalida sesión previa
> 6. Sistema genera token (48 bytes)
> 7. Sistema almacena hash SHA-256 en `user_sessions`
> 8. Sistema establece cookie httponly, samesite=lax
> 9. Sistema registra en `user_activity_logs`

### CU-A02: Cerrar Sesión
> **Actor**: Todos los usuarios  
> **Flujo principal**:
> 1. Usuario hace clic en "Cerrar sesión"
> 2. Sistema extrae token de cookie
> 3. Sistema elimina de `user_sessions`
> 4. Sistema elimina cookie (max-age=0)
> 5. Sistema registra en `user_activity_logs`

### CU-A03: Cambiar Contraseña
> **Actor**: Todos los usuarios  
> **Flujo principal**:
> 1. Usuario ingresa contraseña actual y nueva
> 2. Sistema verifica actual con bcrypt
> 3. Sistema valida nueva ≥ 8 caracteres
> 4. Sistema hashea nueva con bcrypt
> 5. Sistema invalida todas las sesiones excepto actual
> 6. Sistema registra en `user_activity_logs`

### CU-A04: Actualizar Perfil
> **Actor**: Todos los usuarios  
> **Flujo principal**:
> 1. Usuario modifica datos (display_name, email, teléfono)
> 2. Sistema valida unicidad de email
> 3. Sistema actualiza `users`
> 4. Sistema registra en `user_activity_logs`

### CU-A05: Gestionar Usuarios
> **Actor**: Super Admin  
> **Flujo principal**:
> 1. Super admin crea/edita/desactiva usuarios
> 2. Asigna roles y hoteles
> 3. Sistema actualiza `users`, `role_permissions`

### CU-A06: Gestionar Roles y Permisos
> **Actor**: Super Admin  
> **Flujo principal**:
> 1. Super admin define/edita roles
> 2. Asigna permisos granulares
> 3. Sistema actualiza `roles`, `permissions`, `role_permissions`

### CU-A07: Configurar Sistema Global
> **Actor**: Super Admin  
> **Flujo principal**:
> 1. Admin edita comisiones, impuestos, configuraciones
> 2. Sistema actualiza `system_config`, `commission_rates`, `tax_rates`

## 7.5 Colecciones MongoDB

| Colección | Tipo | Propósito | CU Relacionados |
|-----------|------|-----------|-----------------|
| `users` | Lectura/Escritura | Autenticación, perfil | CU-A01, CU-A04, CU-A05 |
| `user_sessions` | Escritura | Sesiones activas | CU-A01, CU-A02 |
| `user_activity_logs` | Escritura | Auditoría | Todos |
| `roles` | Escritura | Definición de roles | CU-A06 |
| `permissions` | Escritura | Definición de permisos | CU-A06 |
| `role_permissions` | Escritura | Asignación permisos→roles | CU-A06 |
| `refresh_tokens` | Escritura | Tokens de refresco | CU-A01 |
| `password_recovery_tokens` | Escritura | Recuperación de contraseña | CU-A03 |
| `email_verification_tokens` | Escritura | Verificación de email | CU-A01 |
| `two_factor_codes` | Escritura | Códigos 2FA | CU-A01 |
| `user_2fa` | Escritura | Configuración 2FA | CU-A01 |
| `pending_registrations` | Escritura | Registros pendientes | CU-A01 |
| `system_config` | Escritura | Configuración global | CU-A07 |
| `commission_rates` | Escritura | Comisiones por hotel | CU-A07 |
| `tax_rates` | Escritura | Tasas de impuesto | CU-A07 |
| `notification_log` | Escritura | Log de notificaciones | CU-A07 |

---

# 8. DEPARTAMENTO: DATOS, ANALÍTICA Y GEOLOCALIZACIÓN

## 8.1 Descripción
Ejecutar pipelines ETL, monitorear calidad de datos, generar reportes, dashboards y gestionar catálogos geoespaciales.

## 8.2 Secciones / Módulos
- **Dashboard / KPIs** (`kpi`, `features/dashboard`)
- **Reportes** (`reports` — PDF, Excel)
- **Auditoría** (`audit`, `features/audit`)
- **Calidad de datos** (`features/quality`)
- **ETL / Pipeline** (`features/etl_status`)
- **Mapa mundial** (`map`)
- **Catálogo geográfico** (`geo_catalog`)
- **Colecciones** (`features/collections`)

## 8.3 Actores
| Actor | Descripción |
|-------|-------------|
| **Auditor de Datos** | Ejecuta ETL, valida calidad, edita metadata |
| **Gerente / Revenue** | Consulta dashboards y reportes |
| **Marketing** | Edita override de nombres, visualiza mapa |

## 8.4 Casos de Uso

### CU-D01: Consultar Dashboard Ejecutivo
> **Actor**: Gerente / Revenue / Admin  
> **Flujo principal**:
> 1. Usuario accede al dashboard
> 2. Sistema consulta `kpi_summary`
> 3. Sistema calcula métricas desde `fact_hotel_reservations`
> 4. Sistema muestra: eventos, reservas, revenue, precio medio, calidad

### CU-D02: Consultar Reporte de Calidad
> **Actor**: Auditor de Datos  
> **Flujo principal**:
> 1. Auditor consulta última ejecución ETL
> 2. Sistema carga `data_quality_reports`
> 3. Sistema muestra: procesados, aceptados, rechazados, completitud

### CU-D03: Ejecutar Pipeline ETL
> **Actor**: Sistema (Airflow) / Auditor  
> **Flujo principal**:
> 1. Airflow DAG lee CSV desde `data/raw/`
> 2. Valida cada registro
> 3. Carga aprobados a colecciones maestras
> 4. Almacena rechazados en `rejected_records`
> 5. Genera `data_quality_reports`
> 6. Actualiza `fact_hotel_reservations`, dimensiones

### CU-D04: Editar Metadata de Destino
> **Actor**: Auditor / Marketing  
> **Flujo principal**:
> 1. Usuario edita nombre visible, coordenadas, país, ciudad
> 2. Sistema valida coordenadas (-90 a 90, -180 a 180)
> 3. Sistema actualiza `dim_destinations`
> 4. Sistema conserva `original_name` para trazabilidad

### CU-D05: Visualizar Mapa Mundial
> **Actor**: Todos los usuarios  
> **Flujo principal**:
> 1. Usuario abre mapa mundial
> 2. Sistema consulta `dim_destinations` con coordenadas
> 3. Sistema consulta `dim_hotels` asociados
> 4. Frontend (Leaflet.js) renderiza marcadores coloreados por precio

### CU-D06: Exportar Reporte
> **Actor**: Gerente / Auditor  
> **Flujo principal**:
> 1. Usuario selecciona tipo de reporte y rango de fechas
> 2. Sistema genera PDF (`reports/pdf`) o Excel (`reports/xlsx`)
> 3. Sistema descarga archivo

## 8.5 Colecciones MongoDB

| Colección | Tipo | Propósito | CU Relacionados |
|-----------|------|-----------|-----------------|
| `fact_hotel_reservations` | Lectura | Datos analíticos | CU-D01 |
| `fact_hotel_events` | Lectura | Eventos alternativos | CU-D01 |
| `dim_hotels` | Lectura | Hoteles para reportes | CU-D01, CU-D05 |
| `dim_destinations` | Lectura/Escritura | Destinos geográficos | CU-D04, CU-D05 |
| `dim_visitor_countries` | Lectura | Países visitantes | CU-D01 |
| `dim_sites` | Lectura | Canales de venta | CU-D01 |
| `dim_dates` | Lectura | Dimensiones temporales | CU-D01 |
| `dim_promotions` | Lectura | Promociones | CU-D01 |
| `dim_click_status` | Lectura | Estado de clicks | CU-D01 |
| `dim_reservation_status` | Lectura | Estado de reservas | CU-D01 |
| `dim_occupancy_profile` | Lectura | Perfiles de ocupación | CU-D01 |
| `dim_stay_length_category` | Lectura | Categorías de estancia | CU-D01 |
| `dim_booking_window_category` | Lectura | Categorías de booking | CU-D01 |
| `dim_price_category` | Lectura | Categorías de precio | CU-D01 |
| `etl_executions` | Escritura | Ejecuciones ETL | CU-D02, CU-D03 |
| `data_quality_reports` | Escritura | Reportes de calidad | CU-D02, CU-D03 |
| `rejected_records` | Escritura | Registros rechazados | CU-D02, CU-D03 |
| `search_logs` | Escritura | Logs de búsqueda | CU-D02 |
| `kpi_summary` | Escritura | Cache de KPIs | CU-D01 |
| `geo_catalog` | Escritura | Catálogo geográfico | CU-D04 |
| `click_events` | Escritura | Eventos de click | CU-D01 |
| `user_activity_logs` | Escritura | Auditoría | Todos |

---

# 9. DEPARTAMENTO: SERVICIOS AL HUÉSPED (IN-STAY)

## 9.1 Descripción
Proveer una experiencia digital durante la estancia del huésped: portal Mi Estancia, chat con recepción, solicitudes de servicio, DND y objetos perdidos.

## 9.2 Secciones / Módulos
- **Mi Estancia** (`instay/guest` — portal, chat, requests, DND)
- **Staff Inbox** (`instay/staff` — requests, conversations)
- **Catálogo de amenities guest** (`amenities/guest`)
- **Objetos perdidos** (`lost_and_found`)

## 9.3 Actores
| Actor | Descripción |
|-------|-------------|
| **Huésped** | Usuario con reserva en estancia activa (checked_in) |
| **Recepcionista / Staff** | Atiende solicitudes y chat del huésped |

## 9.4 Casos de Uso

### CU-I01: Acceder al Portal Mi Estancia
> **Actor**: Huésped  
> **Precondición**: Reserva en estado `"checked_in"`  
> **Flujo principal**:
> 1. Huésped escanea QR o accede con JWT
> 2. Sistema crea/valida `stay_sessions`
> 3. Sistema carga compendio: `hotel_profile`, `hotel_policies`, `hotel_amenities`
> 4. Sistema carga cargos: `additional_charges`
> 5. Sistema carga folio: `guest_folios`
> 6. Huésped visualiza portal con información del hotel

### CU-I02: Enviar Mensaje por Chat
> **Actor**: Huésped  
> **Flujo principal**:
> 1. Huésped escribe mensaje en chat
> 2. Sistema crea `stay_messages` (sender: "guest")
> 3. Sistema notifica a staff (`notification_log`)
> 4. Staff responde (sender: "staff")

### CU-I03: Crear Solicitud de Servicio
> **Actor**: Huésped  
> **Flujo principal**:
> 1. Huésped selecciona tipo: room_service, housekeeping, maintenance, towels, amenities, minibar, laundry, wake_up_call, late_checkout, extra_bed, spa, restaurant, extend_stay
> 2. Huésped opcionalmente agrega descripción
> 3. Sistema crea `stay_service_requests`
> 4. Sistema notifica a staff

### CU-I04: Activar/Desactivar DND
> **Actor**: Huésped  
> **Flujo principal**:
> 1. Huésped hace clic en "No Molestar"
> 2. Sistema lee estado actual desde `room_status_log`
> 3. Sistema invierte valor de `dnd`
> 4. Sistema actualiza `room_status_log.dnd_updated_at`

### CU-I05: Atender Solicitudes (Staff)
> **Actor**: Recepcionista / Staff  
> **Flujo principal**:
> 1. Staff consulta inbox de solicitudes (`stay_service_requests`)
> 2. Staff actualiza estado: pending → in_progress → completed
> 3. Staff puede responder al huésped
> 4. Sistema notifica al huésped

### CU-I06: Gestionar Objetos Perdidos
> **Actor**: Recepcionista / Gerente  
> **Flujo principal**:
> 1. Staff registra objeto encontrado (`lost_and_found`)
> 2. Staff actualiza estado: found → claimed / disposed
> 3. Huésped puede consultar desde portal

## 9.5 Diagrama de Casos de Uso (Texto)

```
Huésped
  ├── CU-I01: Acceder Portal Mi Estancia
  ├── CU-I02: Enviar Mensaje Chat
  ├── CU-I03: Crear Solicitud Servicio
  └── CU-I04: Activar/Desactivar DND

Staff
  ├── CU-I02: Responder Mensaje Chat
  ├── CU-I05: Atender Solicitudes
  └── CU-I06: Gestionar Objetos Perdidos
```

## 9.6 Colecciones MongoDB

| Colección | Tipo | Propósito | CU Relacionados |
|-----------|------|-----------|-----------------|
| `stay_sessions` | Escritura | Sesiones del huésped | CU-I01 |
| `stay_messages` | Escritura | Chat entre huésped y staff | CU-I02 |
| `stay_service_requests` | Escritura | Solicitudes de servicio | CU-I03, CU-I05 |
| `room_status_log` | Lectura/Escritura | Estado DND de habitación | CU-I04 |
| `hotel_profile` | Lectura | Datos del hotel para compendio | CU-I01 |
| `hotel_policies` | Lectura | Políticas para compendio | CU-I01 |
| `hotel_amenities` | Lectura | Amenities para compendio | CU-I01 |
| `additional_charges` | Lectura | Cargos del huésped | CU-I01 |
| `guest_folios` | Lectura | Folio y balance | CU-I01 |
| `lost_and_found` | Escritura | Objetos perdidos | CU-I06 |
| `notification_log` | Escritura | Notificaciones a staff | CU-I02, CU-I03, CU-I05 |
| `booking_orders` | Lectura | Datos de la reserva | CU-I01 |

---

# APÉNDICE A: Mapa Completo de Relaciones <<include>> y <<extend>>

## Relaciones <<include>> (inclusión obligatoria)

| CU Base | CU Incluido | Justificación |
|---------|-------------|---------------|
| CU-C01: Buscar Hoteles | CU-C02: Calcular Tarifa | Cada resultado necesita su precio |
| CU-C01: Buscar Hoteles | CU-C03: Validar Disponibilidad | Solo muestra hoteles con disponibilidad |
| CU-C04: Filtrar/Comparar | CU-C02: Calcular Tarifa | La comparación necesita precios |
| CU-C05: Ver Detalle | CU-C06: Consultar Reseñas | Las reseñas son parte del detalle |
| CU-C07: Solicitar Reserva | CU-C02: Calcular Tarifa | Debe calcular total antes de confirmar |
| CU-C07: Solicitar Reserva | CU-C03: Validar Disponibilidad | Debe verificar stock antes de crear |
| CU-C07: Solicitar Reserva | CU-C08: Validar Autenticación | Requiere JWT |
| CU-R02: Configurar Tarifa | CU-R01: Crear Plan | Necesita un plan existente |
| CU-B01: Generar Factura | CU-B03: Calcular Impuestos | Toda factura incluye impuestos |
| CU-B02: Registrar Pago | CU-B01: Generar Factura | Necesita factura para pagar |
| CU-O04: Check-In | CU-O08: Validar Estado | Debe validar estado previo |
| CU-O05: Check-Out | CU-B01: Generar Factura | Check-out genera factura |
| CU-O05: Check-Out | CU-B02: Registrar Pago | Check-out registra pago |
| CU-O05: Check-Out | CU-O08: Validar Estado | Debe validar estado previo |
| CU-M02: Actualizar Contenido | CU-M03: Validar Imágenes | Subida incluye validación |

## Relaciones <<extend>> (extensión condicional)

| CU Base | CU Extensor | Condición |
|---------|-------------|-----------|
| CU-C01: Buscar Hoteles | CU-C04: Filtrar/Comparar | Elige aplicar filtros |
| CU-C09: Mis Reservas | CU-C10: Cancelar Reserva | Elige cancelar |
| CU-C07: Solicitar Reserva | CU-R04: Aplicar Cupón | Ingresa código de cupón |
| CU-O02: Consultar Solicitudes | CU-O03: Confirmar/Rechazar | Gerente actúa sobre solicitud |

---

# APÉNDICE B: Resumen de Colecciones MongoDB por Departamento

| Departamento | Colecciones | Total |
|-------------|-------------|-------|
| 1. Comercial / Experiencia Cliente | dim_hotels, dim_destinations, dim_visitor_countries, room_types, room_inventory_calendar, hotel_rate_calendar, hotel_images, hotel_content_pages, hotel_policies, hotel_amenities, booking_orders, booking_guests, booking_status_history, reviews, fact_reviews, user_activity_logs, search_logs, click_events | 18 |
| 2. Revenue Management | rate_plans, rate_rules, hotel_rate_calendar, promotion_campaigns, coupon_codes, fact_hotel_reservations, user_activity_logs | 7 |
| 3. Marketing / Partner | dim_hotels, hotel_profile, hotel_profile_changes, hotel_content_pages, hotel_images, hotel_content_changes, hotel_policies, system_catalogs, reviews, fact_reviews, review_reports, room_features, hotel_amenities, corporate_contracts, hotels, user_activity_logs | 16 |
| 4. Operaciones Hoteleras | booking_orders, booking_guests, booking_room_guests, booking_status_history, manual_reservations, room_types, hotel_rooms, room_inventory_calendar, room_availability_blocks, blackout_dates, room_status_log, room_status_history, housekeeping_tasks, maintenance_tasks, reception_shifts, additional_charges, hotel_booking_context, user_activity_logs | 18 |
| 5. Facturación / Gastos | reservation_invoices, reservation_payments, fact_reservation_invoices, fact_reservation_payments, guest_folios, additional_charges, expense_invoices, expense_categories, expense_budget, ledger_transactions, chart_of_accounts, tax_rates, commission_rates, hotel_booking_context, user_activity_logs | 15 |
| 6. Recursos Humanos | employees, employee_departments, employee_documents, employee_shifts, employee_permissions, user_activity_logs | 6 |
| 7. Administración | users, user_sessions, user_activity_logs, roles, permissions, role_permissions, refresh_tokens, password_recovery_tokens, email_verification_tokens, two_factor_codes, user_2fa, pending_registrations, system_config, commission_rates, tax_rates, notification_log | 16 |
| 8. Datos / Analítica | fact_hotel_reservations, fact_hotel_events, dim_hotels, dim_destinations, dim_visitor_countries, dim_sites, dim_dates, dim_promotions, dim_click_status, dim_reservation_status, dim_occupancy_profile, dim_stay_length_category, dim_booking_window_category, dim_price_category, etl_executions, data_quality_reports, rejected_records, search_logs, kpi_summary, geo_catalog, click_events, user_activity_logs | 22 |
| 9. Servicios al Huésped | stay_sessions, stay_messages, stay_service_requests, room_status_log, hotel_profile, hotel_policies, hotel_amenities, additional_charges, guest_folios, lost_and_found, notification_log, booking_orders | 12 |

---

# APÉNDICE C: Glosario de Abreviaturas

| Abreviatura | Significado |
|-------------|-------------|
| CU | Caso de Uso |
| JWT | JSON Web Token |
| DND | Do Not Disturb (No Molestar) |
| ETL | Extract, Transform, Load |
| ADR | Average Daily Rate |
| RevPAR | Revenue Per Available Room |
| HR | Human Resources (Recursos Humanos) |
| KPI | Key Performance Indicator |
| TTL | Time To Live |
| ROH | Run Of House |

---

---

# APÉNDICE D: Sub-paquetes por Departamento

Basado en el análisis de la estructura real del proyecto (backend FastAPI + frontend Angular),
se proponen los siguientes sub-paquetes para departamentos con alta granularidad de casos de uso.

---

## D.1 Departamento 1: Comercial / Experiencia Cliente

| Sub-paquete | Casos de Uso | Backend | Frontend | Colecciones |
|-------------|-------------|---------|----------|-------------|
| **busqueda** | CU-C01, CU-C02, CU-C03, CU-C04 | `hotels/service` | `hotel-search`, `hotel-compare` | `dim_hotels`, `dim_destinations`, `dim_visitor_countries`, `room_inventory_calendar`, `hotel_rate_calendar`, `click_events`, `search_logs` |
| **detalle** | CU-C05, CU-C06 | `hotels/service/detail` | `hotel-detail` | `hotel_images`, `hotel_content_pages`, `hotel_policies`, `hotel_amenities`, `room_types` |
| **reservas-cliente** | CU-C07, CU-C08, CU-C09, CU-C10 | `reservations/routes/reservations` | `reservations` | `booking_orders`, `booking_guests`, `booking_status_history` |
| **resenias-cliente** | CU-C11 | `reviews/service` | `reviews` | `reviews`, `fact_reviews` |

---

## D.2 Departamento 3: Marketing Hotelero / Partner

> ⚠️ El backend ya implementa esta estructura. Solo se documenta.

| Sub-paquete | Casos de Uso | Backend | Frontend | Colecciones |
|-------------|-------------|---------|----------|-------------|
| **propiedades** | CU-M01 | `partner/services/properties` | `properties` | `dim_hotels`, `hotel_profile`, `hotel_profile_changes`, `hotels` |
| **contenido** | CU-M02, CU-M03 | `partner/services/content` | `properties` | `hotel_content_pages`, `hotel_images`, `hotel_content_changes`, `system_catalogs` |
| **politicas** | CU-M04 | `partner/routes` | `policies` | `hotel_policies` |
| **amenities** | CU-M05 | `partner/services` | `amenities` | `hotel_amenities`, `room_features`, `system_catalogs`, `corporate_contracts` |
| **resenias-mod** | CU-M06 | `reviews/service` | `reviews` | `reviews`, `fact_reviews`, `review_reports` |

---

## D.3 Departamento 4: Operaciones Hoteleras

> 🔴 **El más crítico**: 16 CUs, 18 colecciones, 3 módulos backend, 9 features frontend.
> El backend ya tiene sub-estructura (`_checkinout/`, `lifecycle/create/`, `management_impl/`) que el documento debe reflejar.

| Sub-paquete | Casos de Uso | Backend | Frontend | Colecciones |
|-------------|-------------|---------|----------|-------------|
| **reservas-mgmt** | CU-O01, CU-O02, CU-O03, CU-O08 | `reservations/routes/management` | `management`, `manual-reservations` | `booking_orders`, `booking_guests`, `booking_status_history`, `manual_reservations` |
| **checkin-checkout** | CU-O04, CU-O05 | `reservations/service/_checkinout` | `check-ins`, `check-outs` | `booking_orders`, `booking_room_guests`, `room_status_log`, `additional_charges` |
| **habitaciones** | CU-O06, CU-O07, CU-O09, CU-O10, CU-O16 | `reservations/service/lifecycle`, `partner/services/rooms` | `availability`, `rooms` | `room_types`, `hotel_rooms`, `room_inventory_calendar`, `room_availability_blocks`, `blackout_dates`, `room_status_log`, `hotel_booking_context` |
| **housekeeping** | CU-O11, CU-O12 | `housekeeping/service/lifecycle` (cleaning) | `housekeeping` | `room_status_log`, `room_status_history`, `housekeeping_tasks` |
| **mantenimiento** | CU-O13, CU-O14 | `housekeeping/service/lifecycle` (maintenance) | `housekeeping` | `room_status_log`, `maintenance_tasks` |
| **recepcion** | CU-O15 | `reception` | `reception`, `shifts` | `reception_shifts` |

---

## D.4 Departamento 5: Facturación, Pagos y Gastos

| Sub-paquete | Casos de Uso | Backend | Frontend | Colecciones |
|-------------|-------------|---------|----------|-------------|
| **facturas-pagos** | CU-B01, CU-B02, CU-B03, CU-B04 | `billing/service/lifecycle` | `billing` | `reservation_invoices`, `reservation_payments`, `fact_reservation_invoices`, `fact_reservation_payments`, `guest_folios`, `tax_rates`, `commission_rates`, `hotel_booking_context` |
| **cargos** | CU-B05 | `housekeeping/service/lifecycle/charges` | — | `additional_charges`, `guest_folios` |
| **gastos** | CU-B06, CU-B07, CU-B08 | `expenses` | `expenses` | `expense_invoices`, `expense_categories`, `expense_budget`, `ledger_transactions`, `chart_of_accounts` |

---

## D.5 Departamento 7: Administración del Sistema

| Sub-paquete | Casos de Uso | Backend | Frontend | Colecciones |
|-------------|-------------|---------|----------|-------------|
| **auth** | CU-A01, CU-A02, CU-A03 | `auth`, `account` | `account` | `users`, `user_sessions`, `refresh_tokens`, `password_recovery_tokens`, `email_verification_tokens`, `two_factor_codes`, `user_2fa`, `pending_registrations` |
| **usuarios-roles** | CU-A04, CU-A05, CU-A06 | `users`, `admin` | `admin`, `system-admin`, `ownership` | `users`, `roles`, `permissions`, `role_permissions`, `user_activity_logs` |
| **configuracion** | CU-A07 | `settings`, `global_settings` | `settings` | `system_config`, `commission_rates`, `tax_rates`, `notification_log` |

---

## D.6 Departamento 8: Datos, Analítica y Geolocalización

| Sub-paquete | Casos de Uso | Backend | Frontend | Colecciones |
|-------------|-------------|---------|----------|-------------|
| **etl-calidad** | CU-D02, CU-D03 | `audit` | — | `etl_executions`, `data_quality_reports`, `rejected_records`, `search_logs` |
| **dashboard** | CU-D01 | `kpi` | — | `fact_hotel_reservations`, `fact_hotel_events`, `kpi_summary`, `dim_hotels` (+ 12 dimensiones), `click_events` |
| **geo** | CU-D04, CU-D05 | `geo_catalog`, `map` | `geo-catalog`, `map` | `dim_destinations`, `dim_hotels`, `geo_catalog` |
| **reportes** | CU-D06 | `reports` | — | `fact_hotel_reservations`, `kpi_summary` |

---

## D.7 Departamentos sin sub-paquetes

Estos departamentos son lo suficientemente pequeños y cohesivos como para no requerir sub-paquetes:

| # | Departamento | CUs | Justificación |
|---|-------------|-----|---------------|
| 2 | Revenue Management | 5 | Dominio único: tarifas + promociones + reportes revenue |
| 6 | Recursos Humanos | 5 | 6 colecciones, todas giran en torno a `employees` |
| 9 | Servicios al Huésped (In-Stay) | 6 | Ya dividido implícitamente: guest portal (`instay`) + staff inbox + `lost_and_found` |

---

## D.8 Resumen Visual de Sub-paquetes

```
┌─────────────────────────────────────────────────────┐
│                 HOTELDATA HUB                        │
│              9 Departamentos → 25 Sub-paquetes        │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1. COMERCIAL                                        │
│     ├── busqueda (C01-C04)                           │
│     ├── detalle (C05-C06)                            │
│     ├── reservas-cliente (C07-C10)                   │
│     └── resenias-cliente (C11)                       │
│                                                      │
│  2. REVENUE (sin sub-paquetes)                       │
│                                                      │
│  3. MARKETING / PARTNER                              │
│     ├── propiedades (M01)                            │
│     ├── contenido (M02-M03)                          │
│     ├── politicas (M04)                              │
│     ├── amenities (M05)                              │
│     └── resenias-mod (M06)                           │
│                                                      │
│  4. OPERACIONES HOTELERAS                            │
│     ├── reservas-mgmt (O01-O03, O08)                 │
│     ├── checkin-checkout (O04-O05)                   │
│     ├── habitaciones (O06-O07, O09-O10, O16)         │
│     ├── housekeeping (O11-O12)                       │
│     ├── mantenimiento (O13-O14)                      │
│     └── recepcion (O15)                              │
│                                                      │
│  5. FACTURACIÓN                                      │
│     ├── facturas-pagos (B01-B04)                     │
│     ├── cargos (B05)                                 │
│     └── gastos (B06-B08)                             │
│                                                      │
│  6. RRHH (sin sub-paquetes)                          │
│                                                      │
│  7. ADMINISTRACIÓN                                   │
│     ├── auth (A01-A03)                               │
│     ├── usuarios-roles (A04-A06)                     │
│     └── configuracion (A07)                          │
│                                                      │
│  8. ANALÍTICA                                        │
│     ├── etl-calidad (D02-D03)                        │
│     ├── dashboard (D01)                              │
│     ├── geo (D04-D05)                                │
│     └── reportes (D06)                               │
│                                                      │
│  9. IN-STAY (sin sub-paquetes)                       │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

*Fin del documento — HotelData: 9 Departamentos, 40+ Casos de Uso, 110 Colecciones MongoDB, 25 Sub-paquetes*
