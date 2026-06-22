# Desalineaciones TAF06 vs Sistema Actual

> Fecha: 2026-06-20 (actualizado: módulos implementados)
> Base: TAF06 — Estrategia y Visión Arquitectónica (HotelData, Sexto Semestre)
> Propósito: Documentar qué dice el TAF06 vs qué existe hoy en el código, para alinear el desarrollo futuro.

---

## 1. Casos de Uso Operativos (CU-O)

### 1.1 CU-O22: Registrar reseña de estancia

**TAF06 dice:**
> El cliente registra reseñas posteriores a una estancia o reserva. Las reseñas alimentan indicadores de satisfacción, confianza del huésped, reputación y oportunidades de mejora.

**Sistema actual:**
- ✅ Colección `reviews` creada en `src/app/modules/reviews/`
- ✅ API endpoints: `POST /api/reviews/`, `GET /api/reviews/`, `GET /api/reviews/{id}`, `PATCH /api/reviews/{id}/moderate`, `PATCH /api/reviews/{id}/respond`, `DELETE /api/reviews/{id}`
- ✅ Servicio con CRUD completo: `reviews/service/lifecycle.py`
- ✅ Flujo de moderación: pending → approved/rejected
- ✅ Respuesta del hotel: campo `staff_response` + `staff_response_at`
- 🔜 Fact table `Fact_Reviews` en ETL (pendiente de agregar al pipeline)
- ⚠️ UI de frontend pendiente (solo backend)

**Brecha:** RESUELTA (backend). Pendiente ETL Fact_Reviews y UI.

### 1.2 CU-O23: Moderar y responder reseña

**TAF06 dice:**
> Marketing o administración pueden moderar y responder reseñas.

**Sistema actual:**
- ✅ `PATCH /api/reviews/{id}/moderate` — cambia `moderation_status` a `approved` o `rejected`
- ✅ `PATCH /api/reviews/{id}/respond` — guarda `staff_response` del hotel
- ✅ Indexado por `moderation_status` para consultas rápidas

**Brecha:** RESUELTA (backend).

### 1.3 CU-O24: Generar comprobante o factura de reserva

**TAF06 dice:**
> El sistema asocia la reserva con comprobantes o facturas, métodos de pago y trazabilidad del estado. Fortalece la confianza del cliente y ofrece respaldo documental.

**Sistema actual:**
- ✅ Colección `reservation_invoices` creada en `src/app/modules/billing/`
- ✅ API endpoints: `POST /api/billing/invoices`, `GET /api/billing/invoices`, `GET /api/billing/invoices/{id}`, `POST /api/billing/invoices/{id}/cancel`
- ✅ Generación de `invoice_number` única (INV-YYYYMM-XXXX)
- ✅ Campos: subtotal, taxes, total, status (issued/paid/cancelled/refunded)
- 🔜 Fact table `Fact_Reservation_Invoices` en ETL (pendiente)

**Brecha:** RESUELTA (backend). Pendiente ETL.

### 1.4 CU-O25: Registrar pago asociado a reserva

**TAF06 dice:**
> Pagos asociados a reservas y confirmaciones.

**Sistema actual:**
- ✅ Colección `reservation_payments` creada en `src/app/modules/billing/`
- ✅ API endpoints: `POST /api/billing/payments`, `GET /api/billing/payments`, `GET /api/billing/payments/{id}`, `POST /api/billing/payments/{id}/refund`
- ✅ Simulación completa: método `simulated`, transición confirmed → refunded
- ✅ Al pagar, actualiza automáticamente la factura asociada a `paid`
- ✅ Al reembolsar, actualiza la factura a `refunded`
- 🔜 Fact table `Fact_Reservation_Payments` en ETL (pendiente)

**Brecha:** RESUELTA (backend, simulación). Pendiente ETL.

### 1.5 Observaciones sobre CUs Operativos existentes

| CU | Estado | Notas |
|---|---|---|
| CU-O01 a O21 | ✅ Existen | Todos implementados (login, búsqueda, reservas, check-in/out, propiedades, habitaciones, tarifas, políticas, amenities, contenido) |
| CU-O26 a O29 | ✅ Existen | Reportes, calidad, cuenta, contraseña |
| CU-O22, O23, O24, O25 | ❌ Ausentes | Ver secciones 1.1-1.4 |

---

## 2. Casos de Uso Tácticos (CU-T)

### 2.1 CU-T05: Configurar disponibilidad, bloqueos y calendario operativo

**TAF06 dice:**
> Configurar disponibilidad, bloqueos y calendario operativo. Inventario debe ser atómico ante concurrencia.

**Sistema actual:**
- ✅ Existe `room_inventory_calendar` collection con CRUD
- ✅ Existe `create_blackout_block()` para bloqueos
- ✅ `save_inventory_entry()` usa optimistic locking vía campo `version` — si se provee `expected_version`, el update falla si otro proceso modificó el registro
- ✅ Backward compatible: escrituras sin `version` usan upsert tradicional (creación)
- ⚠️ El blackout block tiene rollback manual (ya corregido en fix crítico #6)

**Brecha:** RESUELTA — optimistic locking implementado en `save_inventory_entry()`.

### 2.2 Otros CUs Tácticos

| CU | Estado | Notas |
|---|---|---|
| CU-T01: Campañas/promociones | ✅ Parcial | `promotion_campaigns` existe, sin analítica de campañas |
| CU-T02: Contratos API | ✅ Existe | FastAPI OpenAPI `/docs` |
| CU-T03: Perfil comercial | ✅ Existe | `manual_override`, `hotel_profile_changes` |
| CU-T04: Tipos de habitación | ✅ Existe | `room_types`, `hotel_rooms` |
| CU-T06: Planes tarifarios | ✅ Existe | `rate_plans`, `hotel_rate_calendar` |
| CU-T07: Políticas hoteleras | ✅ Existe | `hotel_policies` |
| CU-T08: Amenities/imágenes | ✅ Existe | `hotel_images`, `hotel_content_pages` |
| CU-T09: Usuarios/roles | ✅ Existe | JWT, roles, permisos |
| CU-T10: Auditoría | ✅ Existe | `user_activity_logs`, `hotel_profile_changes` |
| CU-T11: Monitoreo servicios | ✅ Existe | Redis, health checks |
| CU-T12: Pipeline Airflow | ✅ Existe | DAG `hoteldata_ga03_etl` con 14 tareas |
| CU-T13: Reseñas/reputación | ❌ Ausente | Depende de CU-O22/O23 |

---

## 3. Tablas de Hecho (Fact Tables)

### 3.1 Facts existentes en el modelo ETL (star schema)

| Fact Table | Estado | Colección MongoDB |
|---|---|---|
| `Fact_Hotel_Reservations` | ✅ Existe | `fact_hotel_reservations` (ETL) |
| `Fact_Hotel_Events` | ✅ Existe | `fact_hotel_events` (legacy ETL) |
| `Fact_Data_Quality_Reports` | ✅ Existe | `data_quality_reports` (ETL) |
| `Fact_ETL_Executions` | ✅ Existe | `etl_executions` (ETL) |

### 3.2 Facts que TAF06 requiere y NO existen

| Fact Table | TAF06 dice | Estado |
|---|---|---|
| `Fact_Booking_Orders` | Solicitudes y órdenes de reserva operativas | ⚠️ Existe solo como colección operacional `booking_orders`, no como fact table ETL |
| `Fact_Booking_Status_History` | Cambios de estado de reservas | ⚠️ Existe solo como colección operacional `booking_status_history` |
| `Fact_Room_Inventory_Calendar` | Inventario disponible por fecha | ⚠️ Existe solo como colección operacional `room_inventory_calendar` |
| `Fact_Hotel_Rate_Calendar` | Tarifas por fecha y plan tarifario | ⚠️ Existe solo como colección operacional `hotel_rate_calendar` |
| `Fact_Promotion_Campaigns` | Campañas, promociones y cupones | ⚠️ Existe solo como colección operacional `promotion_campaigns` |
| `Fact_Reservation_Invoices` | Comprobantes o facturas | ❌ No existe en ninguna capa |
| `Fact_Reservation_Payments` | Pagos asociados a reservas | ❌ No existe en ninguna capa |
| `Fact_Reviews` | Reseñas de huéspedes | ❌ No existe en ninguna capa |
| `Fact_User_Activity_Logs` | Actividad de usuarios | ⚠️ Existe solo como colección operacional `user_activity_logs` |
| `Fact_Hotel_Profile_Changes` | Historial de cambios de perfil | ⚠️ Existe solo como colección operacional `hotel_profile_changes` |

**Nota:** Las colecciones operacionales marcadas como ⚠️ functionan para el día a día, pero el TAF06 las lista como tablas Fact del modelo analítico. La decisión de promoverlas a fact tables ETL depende de si necesitan análisis histórico agregado o si el dato operacional es suficiente.

### 3.3 Dimensiones faltantes

| Dimensión | TAF06 dice | Estado |
|---|---|---|
| `Dim_Time` | date_key, año, mes, día, hora | ✅ `dim_dates` existe |
| `Dim_Hotel` | prop_id, nombre, rating, país | ✅ `dim_hotels` existe |
| `Dim_Destination` | srch_destination_id | ✅ `dim_destinations` existe |
| `Dim_Visitor_Country` | país/mercado visitante | ✅ `dim_visitor_countries` existe |
| `Dim_Channel_Site` | site_id, canal | ✅ `dim_sites` existe |
| `Dim_Occupancy_Profile` | adultos, niños, habitaciones | ❌ No existe como dimensión separada |
| `Dim_Stay_Length_Category` | corta/media/larga | ❌ No existe |
| `Dim_Booking_Window_Category` | last minute/corto/medio/largo | ❌ No existe |
| `Dim_Price_Category` | bajo/medio/alto/premium | ❌ No existe |
| `Dim_Promotion` | estado de promoción | ✅ `dim_promotions` existe |
| `Dim_Click_Status` | click/sin click | ✅ existe |
| `Dim_Reservation_Status` | reserva detectada/no | ✅ `dim_reservation_status` existe |
| `Dim_User_Role` | roles del sistema | ❌ No existe como dimensión analítica |
| `Dim_Room_Type` | tipo de habitación | ❌ No existe como dimensión analítica |
| `Dim_Rate_Plan` | plan tarifario | ❌ No existe como dimensión analítica |

---

## 4. Arquitectura de Datos

### 4.1 Medallion Architecture (Bronze → Silver → Gold)

**TAF06 dice:**
> Dos grandes capas: operación hotelera y modelo analítico. La operación diaria registra acciones concretas; el modelo Fact-Dim consolida esas acciones.

**Sistema actual:**
- ✅ Bronze: `data/raw/hotels.csv`
- ✅ Silver: `data/processed/` (CSV limpio)
- ✅ Gold: MongoDB fact/dim collections
- ⚠️ Las colecciones operacionales (booking_orders, etc.) no pasan por el pipeline ETL — se escriben directo vía API sin pasar por la capa Silver/Bronze
- ⚠️ No hay un pipeline unificado que consolide datos operacionales + ETL en un solo modelo Fact-Dim

### 4.2 Data Quality Framework

**TAF06 dice:**
> Reportes de calidad, registros rechazados, data_quality_reports.

**Sistema actual:**
- ✅ `data_quality_reports` collection existe
- ✅ `rejected_records` collection existe
- ✅ Quality gates definidos en ETL
- ⚠️ No hay quality gates para escrituras operacionales (API directa)

### 4.3 Data Lineage

**TAF06 dice:**
> Trazabilidad funcional: quién hizo qué, cuándo, desde qué rol.

**Sistema actual:**
- ✅ `user_activity_logs` registra acciones de usuarios
- ✅ `hotel_profile_changes` registra cambios de perfil
- ✅ `booking_status_history` registra cambios de estado
- ✅ `etl_executions` registra ejecuciones ETL
- ⚠️ No todos los endpoints operacionales registran auditoría

---

## 5. Resumen de Brechas por Severidad

### CRÍTICAS (implementadas)

| # | Brecha | TAF06 Ref | Estado |
|---|---|---|---|
| 1 | CU-O22: Reseñas de huéspedes | §11.3, §13 | ✅ Backend implementado |
| 2 | CU-O23: Moderación de reseñas | §11.3, §13 | ✅ Backend implementado |
| 3 | CU-O24: Facturación/comprobantes | §11.3, §13, §14.3 | ✅ Backend implementado |
| 4 | CU-O25: Pagos simulados | §11.3, §13, §14.3 | ✅ Backend implementado |
| 5 | Fact_Reservation_Invoices | §14.3 | 🔜 Pendiente ETL |
| 6 | Fact_Reservation_Payments | §14.3 | 🔜 Pendiente ETL |
| 7 | Fact_Reviews | §14.3 | 🔜 Pendiente ETL |

### MEDIAS (existe pero incompleto)

### MEDIAS (existe pero incompleto)

| # | Brecha | TAF06 Ref |
|---|---|---|
| 8 | CU-T05: Optimistic locking en inventory | §11.2 | ✅ Implementado en `save_inventory_entry()` con campo `version` |
| 9 | Dimensiones faltantes (Occupancy, Stay Length, Booking Window, Price Category, User Role, Room Type, Rate Plan) | §14.4 |
| 10 | Colecciones operacionales no promovidas a fact tables ETL | §14.3 |
| 11 | Sin quality gates para escrituras API directas | §13 |

### BAJAS (existe, refinable)

| # | Brecha | TAF06 Ref |
|---|---|---|
| 12 | Sin analítica de campañas (CU-T01) | §11.2 |
| 13 | Auditoría no cubre todos los endpoints | §13 |
