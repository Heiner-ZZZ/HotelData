# Ideas para Specs Dedicados

Ideas rescatables de specs 001–004, 008–010 que merecen un spec completo propio.
Última actualización: 2026-06-23 (v4 — categorización Spec 008 Gestión de Reservas).

---

## Análisis de viabilidad — Spec 002 "Fuera de alcance"

Items auto-completados por IA en spec 002 que fueron categorizados según viabilidad actual:


## 12. Búsqueda por Coordenadas Geográficas (Mapa)

**Origen**: Spec 004 (Fuera de alcance)

**Descripción**: Permitir buscar hoteles por cercanía a coordenadas (lat, lon) en lugar de solo por nombre de destino. Mostrar resultados en mapa interactivo.

**Lo que implicaría**:
- Campos `latitude`, `longitude` en `dim_hotels` (o colección separada)
- Índice 2dsphere de MongoDB para búsquedas geoespaciales
- Endpoint `GET /api/hotels/nearby?lat=40.4168&lon=-3.7038&radius=10`
- Frontend: mapa interactivo (Leaflet/Mapbox)
- **Nota**: Si dim_hotels no tiene coordenadas, primero hay que poblar desde fuente externa

**Dependencias**: Coordenadas en los datos de hoteles, librería de mapas en frontend

**Estado**: 📋 Spec dedicado

---

## 13. Tarifas Dinámicas Basadas en Demanda

**Origen**: Spec 004 (Fuera de alcance)

**Descripción**: Mostrar tarifas que varían según la demanda, ocupación actual, y eventos cercanos. En lugar de solo la tarifa mínima configurada, el sistema calcula precios dinámicos.

**Lo que implicaría**:
- Algoritmo de pricing que considera ocupación actual, histórica, eventos, estacionalidad
- Actualización frecuente de `hotel_rate_calendar` con precios dinámicos
- Reglas de negocio: precio mínimo, precio máximo, descuento por early booking
- Panel de configuración para revenue managers

**Dependencias**: Modelo de pricing, datos históricos

**Estado**: 📋 Spec dedicado

---


## 16. Recuperación de Contraseña por Email

**Origen**: Spec 003 (Implementaciones adicionales)

**Descripción**: Permitir al usuario solicitar un enlace de recuperación por email cuando olvida su contraseña. El enlace expira en 1 hora y permite establecer una nueva contraseña.

**Estado**: ✅ **IMPLEMENTADO** (2026-06-22) — Endpoints `POST /api/auth/recover` y `POST /api/auth/recover/reset`, frontend en `/recover` y `/reset`, enlace en login.

---

## 17. Destinos Alternativos cuando no hay Resultados

**Origen**: Spec 004 (Fuera de alcance — IA sugerir destinos alternativos)

**Descripción**: Cuando la búsqueda de hoteles no encuentra resultados, el sistema sugiere destinos alternativos relacionados (mismos términos/región) para que el usuario intente con otra opción.

**Lo que implicaría**:
- Función `_suggest_alternative_destinations()` en `lookups.py` que busca en `dim_destinations` por palabras compartidas
- Respuesta incluye `alternative_destinations[]` en el JSON de búsqueda vacía
- Frontend muestra chips clicables que actualizan la búsqueda

**Dependencias**: `dim_destinations` (ya existe con 6,460 registros)

**Estado**: ✅ **IMPLEMENTADO** (2026-06-22) — Backend + frontend completo.

---

## 18. Promociones y Descuentos en Resultados de Búsqueda

**Origen**: Spec 004 (Fuera de alcance)

**Descripción**: Mostrar promociones activas y descuentos directamente en los resultados de búsqueda (ej. "15% OFF en reserva anticipada"). El usuario ve el precio con descuento aplicado y la promoción destacada.

**Lo que implicaría**:
- Integración con spec 021 (promociones/cupones) para obtener promociones activas por hotel/fecha
- Campo `promotion_label`, `discounted_price` en los items de búsqueda
- Frontend: badge/tag en hotel-card con el descuento
- Lógica de pricing que aplique el mejor descuento disponible al `min_nightly_rate`

**Dependencias**: Spec 021 (promociones), `promotion_campaigns` collection

**Estado**: 📋 Spec dedicado

---

## Análisis de viabilidad — Spec 008 "Gestión de Reservas"

Items en "Fuera de alcance" y "Pendientes de evaluar" del spec 008, categorizados según viabilidad actual:

### ✅ IMPLEMENTAR AHORA (sin dependencias externas)

| # | Idea | Esfuerzo | Implementación |
|---|------|----------|----------------|
| 1 | **Estadísticas de reservas (stats)** — Backend ya tiene `get_reservation_stats()`, solo falta endpoint `GET /api/reservations/stats`. Frontend: summary cards con pending/confirmed/cancelled/rejected/checked_in/checked_out | ⭐ (30 min) | Endpoint en `routes.py` + stats cards en `reservations-list-page` |
| 2 | **Confirmar/Rechazar desde UI de staff** — Backend tiene `confirm_booking()`/`reject_booking()` en servicio pero NO expuestos como endpoints API. Frontend: botones en detalle para roles staff | ⭐⭐ (1h) | `POST /api/reservations/{id}/confirm` + `/reject` en routes.py + botones en `reservation-detail-page` |
| 3 | **Exportar reservas a CSV** — Endpoint que genera CSV desde booking_orders. Sin nuevas dependencias. | ⭐ (45 min) | `GET /api/reservations/export?format=csv` con `csv.writer` + botón descarga en list-page |

### 📋 SPEC DEDICADO (merecen diseño propio)

| # | Idea | Razón | Spec sugerido |
|---|------|-------|---------------|
| 4 | **Calendario de disponibilidad visual para staff** — Al gestionar reservas, staff ve calendario con disponibilidad por tipo de habitación por fecha | Requiere nuevo componente UI de calendario + endpoint de inventario agregado | `084-calendario-disponibilidad-staff` |
| 5 | **Gestión de reservas para grupos/eventos (multi-room, multi-guest)** — Una reserva con múltiples habitaciones y huéspedes | Cambio en estructura de `booking_orders`, nuevo flujo de reserva grupal | `085-reservas-grupos-eventos` |
| 6 | **Quejas y reclamos de clientes sobre reservas** — Sistema de tickets/reclamos asociados a una reserva | Nueva colección `complaint_tickets`, flujo de moderación, UI de gestión | `086-quejas-reclamos` |
| 7 | **Uso de códigos promocionales / descuentos aplicados a reservas** — Aplicar cupón/promoción al crear reserva | Depende de spec 021 (promociones/cupones), integración pricing | `087-codigos-promocionales-reserva` |
| 8 | **Gestión de solicitudes especiales (cama extra, accesibilidad, mascotas)** — Checkbox de solicitudes extras al reservar | Extiende `booking_orders` con campo `special_requests`, nueva UI | `088-solicitudes-especiales-reserva` |
| 9 | **Gestión de reservas multi-habitación (split booking)** — Un solo viaje con múltiples tipos de habitación en booking distinto | Cambio arquitectónico en flujo de creación de reserva | `089-split-booking` |
| 10 | **Reembolso automático dentro del flujo de cancelación** — Al cancelar, calcular monto a reembolsar y procesar | Depende de integración de pagos (spec 009), lógica de reembolso | `090-reembolso-automatico` |
| 11 | **Notificaciones automáticas al staff/cliente por email/SMS** — Email al crear/confirmar/cancelar reserva, check-in/out | Requiere sistema de notificaciones, templates, cola de envío | `091-notificaciones-reservas` |
| 12 | **Integración con calendarios externos (Google Calendar, Outlook, iCal)** — Sincronizar reservas como eventos | APIs externas, OAuth, exportación iCal | `092-integracion-calendarios` |

### 🚫 FUERA DE ALCANCE (no implementar ahora)

| # | Idea | Razón |
|---|------|-------|
| 13 | **Integración con Channel Managers / OTAs (Booking.com, Expedia)** — Sincronizar disponibilidad con plataformas externas | Requiere APIs de terceros, contratos comerciales, mapeo de esquemas |
| 14 | **Validación de datos de huéspedes (pasaportes, visas, listas negras)** — Verificar identidad contra bases externas | Datos sensibles, cumplimiento regulatorio (GDPR, RGPD), APIs externas |
| 15 | **Pagos integrados al flujo de reserva** — Ya cubierto por spec 009 | Delegado a spec 009 (Facturación y Cancelaciones) |
| 16 | **Generación automática de factura al check-out** — Ya cubierto por spec 009 | Delegado a spec 009 |
| 17 | **Chat bot para asistencia en gestión de reservas** — Ya cubierto en otros specs | Delegado a spec correspondiente |

---

## Priorización sugerida

| # | Acción | Item | Esfuerzo | Impacto | Estado |
|---|--------|------|----------|---------|--------|
| 1 | ✅ YA | Logout remoto todos dispositivos | ⭐ (1h) | Alto | ✅ IMPLEMENTADO |
| 2 | ✅ YA | Force logout por admin | ⭐ (1h) | Alto | ✅ IMPLEMENTADO |
| 3 | ✅ YA | Recuperación de contraseña por email | ⭐⭐ (2-3h) | Alto | ✅ IMPLEMENTADO |
| 4 | ✅ YA | Destinos alternativos si no hay resultados | ⭐⭐ (1-2h) | Medio | ✅ IMPLEMENTADO |
| 5 | ✅ AHORA | Expiración por inactividad (heartbeat) | ⭐⭐ (2-3h) | Medio | Pendiente |
| 6 | ✅ AHORA | Stats de reservas | ⭐ (30min) | Medio | Pendiente |
| 7 | ✅ AHORA | Confirmar/Rechazar desde staff | ⭐⭐ (1h) | Alto | Pendiente |
| 8 | ✅ AHORA | Exportar reservas a CSV | ⭐ (45min) | Medio | Pendiente |
| 9 | 📋 Spec | 2FA por email | ⭐⭐ (2d) | Alto | Pendiente |
| 10 | 📋 Spec | JWT API | ⭐⭐ (2-3d) | Alto | Pendiente |
| 11 | 📋 Spec | Rate limiting por usuario | ⭐ (1d) | Medio | Pendiente |
| 12 | 📋 Spec | Cambios masivos de perfil por admins | ⭐⭐ (1-2d) | Medio | Pendiente |
| 13 | 📋 Spec | Promociones y descuentos en búsqueda | ⭐⭐ (1-2d) | Medio | Pendiente |
| 14 | 🚫 No | SSO/OAuth | ⭐⭐⭐⭐ | Alto | Futuro |
| 15 | 🚫 No | Bloqueo geográfico | ⭐⭐ | Bajo | Futuro |
| 16 | ✅ YA | Chatbot IA hoteles similares | ⭐⭐⭐ (3-4h) | Alto | ✅ IMPLEMENTADO |
| 17 | ✅ YA | Políticas cancelación en comparación | ⭐ (0.5h) | Medio | ✅ IMPLEMENTADO |
| 18 | 📋 Spec | Calendario disponibilidad visual staff | ⭐⭐ (1-2d) | Medio | Pendiente |
| 19 | 📋 Spec | Quejas y reclamos | ⭐⭐ (1-2d) | Medio | Pendiente |
| 20 | 📋 Spec | Códigos promocionales en reservas | ⭐⭐ (1-2d) | Medio | Pendiente |
| 21 | 📋 Spec | Solicitudes especiales | ⭐⭐ (1d) | Bajo | Pendiente |
| 22 | 📋 Spec | Split booking | ⭐⭐⭐ (2-3d) | Medio | Pendiente |
| 23 | 📋 Spec | Reembolso automático | ⭐⭐⭐ (2-3d) | Medio | Pendiente |
| 24 | 📋 Spec | Notificaciones reservas | ⭐⭐⭐ (2-3d) | Medio | Pendiente |
| 25 | 📋 Spec | Integración calendarios externos | ⭐⭐⭐ (2-3d) | Bajo | Pendiente |
| 26 | 📋 Spec | Filtros personalizados por usuario | ⭐⭐ (1d) | Medio | Pendiente |
| 27 | 📋 Spec | Pricing en tiempo real | ⭐⭐⭐ (2d) | Alto | Pendiente |
| 28 | 📋 Spec | Búsqueda por coordenadas / mapa | ⭐⭐ (1-2d) | Medio | Pendiente |
| 29 | 📋 Spec | Comparación avanzada de políticas | ⭐ (0.5d) | Bajo | Pendiente |
| 30 | 📋 Spec | Filtros amenities por categorías | ⭐⭐ (1d) | Medio | Pendiente |
| 31 | 🚫 No | Comparación con OTAs externas | ⭐⭐⭐⭐ | Bajo | Futuro |
| 32 | 🚫 No | GANs / IA generación imágenes | ⭐⭐⭐⭐⭐ | Bajo | Futuro |
| 33 | ✅ YA | Hoteles similares con IA | ⭐⭐⭐ (3-4h) | Alto | ✅ IMPLEMENTADO |
| 34 | ✅ YA | Solicitud reserva desde detalle | ⭐ (0.5h) | Medio | ✅ IMPLEMENTADO |
| 35 | ✅ AHORA | Comparar hotel desde detalle | ⭐ (0.5h) | Medio | Pendiente |
| 36 | ✅ AHORA | Compartir hotel en redes sociales | ⭐ (0.5h) | Bajo | Pendiente |
| 37 | 📋 Spec | Tour virtual 360° / video hotel | ⭐⭐ (1d) | Medio | Pendiente |
| 38 | 📋 Spec | Mapa de ubicación (Google Maps) | ⭐⭐ (1d) | Medio | Pendiente |
| 39 | 📋 Spec | Mensajería interna con el hotel | ⭐⭐⭐ (2-3d) | Medio | Pendiente |
| 40 | 📋 Spec | Personalización por historial/preferencias | ⭐⭐ (1-2d) | Medio | Pendiente |
| 41 | 📋 Spec | Itinerarios / paquetes turísticos | ⭐⭐⭐ (2-3d) | Bajo | Pendiente |
| 42 | 📋 Spec | Notificaciones push/email desde detalle | ⭐⭐ (1-2d) | Medio | Pendiente |
| 43 | 📋 Spec | Chat en vivo / soporte | ⭐⭐⭐⭐ (3-4d) | Alto | Pendiente |
| 44 | 📋 Spec | Programas de fidelidad / recompensas | ⭐⭐⭐ (2-3d) | Medio | Pendiente |
| 45 | 🚫 No | Procesamiento de pagos / reservas | ⭐⭐⭐⭐ | Alto | Futuro |
| 46 | 🚫 No | Ganancias de afiliados / comisiones | ⭐⭐⭐⭐ | Bajo | Futuro |
| 47 | 🚫 No | Reseñas externas (TripAdvisor, Yelp) | ⭐⭐⭐ | Bajo | Futuro |

---

## Análisis de viabilidad — Spec 005 "Filtros y Comparación"

Items auto-completados por IA en spec 005, categorizados según viabilidad actual:

### ✅ YA IMPLEMENTADOS

| # | Idea | Ubicación |
|---|------|-----------|
| 1 | **Chatbot IA para sugerir hoteles similares** — Implementado como "Hoteles similares con IA" usando NVIDIA API, ranking por similitud en detalle del hotel | `server/src/app/modules/hotels/service/similar.py`, `GET /api/hotels/{prop_id}/similar` |
| 2 | **Políticas de cancelación/reembolso en comparación** — El endpoint `GET /api/hotels/compare` ya devuelve `policies` con `check_in`, `check_out`, y demás campos de `hotel_policies` | `server/src/app/modules/hotels/service/compare.py:82-94` |

### ✅ IMPLEMENTAR AHORA (sin dependencias externas)

Ninguno de los ítems restantes es implementable "AHORA" sin un spec dedicado. Todos requieren diseño adicional o dependencias externas.

### 📋 SPEC DEDICADO (merecen diseño propio)

| # | Idea | Razón | Spec sugerido |
|---|------|-------|---------------|
| 3 | **Personalización de filtros basada en preferencias del usuario** — Recordar filtros frecuentes por usuario (destino favorito, rango precio, amenities preferidas) | Requiere modelo de preferencias + UI de gestión | `066-filtros-preferencias-usuario` |
| 4 | **Comparación de precios en tiempo real (motor de pricing)** — Mostrar tarifas que varían según demanda/ocupación, no solo la tarifa configurada | Requiere algoritmo de pricing dinámico, depende de spec 021 (promociones) | `067-pricing-tiempo-real` |
| 5 | **Búsqueda por coordenadas geográficas (mapa)** — Buscar hoteles por cercanía a lat/lon en lugar de solo destino nominal. Mapa interactivo | Requiere coordenadas en dim_hotels + índice 2dsphere + librería de mapas | `068-busqueda-mapa` |
| 6 | **Comparación avanzada de políticas (desayuno, cancelación, mascotas)** — Mostrar diferencias específicas de políticas lado a lado con iconos | `hotel_policies` tiene datos, pero la UI de comparación mostraría filas específicas por política (no solo un objeto genérico) | `069-comparacion-politicas-avanzado` |
| 7 | **Filtros de amenities por categorías (checkboxes)** — Reemplazar el input de texto actual por checkboxes agrupados por tipo (WiFi, Piscina, Desayuno, Gimnasio, etc.) | Requiere mapeo de amenities_text a categorías + rediseño del FilterSidebar | `070-filtros-amenities-categorias` |

### 🚫 FUERA DE ALCANCE (no implementar ahora)

| # | Idea | Razón |
|---|------|-------|
| 8 | **Comparación con hoteles de otros sistemas (OTAs)** — Integrar datos de Booking, Expedia, etc. | Requiere APIs externas, contratos, y scraping; fuera del alcance del proyecto |
| 9 | **GANs para generar imágenes de habitaciones según descripción** — IA generativa de imágenes | Requiere GPU/API especializada (DALL-E, Stable Diffusion), alto costo, NVIDIA free tier no lo soporta |
| 10 | **IMG de habitaciones generadas por IA según descripción** — Similar al anterior | Misma razón que #9 |

---

## Análisis de viabilidad — Spec 006 "Detalle de Hotel"

Items auto-completados por IA en spec 006 (sección "Fuera de alcance"), categorizados según viabilidad actual:

### ✅ YA IMPLEMENTADOS

| # | Idea | Ubicación |
|---|------|-----------|
| 1 | **Hoteles similares / recomendaciones** — Implementado como "Hoteles similares con IA" usando NVIDIA API. Sección en detalle con cards de hoteles similares rankeados por IA | `server/src/app/modules/hotels/service/similar.py`, `GET /api/hotels/{prop_id}/similar`, frontend en hotel-detail-page |
| 2 | **Solicitud de reserva desde detalle** — Botón "Solicitar reserva" que navega a `/reservations/new?prop_id=X` | `hotel-detail-page.html:62-65` |

### ✅ IMPLEMENTAR AHORA (sin dependencias externas)

| # | Idea | Esfuerzo | Implementación |
|---|------|----------|----------------|
| 3 | **Comparación de hoteles desde detalle** — Botón "Comparar" en action-row que navega a `/hotels/compare?prop_id=X`. El sistema de comparación ya existe, solo falta el enlace. | ⭐ (30 min) | Añadir botón en `hotel-detail-page.html` → `RouterLink` a `/hotels/compare` con `prop_id` |
| 4 | **Compartir hotel en redes sociales** — Botón "Compartir" que usa `navigator.share()` (Web Share API) o copia el enlace al portapapeles. Sin backend. | ⭐ (30 min) | Añadir botón en `hotel-detail-page.html` + método en component TS |

### 📋 SPEC DEDICADO (merecen diseño propio)

| # | Idea | Razón | Spec sugerido |
|---|------|-------|---------------|
| 5 | **Tour virtual 360° / video del hotel** — Sección de video/tour si el hotel tiene URL de tour virtual | Requiere campo `virtual_tour_url` en `hotel_content_pages` + diseño del viewer | `071-tour-virtual-360` |
| 6 | **Mapa de ubicación (Google Maps)** — Mostrar mapa interactivo con ubicación del hotel | Requiere coordenadas `lat`/`lon` en `dim_hotels` + API key de Google Maps | `072-mapa-ubicacion` |
| 7 | **Mensajería interna con el hotel** — Sistema de mensajería para contactar al hotel directamente | Requiere nuevo módulo backend de messaging, colección `messages`, websockets | `073-mensajeria-interna` |
| 8 | **Personalización por historial/preferencias** — Mostrar contenido relevante según búsquedas/reservas previas | Requiere modelo de preferencias de usuario, tracking de eventos | `074-personalizacion-historial` |
| 9 | **Itinerarios / paquetes turísticos** — Armar paquetes hotel + actividades desde detalle | Requiere nuevo dominio de itinerarios, colecciones, UI compleja | `075-itinerarios-paquetes` |
| 10 | **Notificaciones push/email desde detalle** — "Avísame cuando baje el precio", etc. | Requiere sistema de alertas, jobs programados, plantillas de email | `076-notificaciones-alertas` |
| 11 | **Chat en vivo / soporte al cliente** — Widget de chat en detalle para preguntas | Requiere websockets, sala de chat por hotel/agente, moderación | `077-chat-en-vivo` |
| 12 | **Programas de fidelidad / recompensas** — Puntos, niveles, beneficios desde detalle | Requiere nuevo dominio de loyalty, colecciones, reglas de negocio | `078-programa-fidelidad` |

### 🚫 FUERA DE ALCANCE (no implementar ahora)

| # | Idea | Razón |
|---|------|-------|
| 13 | **Tour virtual 360° con contenido real** — Si no hay URLs de tour en los datos, no se puede mostrar | Sin datos fuente, no hay nada que implementar |
| 14 | **Procesamiento de pagos / reservas directas** — Reemplazar solicitud simulada por pago real | Requiere pasarela de pagos (Stripe, PayPal), cumplimiento PCI, flujo completo de checkout |
| 15 | **Ganancias de afiliados / comisiones** — Modelo de negocio de afiliación | Requiere plataforma de afiliados, trackeo de conversiones, pagos a afiliados |
| 16 | **Reseñas externas (TripAdvisor, Yelp)** — Integrar APIs de terceros | Requiere API keys, contratos, y manejo de rate limits de cada plataforma |
| 17 | **IA generación de imágenes** — Ya evaluado en spec 005, misma razón | Misma razón que spec 005 #9 |

---

## Análisis de viabilidad — Spec 007 "Solicitar Reserva"

Items generados de gap fixes existentes (`server/tests/test_reservations.py`) + flujos alternos del CU-O05 (`TA07_ESPECIFICACIONES.md`), categorizados según viabilidad actual:

### ✅ IMPLEMENTAR AHORA
| # | Idea | Esfuerzo | Implementación |
|---|------|----------|----------------|
| 1 | **GAP-033: Teléfono del huésped** — Agregar `guest_phone` al formulario de reserva. Backend ya lo soporta en `ReservationInput` + `build_reservation_input` + `create_booking()`, solo falta frontend. | ⭐ (30 min) | Añadir campo tel en `reservation-new-page.html`, form control en `.ts`, mapeo en DTO/mapper/model |
| 2 | **GAP-035: Status "pending" no "requested"** — Cambiar status inicial de booking_orders de "requested" a "pending" como especifica el spec. Afecta `lifecycle.py`, `cleanup.py`, `queries.py` (can_cancel), `_history_lookup.py`, `_helpers.py` (ALLOWED_STATUSES) | ⭐ (15 min) | Buscar/reemplazar "requested" → "pending" en módulo reservations |
| 3 | **Auth en POST/detail/cancel** — Los endpoints `POST /api/reservations`, `GET /{booking_id}`, `POST /{booking_id}/cancel` no requerían autenticación. Añadir `Depends(require_login)`. | ⭐ (10 min) | Añadir parámetro `current_user` con dependency en cada endpoint |
| 4 | **GAP-036: Check disponibilidad** — Validar `room_inventory_calendar` antes de crear booking. Función `_check_availability()` implementada en `lifecycle.py`. | ⭐⭐ (1h) | Integrar `_check_availability()` en `create_booking()` + añadir `POST /api/reservations/preview` |
| 5 | **GAP-034: Calcular precio total** — Obtener `hotel_rate_calendar`, calcular `total_price × rooms × nights`, almacenar en booking. | ⭐⭐ (1h) | Función `_calculate_total_price()` en `lifecycle.py` + devolver en create response |
| 6 | **GAP-032: room_type_id en booking** — Almacenar `room_type_id` en el documento booking_orders aunque no se seleccione desde UI. | ⭐ (15 min) | Campo ya en `ReservationInput`/`create_booking()`, solo propagar desde frontend si existe |
| 7 | **Price preview endpoint** — `POST /api/reservations/preview` que toma mismos datos que create pero solo valida disponibilidad + calcula precio, sin crear booking. | ⭐ (30 min) | Nuevo endpoint en `routes.py` |
| 8 | **Mostrar precio en review step** — El paso "Revisar" del formulario muestra el precio total estimado + noches + moneda obtenido del preview. | ⭐⭐ (1h) | Llamar `previewReservation` al entrar a review, mostrar `totalPrice | currency` |
| 9 | **Mostrar precio + teléfono en detalle** — La página de detalle de reserva muestra `total_price`, `currency`, `total_nights` y `guest_phone`. | ⭐ (30 min) | Añadir campos a DTO + mapper + template detail |

### 📋 SPEC DEDICADO (merecen diseño propio)
| # | Idea | Razón | Spec sugerido |
|---|------|-------|---------------|
| 10 | **Selector de tipo de habitación (RF-001)** — El spec dice "Seleccionar tipo de habitación y cantidad". Requiere que `room_types` tenga datos, UI de selector con capacidades/pricing por tipo. | Depende de datos en `room_types` + UI mediana | `079-selector-tipo-habitacion` |
| 11 | **Mostrar políticas de cancelación (RF-003)** — El resumen debería incluir política de cancelación del hotel. Requiere datos en `hotel_policies` + integración con módulo de políticas. | Depende de datos en `hotel_policies` (actualmente vacío) | `080-politicas-cancelacion-reserva` |
| 12 | **FA-01: Sugerir fechas alternativas** — Cuando no hay disponibilidad, el sistema debe sugerir fechas cercanas con inventario. Flujo complejo de búsqueda de alternativas. | Requiere lógica de búsqueda de disponibilidad en fechas cercanas + UI de sugerencias | `081-fechas-alternativas-reserva` |
| 13 | **FA-02: Redirect unauthenticated → login** — Si el usuario no ha iniciado sesión y hace clic en "Reservar", redirigir al login y regresar al flujo después de autenticar. | Flujo UX completo con redirect + session state | `082-auth-flow-reserva` |
| 14 | **GAP-037/038: Confirm/Reject desde management** — Exponer `confirm_booking()` y `reject_booking()` en UI de gestión de reservas (staff). Ya implementado en backend. | Solo falta UI de gestión | `083-confirmacion-rechazo-staff` |

### 🚫 FUERA DE ALCANCE (no implementar ahora)
| # | Idea | Razón |
|---|------|-------|
| 15 | **Pago en línea al reservar** — Reemplazar solicitud simulada por pago real con tarjeta. | Requiere pasarela de pagos (Stripe, PayPal), cumplimiento PCI-DSS, flujo completo de autorización/captura |
| 16 | **Webhook notificar gerente** — Enviar notificación push/email al gerente del hotel cuando se crea una reserva. | Requiere sistema de notificaciones, templates, servicio de email |
| 17 | **IA para sugerir upgrades/promociones** — Al crear reserva, IA sugiere room upgrade o paquete. | Misma razón que specs anteriores — cold start NVIDIA, fuera del core |
| 18 | **Multi-room-type en una solicitud** — Seleccionar múltiples tipos de habitación en una sola reserva. | Cambio arquitectónico mayor en estructura de booking_orders |
| 19 | **Auto-confirmación de reservas** — Confirmar automáticamente sin acción del gerente. | Cambio de política de negocio, requiere configuración por hotel |
| 20 | **Modificación/cancelación por cliente post-confirmación** — Permitir cambios después de confirmado. | Spec 007 lo marca explícitamente como fuera de alcance |
| 21 | **Integración con Channel Managers / OTAs** — Sincronizar disponibilidad con Booking.com, Expedia, etc. | Nuevo dominio de integraciones, APIs de terceros, mapeo de datos |
| 22 | **Validación de huéspedes contra bases externas** — Pasaportes, visas, listas negras. | Datos sensibles, cumplimiento regulatorio (GDPR, etc.) |
| 23 | **Reservas para grupos/eventos especiales** — Booking con múltiples habitaciones de diferentes tipos para grupos grandes. | Cambio arquitectónico, nuevo flujo de grupo |
| 24 | **Chat bot para asistencia en reservas** — Chatbot guiando al usuario en el flujo de reserva. | Integración con NLP, fuera del core de reservas |
| 25 | **Servicios adicionales (cama extra, accesibilidad)** — Opciones extra durante la reserva. | Nueva colección de servicios, pricing, UI de selección |
