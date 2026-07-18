# HotelData — Catálogo Completo de Casos de Uso

**Documento**: Referencia de Casos de Uso  
**Sistema**: HotelData — Plataforma de gestión hotelera y analítica  
**Versión**: 1.0 | **Fecha**: 2026-07-05  
**Base**: Backend FastAPI + Frontend Angular + MongoDB  
**CUs totales**: 45 | **Departamentos**: 9 | **Sub-paquetes**: 25

---

## Índice Rápido de Casos de Uso

| ID | Nombre | Depto | Sub-paquete | Actor | Tipo |
|----|--------|-------|-------------|-------|------|
| CU-C01 | Buscar Hoteles | 1. Comercial | busqueda | Cliente | Concreto |
| CU-C02 | Calcular Tarifa en Tiempo Real | 1. Comercial | busqueda | Sistema | Abstracto |
| CU-C03 | Validar Disponibilidad | 1. Comercial | busqueda | Sistema | Abstracto |
| CU-C04 | Filtrar y Comparar Hoteles | 1. Comercial | busqueda | Cliente | Concreto |
| CU-C05 | Ver Detalle de Hotel | 1. Comercial | detalle | Cliente | Concreto |
| CU-C06 | Consultar Reseñas Públicas | 1. Comercial | detalle | Sistema | Abstracto |
| CU-C07 | Solicitar Reserva | 1. Comercial | reservas-cliente | Cliente | Concreto |
| CU-C08 | Validar Cliente Autenticado | 1. Comercial | reservas-cliente | Sistema | Abstracto |
| CU-C09 | Consultar Mis Reservas | 1. Comercial | reservas-cliente | Cliente | Concreto |
| CU-C10 | Cancelar Reserva | 1. Comercial | reservas-cliente | Cliente | Concreto |
| CU-C11 | Registrar Reseña | 1. Comercial | resenias-cliente | Cliente | Concreto |
| CU-R01 | Crear Plan Tarifario | 2. Revenue | — | Revenue Manager | Concreto |
| CU-R02 | Configurar Tarifa por Fecha | 2. Revenue | — | Revenue Manager | Concreto |
| CU-R03 | Crear Promoción | 2. Revenue | — | Revenue Manager | Concreto |
| CU-R04 | Aplicar Cupón en Reserva | 2. Revenue | — | Cliente | Extensor |
| CU-R05 | Consultar Reportes de Revenue | 2. Revenue | — | Revenue Manager | Concreto |
| CU-M01 | Editar Nombre Comercial del Hotel | 3. Marketing | propiedades | Marketing / Partner | Concreto |
| CU-M02 | Actualizar Contenido del Hotel | 3. Marketing | contenido | Marketing / Partner | Concreto |
| CU-M03 | Validar Imágenes | 3. Marketing | contenido | Sistema | Abstracto |
| CU-M04 | Editar Políticas Hoteleras | 3. Marketing | politicas | Hotel Partner | Concreto |
| CU-M05 | Gestionar Amenities | 3. Marketing | amenities | Hotel Partner | Concreto |
| CU-M06 | Moderar y Responder Reseñas | 3. Marketing | resenias-mod | Marketing / Admin | Concreto |
| CU-O01 | Crear Reserva Manual (Walk-in) | 4. Operaciones | reservas-mgmt | Recepcionista | Concreto |
| CU-O02 | Consultar Solicitudes de Reserva | 4. Operaciones | reservas-mgmt | Gerente | Concreto |
| CU-O03 | Confirmar/Rechazar Solicitud | 4. Operaciones | reservas-mgmt | Gerente | Concreto |
| CU-O04 | Completar Check-In | 4. Operaciones | checkin-checkout | Recepcionista | Concreto |
| CU-O05 | Completar Check-Out | 4. Operaciones | checkin-checkout | Recepcionista | Concreto |
| CU-O06 | Crear Tipo de Habitación | 4. Operaciones | habitaciones | Hotel Partner | Concreto |
| CU-O07 | Actualizar Inventario | 4. Operaciones | habitaciones | Gerente | Concreto |
| CU-O08 | Validar Estado de Reserva | 4. Operaciones | reservas-mgmt | Sistema | Abstracto |
| CU-O09 | Bloquear Disponibilidad | 4. Operaciones | habitaciones | Gerente | Concreto |
| CU-O10 | Consultar Estado de Habitaciones | 4. Operaciones | habitaciones | Recepcionista | Concreto |
| CU-O11 | Asignar Tarea de Limpieza | 4. Operaciones | housekeeping | Gerente | Concreto |
| CU-O12 | Completar Limpieza | 4. Operaciones | housekeeping | Housekeeping | Concreto |
| CU-O13 | Programar Mantenimiento | 4. Operaciones | mantenimiento | Gerente | Concreto |
| CU-O14 | Completar Mantenimiento | 4. Operaciones | mantenimiento | Técnico | Concreto |
| CU-O15 | Gestionar Turnos de Recepción | 4. Operaciones | recepcion | Recepcionista | Concreto |
| CU-O16 | Visualizar Calendario de Recepción | 4. Operaciones | habitaciones | Recepcionista | Concreto |
| CU-B01 | Generar Factura | 5. Facturación | facturas-pagos | Recepcionista | Concreto |
| CU-B02 | Registrar Pago | 5. Facturación | facturas-pagos | Recepcionista | Concreto |
| CU-B03 | Calcular Impuestos | 5. Facturación | facturas-pagos | Sistema | Abstracto |
| CU-B04 | Consultar Folio | 5. Facturación | facturas-pagos | Recepcionista | Concreto |
| CU-B05 | Crear Cargo Adicional | 5. Facturación | cargos | Recepcionista | Concreto |
| CU-B06 | Crear Gasto (Expense) | 5. Facturación | gastos | Gerente | Concreto |
| CU-B07 | Consultar Libro Mayor | 5. Facturación | gastos | Contador | Concreto |
| CU-B08 | Gestionar Presupuesto | 5. Facturación | gastos | Gerente | Concreto |
| CU-H01 | Crear Empleado | 6. RRHH | — | Gerente HR | Concreto |
| CU-H02 | Gestionar Departamentos | 6. RRHH | — | Gerente HR | Concreto |
| CU-H03 | Programar Turno | 6. RRHH | — | Gerente HR | Concreto |
| CU-H04 | Registrar Check-In de Turno | 6. RRHH | — | Empleado | Concreto |
| CU-H05 | Registrar Check-Out de Turno | 6. RRHH | — | Empleado | Concreto |
| CU-A01 | Iniciar Sesión (JWT) | 7. Administración | auth | Todos | Concreto |
| CU-A02 | Cerrar Sesión | 7. Administración | auth | Todos | Concreto |
| CU-A03 | Cambiar Contraseña | 7. Administración | auth | Todos | Concreto |
| CU-A04 | Actualizar Perfil | 7. Administración | usuarios-roles | Todos | Concreto |
| CU-A05 | Gestionar Usuarios | 7. Administración | usuarios-roles | Super Admin | Concreto |
| CU-A06 | Gestionar Roles y Permisos | 7. Administración | usuarios-roles | Super Admin | Concreto |
| CU-A07 | Configurar Sistema Global | 7. Administración | configuracion | Super Admin | Concreto |
| CU-D01 | Consultar Dashboard Ejecutivo | 8. Analítica | dashboard | Gerente | Concreto |
| CU-D02 | Consultar Reporte de Calidad | 8. Analítica | etl-calidad | Auditor | Concreto |
| CU-D03 | Ejecutar Pipeline ETL | 8. Analítica | etl-calidad | Sistema | Concreto |
| CU-D04 | Editar Metadata de Destino | 8. Analítica | geo | Auditor | Concreto |
| CU-D05 | Visualizar Mapa Mundial | 8. Analítica | geo | Todos | Concreto |
| CU-D06 | Exportar Reporte | 8. Analítica | reportes | Gerente | Concreto |
| CU-I01 | Acceder al Portal Mi Estancia | 9. In-Stay | — | Huésped | Concreto |
| CU-I02 | Enviar Mensaje por Chat | 9. In-Stay | — | Huésped | Concreto |
| CU-I03 | Crear Solicitud de Servicio | 9. In-Stay | — | Huésped | Concreto |
| CU-I04 | Activar/Desactivar DND | 9. In-Stay | — | Huésped | Concreto |
| CU-I05 | Atender Solicitudes (Staff) | 9. In-Stay | — | Staff | Concreto |
| CU-I06 | Gestionar Objetos Perdidos | 9. In-Stay | — | Staff | Concreto |

---

# 1. DEPARTAMENTO: COMERCIAL / EXPERIENCIA CLIENTE

**Descripción**: Gestiona la experiencia del cliente desde la búsqueda hasta la reserva.  
**Actores**: Cliente/Viajero, Sistema  
**Módulos Backend**: `hotels`, `reservations` (guest), `amenities`, `reviews`  
**Módulos Frontend**: `hotel-search`, `hotel-compare`, `hotel-detail`, `reservations`

---

## 1.1 Sub-paquete: busqueda

### CU-C01: Buscar Hoteles

| Atributo | Valor |
|----------|-------|
| **Actor** | Cliente / Viajero |
| **Tipo** | Concreto |
| **Precondición** | Cliente accede a la página de búsqueda |
| **Postcondición** | Lista de hoteles disponibles mostrada al cliente |

**Flujo principal**:

1. Cliente ingresa destino, fechas de entrada/salida, huéspedes
2. Sistema consulta `dim_hotels`, `room_inventory_calendar`, `hotel_rate_calendar`
3. Sistema filtra hoteles con disponibilidad en todas las noches
4. Sistema devuelve lista ordenada por precio ascendente
5. Cliente visualiza resultados

**Relaciones**:

- `<<include>>` CU-C02: Calcular Tarifa en Tiempo Real
- `<<include>>` CU-C03: Validar Disponibilidad

**Colecciones**: `dim_hotels`, `dim_destinations`, `dim_visitor_countries`, `room_inventory_calendar`, `hotel_rate_calendar`, `search_logs`, `click_events`

---

### CU-C02: Calcular Tarifa en Tiempo Real

| Atributo | Valor |
|----------|-------|
| **Actor** | Sistema |
| **Tipo** | Abstracto |
| **Precondición** | Parámetros de búsqueda válidos |
| **Postcondición** | Precio mínimo por noche calculado |

**Flujo principal**:

1. Sistema recibe hotel_id, fechas, huéspedes
2. Sistema consulta `hotel_rate_calendar` para las fechas solicitadas
3. Sistema calcula precio mínimo entre los rate_plans activos
4. Sistema devuelve tarifa

**Colecciones**: `hotel_rate_calendar`, `rate_plans`

---

### CU-C03: Validar Disponibilidad

| Atributo | Valor |
|----------|-------|
| **Actor** | Sistema |
| **Tipo** | Abstracto |
| **Precondición** | Hotel y fechas especificados |
| **Postcondición** | Disponibilidad confirmada o rechazada |

**Flujo principal**:

1. Sistema recibe hotel_id, fechas, tipo de habitación
2. Sistema consulta `room_inventory_calendar`
3. Sistema verifica `available_rooms > 0` para cada noche del rango
4. Sistema devuelve resultado de disponibilidad

**Colecciones**: `room_inventory_calendar`, `room_types`

---

### CU-C04: Filtrar y Comparar Hoteles

| Atributo | Valor |
|----------|-------|
| **Actor** | Cliente / Viajero |
| **Tipo** | Concreto |
| **Precondición** | Resultados de búsqueda disponibles (CU-C01 ejecutado) |
| **Postcondición** | Vista comparativa de 2-3 hoteles mostrada |

**Flujo principal**:

1. Cliente aplica filtros (precio, rating, amenities)
2. Sistema actualiza lista
3. Cliente selecciona 2-3 hoteles y hace clic en "Comparar"
4. Sistema muestra vista comparativa lado a lado con precios calculados

**Relaciones**:

- `<<extend>>` CU-C01: Buscar Hoteles
- `<<include>>` CU-C02: Calcular Tarifa en Tiempo Real

**Colecciones**: `dim_hotels`, `room_inventory_calendar`, `hotel_rate_calendar`, `hotel_amenities`, `click_events`

---

## 1.2 Sub-paquete: detalle

### CU-C05: Ver Detalle de Hotel

| Atributo | Valor |
|----------|-------|
| **Actor** | Cliente / Viajero |
| **Tipo** | Concreto |
| **Precondición** | Hotel seleccionado de la lista de búsqueda |
| **Postcondición** | Página de detalle completa mostrada al cliente |

**Flujo principal**:

1. Cliente hace clic en un hotel de la lista
2. Sistema carga `hotel_images`, `hotel_content_pages`, `hotel_policies`, `reviews`
3. Sistema calcula tarifas por tipo de habitación desde `hotel_rate_calendar`
4. Cliente visualiza detalle completo con galería, amenities, políticas y tarifas

**Relaciones**:

- `<<include>>` CU-C06: Consultar Reseñas Públicas

**Colecciones**: `dim_hotels`, `hotel_images`, `hotel_content_pages`, `hotel_policies`, `hotel_amenities`, `room_types`, `hotel_rate_calendar`, `reviews`, `fact_reviews`, `click_events`

---

### CU-C06: Consultar Reseñas Públicas

| Atributo | Valor |
|----------|-------|
| **Actor** | Sistema |
| **Tipo** | Abstracto |
| **Precondición** | Hotel identificado |
| **Postcondición** | Lista de reseñas aprobadas disponibles |

**Flujo principal**:

1. Sistema recibe prop_id
2. Sistema consulta `reviews` con `moderation_status = "approved"`
3. Sistema ordena por fecha descendente
4. Sistema devuelve reseñas con calificación y comentario

**Colecciones**: `reviews`, `fact_reviews`

---

## 1.3 Sub-paquete: reservas-cliente

### CU-C07: Solicitar Reserva

| Atributo | Valor |
|----------|-------|
| **Actor** | Cliente / Viajero |
| **Tipo** | Concreto |
| **Precondición** | Cliente autenticado (JWT válido), habitación y fechas seleccionadas |
| **Postcondición** | Reserva creada en estado "pending" |

**Flujo principal**:

1. Cliente selecciona tipo de habitación y fechas
2. Sistema valida disponibilidad (`room_inventory_calendar`)
3. Sistema calcula total (`hotel_rate_calendar`)
4. Cliente ingresa datos de huéspedes
5. Sistema crea `booking_orders` en estado `"pending"`
6. Sistema crea `booking_guests`
7. Sistema registra en `booking_status_history`

**Relaciones**:

- `<<include>>` CU-C02: Calcular Tarifa en Tiempo Real
- `<<include>>` CU-C03: Validar Disponibilidad
- `<<include>>` CU-C08: Validar Cliente Autenticado

**Colecciones**: `booking_orders`, `booking_guests`, `booking_status_history`, `room_inventory_calendar`, `hotel_rate_calendar`, `room_types`

---

### CU-C08: Validar Cliente Autenticado

| Atributo | Valor |
|----------|-------|
| **Actor** | Sistema |
| **Tipo** | Abstracto |
| **Precondición** | Petición con cookie/token JWT |
| **Postcondición** | Identidad del usuario verificada o rechazada |

**Flujo principal**:

1. Sistema extrae token JWT de cookie o header
2. Sistema verifica firma y expiración
3. Sistema verifica `user_sessions` activa
4. Sistema devuelve user_id o rechaza con 401

**Colecciones**: `users`, `user_sessions`

---

### CU-C09: Consultar Mis Reservas

| Atributo | Valor |
|----------|-------|
| **Actor** | Cliente / Viajero |
| **Tipo** | Concreto |
| **Precondición** | Cliente autenticado |
| **Postcondición** | Listado de reservas del cliente mostrado |

**Flujo principal**:

1. Cliente navega a "Mis Reservas"
2. Sistema consulta `booking_orders` filtrado por `user_id`
3. Cliente visualiza lista con estados, fechas, hoteles y totales

**Colecciones**: `booking_orders`, `dim_hotels`

---

### CU-C10: Cancelar Reserva

| Atributo | Valor |
|----------|-------|
| **Actor** | Cliente / Viajero |
| **Tipo** | Concreto |
| **Precondición** | Reserva en estado `"pending"` o `"confirmed"` |
| **Postcondición** | Reserva cancelada, inventario liberado si aplica |

**Flujo principal**:

1. Cliente selecciona reserva y hace clic en "Cancelar"
2. Sistema carga política de cancelación desde `hotel_policies`
3. Sistema muestra diálogo con posibles cargos
4. Cliente confirma cancelación
5. Sistema actualiza `booking_orders.status → "cancelled"`
6. Sistema libera inventario (si estaba confirmed)
7. Sistema registra en `booking_status_history`

**Relaciones**:

- `<<extend>>` CU-C09: Consultar Mis Reservas

**Colecciones**: `booking_orders`, `booking_status_history`, `room_inventory_calendar`, `hotel_policies`

---

## 1.4 Sub-paquete: resenias-cliente

### CU-C11: Registrar Reseña

| Atributo | Valor |
|----------|-------|
| **Actor** | Cliente / Viajero |
| **Tipo** | Concreto |
| **Precondición** | Reserva en estado `"checked_out"` |
| **Postcondición** | Reseña creada, pendiente de moderación |

**Flujo principal**:

1. Cliente accede a reseñas desde reserva completada
2. Cliente ingresa calificación (1-5) y comentario
3. Sistema crea `reviews` en estado `"pending"`
4. Sistema realiza dual-write a `fact_reviews`
5. Si calificación ≥ 4: aprobación automática con `moderation_status = "approved"`

**Colecciones**: `reviews`, `fact_reviews`, `booking_orders`

---

# 2. DEPARTAMENTO: REVENUE MANAGEMENT

**Descripción**: Configurar y optimizar tarifas, planes tarifarios, promociones y cupones.  
**Actores**: Revenue Manager, Marketing Hotelero, Gerente, Cliente  
**Módulos Backend**: `revenue`, `partner/rates`  
**Módulos Frontend**: `rates`, `revenue`  
**Sub-paquetes**: Sin sub-paquetes (5 CUs, dominio cohesivo)

---

### CU-R01: Crear Plan Tarifario

| Atributo | Valor |
|----------|-------|
| **Actor** | Revenue Manager |
| **Tipo** | Concreto |
| **Precondición** | Hotel seleccionado |
| **Postcondición** | Plan tarifario creado |

**Flujo principal**:

1. Revenue manager ingresa nombre, descripción, precio base
2. Sistema valida unicidad por propiedad
3. Sistema crea `rate_plans`
4. Sistema registra en `user_activity_logs`

**Colecciones**: `rate_plans`, `rate_rules`, `user_activity_logs`

---

### CU-R02: Configurar Tarifa por Fecha

| Atributo | Valor |
|----------|-------|
| **Actor** | Revenue Manager |
| **Tipo** | Concreto |
| **Precondición** | Plan tarifario existente (CU-R01) |
| **Postcondición** | Tarifas configuradas para las fechas seleccionadas |

**Flujo principal**:

1. Revenue manager navega al calendario de tarifas
2. Sistema muestra precios actuales desde `hotel_rate_calendar`
3. Revenue manager selecciona fecha/rango y asigna precio
4. Sistema valida precio > 0
5. Sistema crea/actualiza `hotel_rate_calendar`

**Relaciones**:

- `<<include>>` CU-R01: Crear Plan Tarifario

**Colecciones**: `hotel_rate_calendar`, `rate_plans`, `user_activity_logs`

---

### CU-R03: Crear Promoción

| Atributo | Valor |
|----------|-------|
| **Actor** | Revenue Manager / Marketing Hotelero |
| **Tipo** | Concreto |
| **Precondición** | Hotel y rate_plan seleccionados |
| **Postcondición** | Campaña y cupones creados |

**Flujo principal**:

1. Usuario crea campaña con nombre, descuento (%), vigencia (start_date, end_date)
2. Sistema genera código de cupón único
3. Sistema guarda en `promotion_campaigns` y `coupon_codes`
4. Sistema registra en `user_activity_logs`

**Colecciones**: `promotion_campaigns`, `coupon_codes`, `user_activity_logs`

---

### CU-R04: Aplicar Cupón en Reserva

| Atributo | Valor |
|----------|-------|
| **Actor** | Cliente / Viajero |
| **Tipo** | Extensor |
| **Precondición** | Reserva en proceso (CU-C07 en ejecución) |
| **Postcondición** | Descuento aplicado al total de la reserva |

**Flujo principal**:

1. Cliente ingresa código de cupón durante solicitud de reserva
2. Sistema valida vigencia (`start_date ≤ today ≤ end_date`)
3. Sistema valida usos restantes (`coupons_used < coupon_count`)
4. Sistema aplica descuento (`discount_percent`) sobre tarifa base
5. Sistema recalcula total de la reserva

**Relaciones**:

- `<<extend>>` CU-C07: Solicitar Reserva

**Colecciones**: `coupon_codes`, `promotion_campaigns`, `booking_orders`

---

### CU-R05: Consultar Reportes de Revenue

| Atributo | Valor |
|----------|-------|
| **Actor** | Revenue Manager / Gerente |
| **Tipo** | Concreto |
| **Precondición** | Datos ETL cargados en `fact_hotel_reservations` |
| **Postcondición** | Dashboard de revenue con métricas calculadas |

**Flujo principal**:

1. Usuario consulta dashboard de revenue
2. Sistema agrega datos desde `fact_hotel_reservations`
3. Sistema calcula ADR (`total_revenue / reservations_count`)
4. Sistema calcula RevPAR (`total_revenue / available_rooms`)
5. Sistema calcula ocupación (`occupied_rooms / total_rooms`)
6. Sistema muestra top hoteles, destinos y países por revenue

**Colecciones**: `fact_hotel_reservations`, `kpi_summary`, `dim_hotels`

---

# 3. DEPARTAMENTO: MARKETING HOTELERO / PARTNER

**Descripción**: Gestionar reputación online, contenido comercial, imágenes, amenities y perfil.  
**Actores**: Marketing Hotelero, Hotel Partner, Super Admin  
**Módulos Backend**: `partner`, `amenities`, `reviews`  
**Módulos Frontend**: `properties`, `policies`, `rooms`, `amenities`

---

## 3.1 Sub-paquete: propiedades

### CU-M01: Editar Nombre Comercial del Hotel

| Atributo | Valor |
|----------|-------|
| **Actor** | Marketing Hotelero / Hotel Partner |
| **Tipo** | Concreto |
| **Precondición** | Hotel identificado |
| **Postcondición** | Nombre comercial actualizado, override activado |

**Flujo principal**:

1. Usuario navega a edición de perfil del hotel
2. Sistema muestra formulario con campos editables
3. Usuario modifica `display_name` / `hotel_name`
4. Sistema activa `manual_override = true`
5. Sistema registra cambio en `hotel_profile_changes`
6. Sistema actualiza `dim_hotels`

**Colecciones**: `dim_hotels`, `hotel_profile`, `hotel_profile_changes`, `hotels`, `user_activity_logs`

---

## 3.2 Sub-paquete: contenido

### CU-M02: Actualizar Contenido del Hotel

| Atributo | Valor |
|----------|-------|
| **Actor** | Marketing Hotelero / Hotel Partner |
| **Tipo** | Concreto |
| **Precondición** | Hotel identificado |
| **Postcondición** | Contenido e imágenes actualizados |

**Flujo principal**:

1. Usuario navega al gestor de contenido
2. Sistema carga `hotel_content_pages`, `hotel_images`, `system_catalogs`
3. Usuario edita descripciones, highlights, amenities
4. Usuario sube/elimina imágenes (JPEG/PNG, máx 5MB)
5. Sistema actualiza `hotel_content_pages`, `hotel_images`
6. Sistema registra en `hotel_content_changes`

**Relaciones**:

- `<<include>>` CU-M03: Validar Imágenes

**Colecciones**: `hotel_content_pages`, `hotel_images`, `hotel_content_changes`, `system_catalogs`, `user_activity_logs`

---

### CU-M03: Validar Imágenes

| Atributo | Valor |
|----------|-------|
| **Actor** | Sistema |
| **Tipo** | Abstracto |
| **Precondición** | Archivo de imagen recibido |
| **Postcondición** | Imagen validada o rechazada |

**Flujo principal**:

1. Sistema verifica formato (JPEG/PNG)
2. Sistema verifica tamaño (≤ 5MB)
3. Sistema genera nombre único y almacena
4. Si error: devuelve mensaje de validación

**Colecciones**: `hotel_images`

---

## 3.3 Sub-paquete: politicas

### CU-M04: Editar Políticas Hoteleras

| Atributo | Valor |
|----------|-------|
| **Actor** | Hotel Partner |
| **Tipo** | Concreto |
| **Precondición** | Hotel identificado |
| **Postcondición** | Políticas actualizadas |

**Flujo principal**:

1. Usuario edita check-in/out, cancelación, mascotas, niños
2. Sistema valida horarios (formato HH:MM)
3. Sistema valida `min_stay ≥ 1`, `max_stay ≤ 365`
4. Sistema guarda en `hotel_policies`
5. Sistema registra auditoría

**Colecciones**: `hotel_policies`, `user_activity_logs`

---

## 3.4 Sub-paquete: amenities

### CU-M05: Gestionar Amenities

| Atributo | Valor |
|----------|-------|
| **Actor** | Hotel Partner |
| **Tipo** | Concreto |
| **Precondición** | Hotel identificado, catálogo `system_catalogs` cargado |
| **Postcondición** | Amenities del hotel actualizados |

**Flujo principal**:

1. Usuario selecciona amenities del catálogo (`system_catalogs`)
2. Sistema actualiza `hotel_content_pages.active_amenities`
3. Sistema genera `amenities_catalog` con categorías
4. Sistema actualiza `hotel_amenities` y `room_features`

**Colecciones**: `hotel_amenities`, `room_features`, `system_catalogs`, `hotel_content_pages`, `corporate_contracts`, `user_activity_logs`

---

## 3.5 Sub-paquete: resenias-mod

### CU-M06: Moderar y Responder Reseñas

| Atributo | Valor |
|----------|-------|
| **Actor** | Marketing Hotelero / Super Admin |
| **Tipo** | Concreto |
| **Precondición** | Reseñas pendientes de moderación existentes |
| **Postcondición** | Reseña aprobada/rechazada, respuesta publicada si aplica |

**Flujo principal**:

1. Moderador revisa reseñas con `moderation_status = "pending"`
2. Moderador aprueba (`"approved"`) o rechaza (`"rejected"`) con motivo
3. Si aprobada y necesita respuesta: escribe `staff_response`
4. Sistema actualiza `reviews.moderation_status`, `staff_response`, `staff_response_at`
5. Sistema actualiza `fact_reviews` (dual-write)
6. Si rechazada: opcionalmente crea `review_reports`

**Colecciones**: `reviews`, `fact_reviews`, `review_reports`, `user_activity_logs`

---

# 4. DEPARTAMENTO: OPERACIONES HOTELERAS

**Descripción**: Ejecutar la operación diaria del hotel: check-in/out, reservas manuales, gestión de habitaciones, inventario, housekeeping, mantenimiento y recepción.  
**Actores**: Recepcionista, Gerente, Hotel Partner, Personal de Housekeeping, Técnico  
**Módulos Backend**: `reservations`, `housekeeping`, `reception`, `reception-calendar`  
**Módulos Frontend**: `management`, `check-ins`, `check-outs`, `manual-reservations`, `housekeeping`, `reception`, `shifts`, `availability`

---

## 4.1 Sub-paquete: reservas-mgmt

### CU-O01: Crear Reserva Manual (Walk-in)

| Atributo | Valor |
|----------|-------|
| **Actor** | Recepcionista |
| **Tipo** | Concreto |
| **Precondición** | Habitación disponible |
| **Postcondición** | Reserva creada en estado "confirmed", inventario descontado |

**Flujo principal**:

1. Recepcionista ingresa datos del huésped (nombre, email, teléfono)
2. Recepcionista selecciona tipo de habitación y fechas
3. Sistema crea `booking_orders` en estado `"confirmed"`
4. Sistema descuenta inventario inmediatamente (`room_inventory_calendar`)
5. Sistema registra en `booking_status_history`
6. Sistema crea `manual_reservations` vinculando a la reserva

**Colecciones**: `booking_orders`, `booking_guests`, `booking_status_history`, `manual_reservations`, `room_inventory_calendar`, `user_activity_logs`

---

### CU-O02: Consultar Solicitudes de Reserva

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente |
| **Tipo** | Concreto |
| **Precondición** | Reservas en estado "pending" existen |
| **Postcondición** | Listado de solicitudes pendientes mostrado |

**Flujo principal**:

1. Gerente consulta reservas en estado `"pending"`
2. Sistema muestra listado filtrado por `prop_id`
3. Sistema incluye datos del huésped, fechas, tipo de habitación, total

**Colecciones**: `booking_orders`, `booking_guests`, `dim_hotels`

---

### CU-O03: Confirmar/Rechazar Solicitud

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente |
| **Tipo** | Concreto |
| **Precondición** | Solicitud pendiente seleccionada (CU-O02) |
| **Postcondición** | Reserva confirmada o cancelada |

**Flujo principal**:

1. Gerente selecciona solicitud pendiente
2. **Confirmar**: estado → `"confirmed"`, descuenta inventario, notifica al cliente
3. **Rechazar**: estado → `"cancelled"`, registra motivo de rechazo
4. Sistema actualiza `booking_status_history`

**Relaciones**:

- `<<extend>>` CU-O02: Consultar Solicitudes

**Colecciones**: `booking_orders`, `booking_status_history`, `room_inventory_calendar`, `user_activity_logs`

---

### CU-O08: Validar Estado de Reserva

| Atributo | Valor |
|----------|-------|
| **Actor** | Sistema |
| **Tipo** | Abstracto |
| **Precondición** | Reserva identificada |
| **Postcondición** | Estado validado o error |

**Flujo principal**:

1. Sistema recibe booking_id y estado esperado
2. Sistema consulta `booking_orders.status`
3. Si `status == estado_esperado`: continúa
4. Si no: devuelve error con estado actual vs esperado

**Colecciones**: `booking_orders`

---

## 4.2 Sub-paquete: checkin-checkout

### CU-O04: Completar Check-In

| Atributo | Valor |
|----------|-------|
| **Actor** | Recepcionista |
| **Tipo** | Concreto |
| **Precondición** | Reserva en estado `"confirmed"` |
| **Postcondición** | Huésped registrado, habitación ocupada |

**Flujo principal**:

1. Recepcionista busca reserva por nombre/booking_id
2. Verifica identidad del huésped
3. Confirma check-in
4. Sistema: `booking_orders.status → "checked_in"`, `stay_status → "active"`
5. Sistema: actualiza `room_status_log` a `"occupied"`
6. Sistema: registra en `booking_status_history`
7. Sistema: asigna huéspedes a habitaciones (`booking_room_guests`)

**Relaciones**:

- `<<include>>` CU-O08: Validar Estado de Reserva

**Colecciones**: `booking_orders`, `booking_room_guests`, `booking_status_history`, `room_status_log`, `user_activity_logs`

---

### CU-O05: Completar Check-Out

| Atributo | Valor |
|----------|-------|
| **Actor** | Recepcionista |
| **Tipo** | Concreto |
| **Precondición** | Reserva en estado `"checked_in"` |
| **Postcondición** | Huésped fuera, habitación en limpieza, factura generada |

**Flujo principal**:

1. Recepcionista busca reserva
2. Verifica cargos adicionales (`additional_charges`)
3. Genera factura (invoca CU-B01)
4. Registra pago (invoca CU-B02)
5. Confirma check-out
6. Sistema: `booking_orders.status → "checked_out"`, `stay_status → "completed"`
7. Sistema: libera inventario de noches futuras
8. Sistema: `room_status_log → "cleaning_needed"`

**Relaciones**:

- `<<include>>` CU-B01: Generar Factura
- `<<include>>` CU-B02: Registrar Pago
- `<<include>>` CU-O08: Validar Estado de Reserva

**Colecciones**: `booking_orders`, `booking_status_history`, `room_status_log`, `additional_charges`, `room_inventory_calendar`, `user_activity_logs`

---

## 4.3 Sub-paquete: habitaciones

### CU-O06: Crear Tipo de Habitación

| Atributo | Valor |
|----------|-------|
| **Actor** | Hotel Partner |
| **Tipo** | Concreto |
| **Precondición** | Hotel identificado |
| **Postcondición** | Tipo de habitación y habitaciones físicas creadas |

**Flujo principal**:

1. Partner ingresa nombre, capacidad (max_adults, max_children), descripción
2. Sistema valida unicidad de `room_type_id` por propiedad
3. Sistema crea `room_types`
4. Sistema crea `hotel_rooms` físicas asociadas (una por cada habitación)

**Colecciones**: `room_types`, `hotel_rooms`, `user_activity_logs`

---

### CU-O07: Actualizar Inventario

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente |
| **Tipo** | Concreto |
| **Precondición** | Tipo de habitación creado (CU-O06) |
| **Postcondición** | Inventario actualizado con optimistic locking |

**Flujo principal**:

1. Gerente selecciona tipo de habitación y fecha
2. Ingresa nuevo inventario disponible (`available_rooms`)
3. Sistema aplica optimistic locking: verifica `version` actual
4. Sistema actualiza `room_inventory_calendar` con `version + 1`
5. Si conflicto de versión: recarga y reintenta

**Colecciones**: `room_inventory_calendar`, `room_types`, `user_activity_logs`

---

### CU-O09: Bloquear Disponibilidad

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente |
| **Tipo** | Concreto |
| **Precondición** | Fechas y tipo de habitación seleccionados |
| **Postcondición** | Habitaciones bloqueadas, blackout registrado |

**Flujo principal**:

1. Gerente selecciona rango de fechas y tipo de habitación
2. Ingresa motivo (mantenimiento, evento, overbooking)
3. Sistema crea `blackout_dates`
4. Sistema crea `room_availability_blocks`
5. Sistema actualiza `room_inventory_calendar.blocked_rooms`

**Colecciones**: `blackout_dates`, `room_availability_blocks`, `room_inventory_calendar`, `user_activity_logs`

---

### CU-O10: Consultar Estado de Habitaciones

| Atributo | Valor |
|----------|-------|
| **Actor** | Recepcionista / Gerente |
| **Tipo** | Concreto |
| **Precondición** | Hotel seleccionado |
| **Postcondición** | Matriz visual de estados de habitaciones mostrada |

**Flujo principal**:

1. Usuario abre panel de estado de habitaciones
2. Sistema consulta `room_status_log` filtrado por `prop_id`
3. Sistema muestra matriz visual con códigos de colores:
   - Verde: `available`
   - Rojo: `occupied`
   - Amarillo: `cleaning_needed` / `cleaning_in_progress`
   - Gris: `maintenance`
   - Naranja: `dnd`

**Colecciones**: `room_status_log`, `hotel_rooms`

---

### CU-O16: Visualizar Calendario de Recepción

| Atributo | Valor |
|----------|-------|
| **Actor** | Recepcionista / Gerente |
| **Tipo** | Concreto |
| **Precondición** | Hotel y rango de fechas seleccionados |
| **Postcondición** | Timeline visual de reservas por habitación mostrado |

**Flujo principal**:

1. Usuario accede al calendario de recepción
2. Sistema consulta `hotel_rooms` (habitaciones físicas activas)
3. Sistema consulta `booking_orders` que intersectan el rango de fechas
4. Sistema asigna cada reserva a su habitación física (`assigned_rooms`)
5. Sistema calcula estado visual: `active` | `upcoming` | `past` | `cancelled`
6. Sistema devuelve timeline por habitación con fracciones de check-in/out

**Colecciones**: `hotel_rooms`, `booking_orders`, `booking_room_guests`, `room_status_log`, `hotel_booking_context`

---

## 4.4 Sub-paquete: housekeeping

### CU-O11: Asignar Tarea de Limpieza

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente / Recepcionista |
| **Tipo** | Concreto |
| **Precondición** | Habitación en estado `"cleaning_needed"` |
| **Postcondición** | Tarea asignada, estado actualizado |

**Flujo principal**:

1. Post-check-out: habitación aparece en `"cleaning_needed"`
2. Usuario asigna tarea a personal de housekeeping (`assigned_to`)
3. Sistema crea `housekeeping_tasks` con `status = "pending"`, `priority = "normal"`
4. Sistema actualiza `room_status_log.status → "cleaning_in_progress"`

**Colecciones**: `housekeeping_tasks`, `room_status_log`, `room_status_history`, `user_activity_logs`

---

### CU-O12: Completar Limpieza

| Atributo | Valor |
|----------|-------|
| **Actor** | Personal de Housekeeping |
| **Tipo** | Concreto |
| **Precondición** | Tarea de limpieza asignada (CU-O11) |
| **Postcondición** | Habitación disponible, tarea completada |

**Flujo principal**:

1. Personal marca inicio de limpieza (`status → "in_progress"`)
2. Personal completa limpieza
3. Sistema registra tiempo de rotación (`completed_at - scheduled_date`)
4. Sistema: `room_status_log.status → "available"`
5. Sistema: `housekeeping_tasks.status → "completed"`

**Colecciones**: `housekeeping_tasks`, `room_status_log`, `room_status_history`, `user_activity_logs`

---

## 4.5 Sub-paquete: mantenimiento

### CU-O13: Programar Mantenimiento

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente |
| **Tipo** | Concreto |
| **Precondición** | Habitación identificada |
| **Postcondición** | Tarea de mantenimiento programada, habitación bloqueada |

**Flujo principal**:

1. Gerente selecciona habitación y tipo de mantenimiento (plomería, eléctrico, pintura, etc.)
2. Ingresa fecha programada, prioridad y descripción
3. Sistema crea `maintenance_tasks` con `status = "scheduled"`
4. Sistema: `room_status_log.status → "maintenance"`
5. Sistema: actualiza `room_inventory_calendar` (descuenta disponibilidad)

**Colecciones**: `maintenance_tasks`, `room_status_log`, `room_inventory_calendar`, `user_activity_logs`

---

### CU-O14: Completar Mantenimiento

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente / Técnico |
| **Tipo** | Concreto |
| **Precondición** | Tarea de mantenimiento programada (CU-O13) |
| **Postcondición** | Habitación disponible o en limpieza |

**Flujo principal**:

1. Técnico completa tarea de mantenimiento
2. Sistema actualiza `maintenance_tasks.status → "completed"`
3. Si habitación quedó limpia: `room_status_log → "available"`
4. Si necesita limpieza post-mantenimiento: `room_status_log → "cleaning_needed"`

**Colecciones**: `maintenance_tasks`, `room_status_log`, `user_activity_logs`

---

## 4.6 Sub-paquete: recepcion

### CU-O15: Gestionar Turnos de Recepción

| Atributo | Valor |
|----------|-------|
| **Actor** | Recepcionista / Gerente |
| **Tipo** | Concreto |
| **Precondición** | Usuario autenticado como recepcionista |
| **Postcondición** | Turno abierto/cerrado, transacciones registradas |

**Flujo principal**:

1. Recepcionista abre turno: sistema crea `reception_shifts` con `start_time = now()`
2. Durante el turno: sistema registra transacciones (check-ins, check-outs, pagos)
3. Al finalizar: recepcionista cierra turno con notas y conteo de caja
4. Sistema: `reception_shifts.status → "closed"`, `end_time = now()`

**Colecciones**: `reception_shifts`, `user_activity_logs`

---

# 5. DEPARTAMENTO: FACTURACIÓN, PAGOS Y GASTOS

**Descripción**: Gestionar facturación, pagos, folios de huésped, cargos adicionales y gastos operativos.  
**Actores**: Recepcionista, Gerente, Contador  
**Módulos Backend**: `billing`, `expenses`  
**Módulos Frontend**: `billing`, `expenses`

---

## 5.1 Sub-paquete: facturas-pagos

### CU-B01: Generar Factura

| Atributo | Valor |
|----------|-------|
| **Actor** | Recepcionista |
| **Tipo** | Concreto |
| **Precondición** | Reserva en estado `"checked_out"` o `"checked_in"` (early invoice) |
| **Postcondición** | Factura generada con número único |

**Flujo principal**:

1. Sistema calcula subtotal = noches × tarifa por noche
2. Sistema suma cargos adicionales desde `additional_charges`
3. Sistema aplica impuestos (invoca CU-B03)
4. Sistema genera número de factura único (`invoice_number`)
5. Sistema crea `reservation_invoices` con `status = "pending"`
6. Sistema realiza dual-write a `fact_reservation_invoices`

**Relaciones**:

- `<<include>>` CU-B03: Calcular Impuestos

**Colecciones**: `reservation_invoices`, `fact_reservation_invoices`, `additional_charges`, `tax_rates`, `commission_rates`, `booking_orders`, `user_activity_logs`

---

### CU-B02: Registrar Pago

| Atributo | Valor |
|----------|-------|
| **Actor** | Recepcionista |
| **Tipo** | Concreto |
| **Precondición** | Factura generada (CU-B01) |
| **Postcondición** | Pago registrado, factura actualizada |

**Flujo principal**:

1. Recepcionista selecciona factura pendiente
2. Ingresa monto, método (cash, card, transfer), referencia
3. Sistema crea `reservation_payments` con `status = "completed"`
4. Sistema actualiza estado de factura según monto:
   - Pago parcial: `status = "partial"`
   - Pago completo: `status = "paid"`
5. Sistema actualiza `guest_folios` (total_payments, total_due)
6. Sistema dual-write a `fact_reservation_payments`

**Relaciones**:

- `<<include>>` CU-B01: Generar Factura

**Colecciones**: `reservation_payments`, `fact_reservation_payments`, `reservation_invoices`, `guest_folios`, `user_activity_logs`

---

### CU-B03: Calcular Impuestos

| Atributo | Valor |
|----------|-------|
| **Actor** | Sistema |
| **Tipo** | Abstracto |
| **Precondición** | Subtotal y país del hotel disponibles |
| **Postcondición** | Total con impuestos calculado |

**Flujo principal**:

1. Sistema consulta `tax_rates` por país del hotel
2. Sistema consulta `commission_rates` por prop_id
3. Sistema calcula: `taxes = subtotal × tax_pct`
4. Sistema calcula: `commission = (subtotal + taxes) × commission_pct`
5. Sistema devuelve: `total = subtotal + taxes`

**Colecciones**: `tax_rates`, `commission_rates`

---

### CU-B04: Consultar Folio

| Atributo | Valor |
|----------|-------|
| **Actor** | Recepcionista / Gerente |
| **Tipo** | Concreto |
| **Precondición** | Reserva activa o completada |
| **Postcondición** | Folio con balance y postings mostrado |

**Flujo principal**:

1. Usuario busca folio por `booking_id`
2. Sistema consulta `guest_folios`
3. Sistema muestra: postings (cargos y pagos), totales, balance (`total_due`)
4. Sistema indica si el folio está cerrado o abierto

**Colecciones**: `guest_folios`, `additional_charges`, `reservation_invoices`, `reservation_payments`

---

## 5.2 Sub-paquete: cargos

### CU-B05: Crear Cargo Adicional

| Atributo | Valor |
|----------|-------|
| **Actor** | Recepcionista |
| **Tipo** | Concreto |
| **Precondición** | Reserva en estado `"confirmed"` o `"checked_in"` |
| **Postcondición** | Cargo agregado al folio del huésped |

**Flujo principal**:

1. Recepcionista selecciona reserva activa
2. Ingresa concepto (minibar, room service, lavandería, etc.), monto, cantidad
3. Sistema valida que la reserva esté en estado válido
4. Sistema crea `additional_charges` con `total = amount × quantity`
5. Sistema actualiza `guest_folios`: agrega posting, recalcula `total_due`

**Colecciones**: `additional_charges`, `guest_folios`, `booking_orders`, `user_activity_logs`

---

## 5.3 Sub-paquete: gastos

### CU-B06: Crear Gasto (Expense)

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente |
| **Tipo** | Concreto |
| **Precondición** | Categoría de gasto existente |
| **Postcondición** | Gasto registrado, presupuesto actualizado |

**Flujo principal**:

1. Gerente ingresa proveedor, categoría, monto, descripción, fecha
2. Sistema crea `expense_invoices` con `status = "pending"`
3. Sistema actualiza `expense_categories.spent += amount`
4. Sistema recalcula `expense_categories.remaining = budget - spent`
5. Si `spent > 90%` del presupuesto: sistema genera alerta
6. Si aprobado: sistema impacta `ledger_transactions`

**Colecciones**: `expense_invoices`, `expense_categories`, `expense_budget`, `ledger_transactions`, `user_activity_logs`

---

### CU-B07: Consultar Libro Mayor

| Atributo | Valor |
|----------|-------|
| **Actor** | Contador / Gerente |
| **Tipo** | Concreto |
| **Precondición** | Transacciones registradas |
| **Postcondición** | Balance y movimientos del período mostrados |

**Flujo principal**:

1. Usuario consulta `ledger_transactions` filtrando por período
2. Sistema muestra transacciones ordenadas por fecha
3. Sistema calcula balance: `SUM(debit) - SUM(credit)`
4. Sistema muestra cuentas del `chart_of_accounts`

**Colecciones**: `ledger_transactions`, `chart_of_accounts`

---

### CU-B08: Gestionar Presupuesto

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente |
| **Tipo** | Concreto |
| **Precondición** | Departamento y período definidos |
| **Postcondición** | Presupuesto creado/actualizado con alertas |

**Flujo principal**:

1. Gerente define presupuesto por departamento y período (ej: "2026-Q3")
2. Sistema crea `expense_budget` con `amount`, `spent = 0`, `remaining = amount`
3. A medida que se crean gastos: `spent` aumenta, `remaining` disminuye
4. Sistema alerta si `spent > 90%` del budget
5. Sistema alerta si `spent > amount` (sobrepresupuesto)

**Colecciones**: `expense_budget`, `expense_categories`, `user_activity_logs`

---

# 6. DEPARTAMENTO: RECURSOS HUMANOS

**Descripción**: Gestionar empleados, departamentos, turnos y documentación del personal.  
**Actores**: Gerente HR, Empleado  
**Módulos Backend**: `hr`  
**Módulos Frontend**: `hr`  
**Sub-paquetes**: Sin sub-paquetes (5 CUs, 6 colecciones)

---

### CU-H01: Crear Empleado

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente HR |
| **Tipo** | Concreto |
| **Precondición** | Departamento definido |
| **Postcondición** | Empleado creado en el sistema |

**Flujo principal**:

1. Gerente ingresa datos personales (full_name, id_document, phone, email, address)
2. Gerente asigna posición, departamento, fecha de contratación, salario
3. Sistema valida unicidad de `id_document`
4. Sistema crea `employees` con `is_active = true`
5. Sistema sube documentos (`employee_documents`) si se adjuntan

**Colecciones**: `employees`, `employee_documents`, `employee_departments`, `user_activity_logs`

---

### CU-H02: Gestionar Departamentos

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente HR |
| **Tipo** | Concreto |
| **Precondición** | Ninguna |
| **Postcondición** | Departamento creado/editado |

**Flujo principal**:

1. Gerente crea/edita departamentos (nombre, descripción)
2. Sistema actualiza `employee_departments`
3. Sistema recalcula `head_count` basado en empleados activos del departamento

**Colecciones**: `employee_departments`, `employees`, `user_activity_logs`

---

### CU-H03: Programar Turno

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente HR |
| **Tipo** | Concreto |
| **Precondición** | Empleado activo |
| **Postcondición** | Turno programado |

**Flujo principal**:

1. Gerente selecciona empleado y fecha
2. Ingresa horario programado (`scheduled_start`, `scheduled_end`), área, tipo de turno
3. Sistema crea `employee_shifts` con `status = "pending"`

**Colecciones**: `employee_shifts`, `employees`, `user_activity_logs`

---

### CU-H04: Registrar Check-In de Turno

| Atributo | Valor |
|----------|-------|
| **Actor** | Empleado |
| **Tipo** | Concreto |
| **Precondición** | Turno programado (CU-H03) |
| **Postcondición** | Check-in registrado, turno activo |

**Flujo principal**:

1. Empleado accede a portal de empleado
2. Empleado registra llegada al turno
3. Sistema: `employee_shifts.actual_check_in = now()`
4. Sistema: `employee_shifts.status → "active"`

**Colecciones**: `employee_shifts`

---

### CU-H05: Registrar Check-Out de Turno

| Atributo | Valor |
|----------|-------|
| **Actor** | Empleado |
| **Tipo** | Concreto |
| **Precondición** | Turno en estado "active" (CU-H04) |
| **Postcondición** | Turno completado, horas calculadas |

**Flujo principal**:

1. Empleado registra salida del turno
2. Sistema: `employee_shifts.actual_check_out = now()`
3. Sistema: `employee_shifts.status → "completed"`
4. Sistema calcula horas trabajadas: `actual_check_out - actual_check_in`

**Colecciones**: `employee_shifts`

---

# 7. DEPARTAMENTO: ADMINISTRACIÓN DEL SISTEMA

**Descripción**: Administrar usuarios, roles, permisos, autenticación, configuración global y auditoría.  
**Actores**: Super Admin, Admin de Sistema, Todos los usuarios  
**Módulos Backend**: `admin`, `auth`, `account`, `users`, `settings`, `global_settings`, `notifications`  
**Módulos Frontend**: `admin`, `account`, `system-admin`, `ownership`, `settings`, `notifications`

---

## 7.1 Sub-paquete: auth

### CU-A01: Iniciar Sesión (JWT)

| Atributo | Valor |
|----------|-------|
| **Actor** | Todos los usuarios |
| **Tipo** | Concreto |
| **Precondición** | Usuario registrado con email verificado |
| **Postcondición** | Sesión JWT creada, cookie establecida |

**Flujo principal**:

1. Usuario ingresa email + contraseña
2. Sistema busca en `users` por email
3. Sistema verifica contraseña con bcrypt
4. Sistema verifica `is_active = true` y `locked_until` no expirado
5. Sistema invalida sesiones previas del usuario
6. Sistema genera token JWT (48 bytes)
7. Sistema almacena hash SHA-256 en `user_sessions`
8. Sistema establece cookie httponly, samesite=lax
9. Sistema registra en `user_activity_logs`

**Colecciones**: `users`, `user_sessions`, `refresh_tokens`, `user_activity_logs`

---

### CU-A02: Cerrar Sesión

| Atributo | Valor |
|----------|-------|
| **Actor** | Todos los usuarios |
| **Tipo** | Concreto |
| **Precondición** | Sesión activa |
| **Postcondición** | Sesión eliminada, cookie expirada |

**Flujo principal**:

1. Usuario hace clic en "Cerrar sesión"
2. Sistema extrae token de cookie
3. Sistema elimina registro de `user_sessions`
4. Sistema elimina cookie (max-age=0)
5. Sistema registra en `user_activity_logs`

**Colecciones**: `user_sessions`, `user_activity_logs`

---

### CU-A03: Cambiar Contraseña

| Atributo | Valor |
|----------|-------|
| **Actor** | Todos los usuarios |
| **Tipo** | Concreto |
| **Precondición** | Usuario autenticado, contraseña actual conocida |
| **Postcondición** | Contraseña actualizada, sesiones antiguas invalidadas |

**Flujo principal**:

1. Usuario ingresa contraseña actual y nueva
2. Sistema verifica contraseña actual con bcrypt
3. Sistema valida nueva contraseña ≥ 8 caracteres
4. Sistema hashea nueva con bcrypt
5. Sistema invalida todas las sesiones excepto la actual
6. Sistema: `must_change_password = false`
7. Sistema registra en `user_activity_logs`

**Colecciones**: `users`, `user_sessions`, `password_recovery_tokens`, `user_activity_logs`

---

## 7.2 Sub-paquete: usuarios-roles

### CU-A04: Actualizar Perfil

| Atributo | Valor |
|----------|-------|
| **Actor** | Todos los usuarios |
| **Tipo** | Concreto |
| **Precondición** | Usuario autenticado |
| **Postcondición** | Perfil actualizado |

**Flujo principal**:

1. Usuario modifica datos (display_name, email, teléfono)
2. Sistema valida unicidad de email si cambió
3. Sistema actualiza `users`
4. Sistema registra en `user_activity_logs`

**Colecciones**: `users`, `user_activity_logs`

---

### CU-A05: Gestionar Usuarios

| Atributo | Valor |
|----------|-------|
| **Actor** | Super Admin |
| **Tipo** | Concreto |
| **Precondición** | Rol con permisos de administración |
| **Postcondición** | Usuario creado/editado/desactivado |

**Flujo principal**:

1. Super admin crea/edita/desactiva usuarios
2. Asigna roles (role_ids) y hoteles (`prop_id` scope)
3. Sistema actualiza `users`
4. Sistema actualiza `role_permissions` si cambian roles
5. Sistema registra en `user_activity_logs`

**Colecciones**: `users`, `roles`, `role_permissions`, `user_activity_logs`

---

### CU-A06: Gestionar Roles y Permisos

| Atributo | Valor |
|----------|-------|
| **Actor** | Super Admin |
| **Tipo** | Concreto |
| **Precondición** | Ninguna |
| **Postcondición** | Roles y permisos actualizados |

**Flujo principal**:

1. Super admin define/edita roles (`role_name`, `display_name`, `description`)
2. Super admin define/edita permisos (`permission_code`, `description`)
3. Asigna permisos a roles en `role_permissions`
4. Sistema actualiza `roles`, `permissions`, `role_permissions`

**Colecciones**: `roles`, `permissions`, `role_permissions`, `user_activity_logs`

---

## 7.3 Sub-paquete: configuracion

### CU-A07: Configurar Sistema Global

| Atributo | Valor |
|----------|-------|
| **Actor** | Super Admin |
| **Tipo** | Concreto |
| **Precondición** | Permisos de administración del sistema |
| **Postcondición** | Configuración global actualizada |

**Flujo principal**:

1. Admin edita comisiones (`commission_rates.commission_pct`)
2. Admin edita impuestos (`tax_rates.tax_pct`)
3. Admin edita configuraciones generales (`system_config`)
4. Sistema valida valores (porcentajes entre 0-100)
5. Sistema actualiza colecciones correspondientes
6. Sistema registra en `user_activity_logs`

**Colecciones**: `system_config`, `commission_rates`, `tax_rates`, `notification_log`, `user_activity_logs`

---

# 8. DEPARTAMENTO: DATOS, ANALÍTICA Y GEOLOCALIZACIÓN

**Descripción**: Ejecutar pipelines ETL, monitorear calidad de datos, generar reportes, dashboards y gestionar catálogos geoespaciales.  
**Actores**: Auditor de Datos, Gerente, Marketing  
**Módulos Backend**: `kpi`, `audit`, `map`, `geo_catalog`, `reports`  
**Módulos Frontend**: `map`, `geo-catalog`

---

## 8.1 Sub-paquete: etl-calidad

### CU-D02: Consultar Reporte de Calidad

| Atributo | Valor |
|----------|-------|
| **Actor** | Auditor de Datos |
| **Tipo** | Concreto |
| **Precondición** | Pipeline ETL ejecutado al menos una vez |
| **Postcondición** | Métricas de calidad mostradas |

**Flujo principal**:

1. Auditor consulta última ejecución ETL por `execution_id`
2. Sistema carga `data_quality_reports`
3. Sistema muestra: registros procesados, aceptados, rechazados
4. Sistema muestra `completeness_score` por dimensión
5. Auditor puede navegar a `rejected_records` para ver detalle

**Colecciones**: `data_quality_reports`, `etl_executions`, `rejected_records`, `search_logs`

---

### CU-D03: Ejecutar Pipeline ETL

| Atributo | Valor |
|----------|-------|
| **Actor** | Sistema (Airflow) / Auditor de Datos |
| **Tipo** | Concreto |
| **Precondición** | Archivos CSV en `data/raw/` |
| **Postcondición** | Datos cargados, reporte de calidad generado |

**Flujo principal**:

1. Airflow DAG lee CSV desde `data/raw/`
2. Sistema valida cada registro (tipos, rangos, nulos)
3. Sistema carga aprobados a colecciones maestras:
   - Dimensiones: `dim_hotels`, `dim_destinations`, `dim_dates`, etc.
   - Hechos: `fact_hotel_reservations`
4. Sistema almacena rechazados en `rejected_records` con motivo
5. Sistema genera `data_quality_reports` con métricas
6. Sistema registra ejecución en `etl_executions`

**Colecciones**: `etl_executions`, `data_quality_reports`, `rejected_records`, `fact_hotel_reservations`, 14 dimensiones

---

## 8.2 Sub-paquete: dashboard

### CU-D01: Consultar Dashboard Ejecutivo

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente / Revenue Manager / Admin |
| **Tipo** | Concreto |
| **Precondición** | Datos ETL cargados |
| **Postcondición** | Dashboard con métricas clave mostrado |

**Flujo principal**:

1. Usuario accede al dashboard
2. Sistema consulta `kpi_summary` (cache)
3. Sistema calcula métricas desde `fact_hotel_reservations`:
   - Total de eventos
   - Total de reservas
   - Revenue total
   - Precio medio
   - Ocupación
4. Sistema muestra gráficos de tendencias por dimensiones

**Colecciones**: `kpi_summary`, `fact_hotel_reservations`, `fact_hotel_events`, `dim_hotels` (+ 12 dimensiones), `click_events`

---

## 8.3 Sub-paquete: geo

### CU-D04: Editar Metadata de Destino

| Atributo | Valor |
|----------|-------|
| **Actor** | Auditor de Datos / Marketing |
| **Tipo** | Concreto |
| **Precondición** | Destino existente en `dim_destinations` |
| **Postcondición** | Metadata geográfica actualizada |

**Flujo principal**:

1. Usuario edita nombre visible, coordenadas (lat, lng), país, ciudad
2. Sistema valida coordenadas: latitud (-90 a 90), longitud (-180 a 180)
3. Sistema actualiza `dim_destinations.destination_display_name`
4. Sistema conserva `destination_label` original para trazabilidad
5. Sistema actualiza `geo_catalog`

**Colecciones**: `dim_destinations`, `geo_catalog`, `user_activity_logs`

---

### CU-D05: Visualizar Mapa Mundial

| Atributo | Valor |
|----------|-------|
| **Actor** | Todos los usuarios |
| **Tipo** | Concreto |
| **Precondición** | Destinos con coordenadas cargados |
| **Postcondición** | Mapa interactivo con marcadores mostrado |

**Flujo principal**:

1. Usuario abre mapa mundial
2. Sistema consulta `dim_destinations` con coordenadas (lat, lng no nulas)
3. Sistema consulta `dim_hotels` asociados a cada destino
4. Sistema calcula precio promedio por destino
5. Frontend (Leaflet.js) renderiza marcadores coloreados por rango de precio

**Colecciones**: `dim_destinations`, `dim_hotels`, `geo_catalog`

---

## 8.4 Sub-paquete: reportes

### CU-D06: Exportar Reporte

| Atributo | Valor |
|----------|-------|
| **Actor** | Gerente / Auditor de Datos |
| **Tipo** | Concreto |
| **Precondición** | Datos cargados en `fact_hotel_reservations` |
| **Postcondición** | Archivo PDF o Excel descargado |

**Flujo principal**:

1. Usuario selecciona tipo de reporte (revenue, ocupación, calidad)
2. Usuario selecciona rango de fechas y filtros
3. Sistema consulta `fact_hotel_reservations` y dimensiones
4. Sistema genera PDF (`reports/pdf`) o Excel (`reports/xlsx`)
5. Sistema devuelve archivo para descarga

**Colecciones**: `fact_hotel_reservations`, `kpi_summary`, `dim_hotels`

---

# 9. DEPARTAMENTO: SERVICIOS AL HUÉSPED (IN-STAY)

**Descripción**: Proveer experiencia digital durante la estancia: portal Mi Estancia, chat con recepción, solicitudes de servicio, DND y objetos perdidos.  
**Actores**: Huésped, Recepcionista/Staff  
**Módulos Backend**: `instay`, `lost_and_found`  
**Módulos Frontend**: `in-stay`, `lost-and-found`  
**Sub-paquetes**: Sin sub-paquetes (6 CUs, dominio cohesivo)

---

### CU-I01: Acceder al Portal Mi Estancia

| Atributo | Valor |
|----------|-------|
| **Actor** | Huésped |
| **Tipo** | Concreto |
| **Precondición** | Reserva en estado `"checked_in"` |
| **Postcondición** | Portal con compendio del hotel mostrado |

**Flujo principal**:

1. Huésped escanea QR en habitación o accede con JWT de reserva
2. Sistema crea/valida `stay_sessions` (token único, expira al check-out)
3. Sistema carga compendio del hotel: `hotel_profile`, `hotel_policies`, `hotel_amenities`
4. Sistema carga cargos del huésped: `additional_charges`
5. Sistema carga folio y balance: `guest_folios`
6. Huésped visualiza portal con información completa del hotel

**Colecciones**: `stay_sessions`, `hotel_profile`, `hotel_policies`, `hotel_amenities`, `additional_charges`, `guest_folios`, `booking_orders`

---

### CU-I02: Enviar Mensaje por Chat

| Atributo | Valor |
|----------|-------|
| **Actor** | Huésped / Staff |
| **Tipo** | Concreto |
| **Precondición** | Sesión de estancia activa (CU-I01) |
| **Postcondición** | Mensaje enviado, staff/huésped notificado |

**Flujo principal**:

1. Huésped escribe mensaje en chat del portal
2. Sistema crea `stay_messages` con `sender = "guest"`
3. Sistema notifica a staff (`notification_log`)
4. Staff recibe notificación y abre conversación
5. Staff responde: `sender = "staff"`
6. Huésped recibe respuesta en tiempo real

**Colecciones**: `stay_messages`, `notification_log`, `stay_sessions`, `booking_orders`

---

### CU-I03: Crear Solicitud de Servicio

| Atributo | Valor |
|----------|-------|
| **Actor** | Huésped |
| **Tipo** | Concreto |
| **Precondición** | Sesión de estancia activa (CU-I01) |
| **Postcondición** | Solicitud creada, staff notificado |

**Flujo principal**:

1. Huésped selecciona tipo de servicio: `room_service`, `housekeeping`, `maintenance`, `towels`, `amenities`, `minibar`, `laundry`, `wake_up_call`, `late_checkout`, `extra_bed`, `spa`, `restaurant`, `extend_stay`
2. Huésped opcionalmente agrega descripción o notas
3. Sistema crea `stay_service_requests` con `status = "pending"`
4. Sistema notifica a staff (`notification_log`)

**Colecciones**: `stay_service_requests`, `notification_log`, `stay_sessions`

---

### CU-I04: Activar/Desactivar DND

| Atributo | Valor |
|----------|-------|
| **Actor** | Huésped |
| **Tipo** | Concreto |
| **Precondición** | Sesión de estancia activa (CU-I01) |
| **Postcondición** | Estado DND invertido |

**Flujo principal**:

1. Huésped hace clic en toggle "No Molestar" en el portal
2. Sistema lee estado actual de `dnd` desde `room_status_log`
3. Sistema invierte valor: `dnd = !dnd`
4. Sistema actualiza `room_status_log.dnd_updated_at = now()`

**Colecciones**: `room_status_log`, `stay_sessions`

---

### CU-I05: Atender Solicitudes (Staff)

| Atributo | Valor |
|----------|-------|
| **Actor** | Recepcionista / Staff |
| **Tipo** | Concreto |
| **Precondición** | Solicitudes pendientes existen |
| **Postcondición** | Solicitud atendida, huésped notificado |

**Flujo principal**:

1. Staff consulta inbox de solicitudes (`stay_service_requests` con status `"pending"`)
2. Staff actualiza estado: `pending → in_progress → completed`
3. Staff puede enviar mensaje al huésped (invoca CU-I02 como staff)
4. Sistema notifica al huésped del cambio de estado

**Colecciones**: `stay_service_requests`, `notification_log`, `stay_messages`

---

### CU-I06: Gestionar Objetos Perdidos

| Atributo | Valor |
|----------|-------|
| **Actor** | Recepcionista / Gerente |
| **Tipo** | Concreto |
| **Precondición** | Objeto encontrado en el hotel |
| **Postcondición** | Objeto registrado, reclamado o descartado |

**Flujo principal**:

1. Staff registra objeto encontrado: descripción, ubicación, quién lo reportó
2. Sistema crea `lost_and_found` con `status = "found"`
3. Huésped puede consultar objetos perdidos desde portal
4. Si huésped reclama: `status → "claimed"`
5. Si no reclamado en 90 días: `status → "disposed"`

**Colecciones**: `lost_and_found`, `booking_orders`, `user_activity_logs`

---

# APÉNDICE A: Relaciones entre Casos de Uso

## Relaciones `<<include>>` (inclusión obligatoria)

| CU Base | CU Incluido | Justificación |
|---------|-------------|---------------|
| CU-C01 Buscar Hoteles | CU-C02 Calcular Tarifa | Cada resultado necesita su precio |
| CU-C01 Buscar Hoteles | CU-C03 Validar Disponibilidad | Solo muestra hoteles con disponibilidad |
| CU-C04 Filtrar/Comparar | CU-C02 Calcular Tarifa | La comparación necesita precios |
| CU-C05 Ver Detalle | CU-C06 Consultar Reseñas | Las reseñas son parte del detalle |
| CU-C07 Solicitar Reserva | CU-C02 Calcular Tarifa | Debe calcular total antes de confirmar |
| CU-C07 Solicitar Reserva | CU-C03 Validar Disponibilidad | Debe verificar stock antes de crear |
| CU-C07 Solicitar Reserva | CU-C08 Validar Autenticación | Requiere JWT |
| CU-R02 Configurar Tarifa | CU-R01 Crear Plan | Necesita un plan existente |
| CU-B01 Generar Factura | CU-B03 Calcular Impuestos | Toda factura incluye impuestos |
| CU-B02 Registrar Pago | CU-B01 Generar Factura | Necesita factura para pagar |
| CU-O04 Check-In | CU-O08 Validar Estado | Debe validar estado previo |
| CU-O05 Check-Out | CU-B01 Generar Factura | Check-out genera factura |
| CU-O05 Check-Out | CU-B02 Registrar Pago | Check-out registra pago |
| CU-O05 Check-Out | CU-O08 Validar Estado | Debe validar estado previo |
| CU-M02 Actualizar Contenido | CU-M03 Validar Imágenes | Subida incluye validación |

## Relaciones `<<extend>>` (extensión condicional)

| CU Base | CU Extensor | Condición |
|---------|-------------|-----------|
| CU-C01 Buscar Hoteles | CU-C04 Filtrar/Comparar | Cliente elige aplicar filtros |
| CU-C09 Mis Reservas | CU-C10 Cancelar Reserva | Cliente elige cancelar |
| CU-C07 Solicitar Reserva | CU-R04 Aplicar Cupón | Cliente ingresa código de cupón |
| CU-O02 Consultar Solicitudes | CU-O03 Confirmar/Rechazar | Gerente actúa sobre solicitud |

---

# APÉNDICE B: Actores del Sistema

| Actor | Departamento | CUs |
|-------|-------------|-----|
| **Cliente / Viajero** | 1. Comercial | CU-C01, CU-C04, CU-C05, CU-C07, CU-C09, CU-C10, CU-C11, CU-R04 |
| **Revenue Manager** | 2. Revenue | CU-R01, CU-R02, CU-R03, CU-R05 |
| **Marketing Hotelero** | 3. Marketing | CU-M01, CU-M02, CU-M03, CU-M06, CU-R03 |
| **Hotel Partner** | 3, 4 | CU-M01, CU-M02, CU-M04, CU-M05, CU-O06 |
| **Recepcionista** | 4, 5 | CU-O01, CU-O04, CU-O05, CU-O10, CU-O15, CU-O16, CU-B01, CU-B02, CU-B04, CU-B05 |
| **Gerente de Hotel** | 4, 5, 8 | CU-O02, CU-O03, CU-O07, CU-O09, CU-O10, CU-O11, CU-O13, CU-O14, CU-O15, CU-O16, CU-B04, CU-B06, CU-B07, CU-B08, CU-D01, CU-D06 |
| **Personal Housekeeping** | 4 | CU-O12 |
| **Técnico** | 4 | CU-O14 |
| **Contador** | 5 | CU-B07 |
| **Gerente HR** | 6 | CU-H01, CU-H02, CU-H03 |
| **Empleado** | 6 | CU-H04, CU-H05 |
| **Super Admin** | 7 | CU-A05, CU-A06, CU-A07, CU-M06 |
| **Admin de Sistema** | 7 | CU-A05, CU-A06, CU-A07 |
| **Auditor de Datos** | 8 | CU-D02, CU-D03, CU-D04, CU-D06 |
| **Huésped** | 9 | CU-I01, CU-I02, CU-I03, CU-I04 |
| **Staff (In-Stay)** | 9 | CU-I02 (responder), CU-I05, CU-I06 |
| **Sistema** | Todos | CU-C02, CU-C03, CU-C06, CU-C08, CU-M03, CU-B03, CU-O08, CU-D03 |

---

# APÉNDICE C: Resumen por Sub-paquete

| Departamento | Sub-paquete | CUs | Colecciones |
|-------------|-------------|-----|-------------|
| 1. Comercial | busqueda | 4 | 7 |
| 1. Comercial | detalle | 2 | 6 |
| 1. Comercial | reservas-cliente | 4 | 4 |
| 1. Comercial | resenias-cliente | 1 | 2 |
| 2. Revenue | — | 5 | 6 |
| 3. Marketing | propiedades | 1 | 4 |
| 3. Marketing | contenido | 2 | 4 |
| 3. Marketing | politicas | 1 | 1 |
| 3. Marketing | amenities | 1 | 4 |
| 3. Marketing | resenias-mod | 1 | 3 |
| 4. Operaciones | reservas-mgmt | 4 | 4 |
| 4. Operaciones | checkin-checkout | 2 | 5 |
| 4. Operaciones | habitaciones | 5 | 7 |
| 4. Operaciones | housekeeping | 2 | 3 |
| 4. Operaciones | mantenimiento | 2 | 2 |
| 4. Operaciones | recepcion | 1 | 1 |
| 5. Facturación | facturas-pagos | 4 | 8 |
| 5. Facturación | cargos | 1 | 2 |
| 5. Facturación | gastos | 3 | 5 |
| 6. RRHH | — | 5 | 5 |
| 7. Administración | auth | 3 | 8 |
| 7. Administración | usuarios-roles | 3 | 4 |
| 7. Administración | configuracion | 1 | 4 |
| 8. Analítica | etl-calidad | 2 | 4 |
| 8. Analítica | dashboard | 1 | 4 |
| 8. Analítica | geo | 2 | 3 |
| 8. Analítica | reportes | 1 | 2 |
| 9. In-Stay | — | 6 | 8 |

**Total: 45 CUs | 25 Sub-paquetes | 9 Departamentos**

---

*Fin del documento — Catálogo completo de Casos de Uso del HotelData*
