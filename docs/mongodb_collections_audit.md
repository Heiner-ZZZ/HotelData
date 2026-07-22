# Auditoría de Colecciones MongoDB — `hoteldata_hub`

> Fecha de análisis: 2026-07-22  
> Conexión: `mongodb://localhost:27018/?directConnection=true`  
> Base de datos: `hoteldata_hub`  
> Total de colecciones: **92**

---

## 1. Resumen ejecutivo

- **92 colecciones** en total.
- **800.000 registros** en el hecho principal `fact_hotel_reservations`.
- **22 colecciones vacías**.
- Se detectan colecciones operativas bien conectadas, colecciones separadas que no referencian a otras, y colecciones legacy o duplicadas.

---

## 2. Colecciones separadas / desconectadas

Son colecciones que no tienen FKs hacia otras entidades, o cuyos vínculos son débiles/string-based, lo que las deja aisladas del grafo relacional del sistema.

| Colección | Docs | ¿Por qué está separada? | Recomendación |
|---|---|---|---|
| `geo_catalog` | 32 | Catálogo geográfico sin referencias desde `dim_hotels` ni `dim_destinations`. | Agregar `geo_catalog_id` en hoteles/destinos o usar `code` como FK formal. |
| `system_catalogs` | 4 | Maestro de catálogos sin FKs. | Documentar su uso; si es lookup, mantener como catálogo libre. |
| `system_config` | 1 | Configuración global sin relaciones. | Normal para configuración. |
| `system_currencies` | 17 | Catálogo de monedas sin FKs. | Normal; podría referenciarse desde `booking_orders.currency`. |
| `navigation` | 43 | Menú de UI; `required_permission` es string. | Considerar `permission_id` → `permissions._id` para integridad. |
| `kpi_summary` | 1 | Cache plano de KPIs. | Normal para cache. |
| `click_events` | 330 | Tiene `prop_id`/`user_id` pero nadie lo referencia. | Definir si se usa para analytics; de lo contrario marcar como legacy. |
| `data_quality_reports` | 1 | Log del ETL, autónomo. | Normal. |
| `etl_executions` | 1 | Log del ETL, autónomo. | Normal. |
| `user_activity_logs` | 1,278 | Log de actividad; nadie apunta a él. | Normal para auditoría. |
| `audit_log` | 1,457 | `entity_id` es genérico y no garantiza FK. | Mejorar `entity_id` + `entity_type` con validación o ObjectId. |

---

## 3. Colecciones por dominio

### 3.1 Analytics / ETL (dimensiones + hechos)

| Colección | Docs | Observación |
|---|---|---|
| `fact_hotel_reservations` | 800,000 | Hecho principal del GA03. |
| `dim_hotels` | 93,990 | Dimensión hotel. |
| `dim_destinations` | 7,609 | Dimensión destino. |
| `dim_visitor_countries` | 163 | Países. |
| `dim_occupancy_profile` | 148 | Perfiles de ocupación. |
| `dim_dates` | 242 | Calendario. |
| `dim_sites` | 32 | Sitios. |
| `dim_booking_window_category` | 4 | Categorías de ventana de reserva. |
| `dim_click_status` | 2 | Estados de click. |
| `dim_price_category` | 4 | Categorías de precio. |
| `dim_promotions` | 2 | Promociones. |
| `dim_reservation_status` | 2 | Estados de reserva. |
| `dim_stay_length_category` | 3 | Categorías de longitud de estancia. |

### 3.2 PMS — Reservas

| Colección | Docs | Observación |
|---|---|---|
| `booking_orders` | 12 | Ordenes de reserva. |
| `booking_guests` | 12 | Huéspedes por reserva. |
| `booking_room_guests` | 1 | Asignación de huéspedes a habitaciones. |
| `booking_status_history` | 65 | Historial de transiciones de estado. |
| `manual_reservations` | 0 | Documentada pero vacía. |

### 3.3 PMS — Habitaciones e Inventario

| Colección | Docs | Observación |
|---|---|---|
| `room_types` | 26 | Tipos de habitación. |
| `hotel_rooms` | 48 | Habitaciones físicas. |
| `room_inventory_calendar` | 105 | Disponibilidad por fecha. |
| `room_status_log` | 48 | Estado actual de habitación. |
| `room_status_history` | 29 | Historial de estado. |
| `room_availability_blocks` | 0 | Documentada, vacía. |
| `room_features` | 0 | Documentada, vacía. |
| `blackout_dates` | 1 | Fechas bloqueadas. |

### 3.4 PMS — Housekeeping y Mantenimiento

| Colección | Docs | Observación |
|---|---|---|
| `housekeeping_tasks` | 10 | Usa `room_label` en vez de `room_id`. |
| `maintenance_tasks` | 4 | Usa `room_label` en vez de `room_id`. |

### 3.5 Revenue / CRS

| Colección | Docs | Observación |
|---|---|---|
| `rate_plans` | 12 | Planes tarifarios. |
| `rate_rules` | 1 | Reglas tarifarias. |
| `hotel_rate_calendar` | 84 | Tarifa por fecha y plan. |
| `promotion_campaigns` | 6 | Campañas. |
| `coupon_codes` | 16 | Cupones. |

### 3.6 Billing / Finanzas

| Colección | Docs | Observación |
|---|---|---|
| `guest_folios` | 6 | Folios por reserva. |
| `reservation_invoices` | 8 | Facturas operativas. |
| `reservation_payments` | 5 | Pagos operativos. |
| `fact_reservation_invoices` | 8 | Hecho analytics duplicado. |
| `fact_reservation_payments` | 5 | Hecho analytics duplicado. |
| `additional_charges` | 9 | Cargos extra. |
| `expense_invoices` | 1 | Gastos; `category` es string. |
| `expense_categories` | 0 | Documentada, vacía. |
| `expense_budget` | 0 | Documentada, vacía. |
| `ledger_transactions` | 32 | Asientos contables. |
| `chart_of_accounts` | 21 | Plan de cuentas. |
| `platform_earnings` | 7 | Comisiones. |

### 3.7 Identidad y Permisos

| Colección | Docs | Observación |
|---|---|---|
| `users` | 13 | Usuarios. |
| `user_sessions` | 501 | Sesiones. |
| `refresh_tokens` | 3 | Tokens de refresh. |
| `pending_registrations` | 5 | Registros pendientes. |
| `roles` | 10 | Roles con permisos embebidos. |
| `permissions` | 119 | Permisos atómicos. |
| `user_favorites` | 4 | Favoritos. |

### 3.8 RRHH

| Colección | Docs | Observación |
|---|---|---|
| `employees` | 5 | Empleados. |
| `employee_departments` | 5 | Departamentos. |
| `employee_shifts` | 1 | Turnos. |
| `employee_documents` | 0 | Probable legacy. |

### 3.9 In-Stay / CRM

| Colección | Docs | Observación |
|---|---|---|
| `stay_sessions` | 4 | Sesiones del huésped. |
| `stay_service_requests` | 51 | Solicitudes in-stay. |
| `stay_messages` | 0 | Vacía. |
| `reviews` | 0 | Vacía. |
| `review_reports` | 0 | Vacía. |
| `fact_reviews` | 0 | Vacía. |
| `lost_and_found` | 0 | Vacía. |

### 3.10 Partner / Contenido

| Colección | Docs | Observación |
|---|---|---|
| `hotel_content_pages` | 6 | Contenido del hotel. |
| `hotel_content_changes` | 28 | Auditoría de contenido. |
| `hotel_profile_changes` | 4 | Cambios de perfil. |
| `hotel_policies` | 5 | Políticas. |
| `hotel_images` | 0 | Vacía; puede estar reemplazada por GridFS. |
| `hotel_products` | 0 | No documentada; probable legacy. |

### 3.11 GridFS

| Colección | Docs | Observación |
|---|---|---|
| `fs.files` | 3 | Archivos. |
| `fs.chunks` | 7 | Chunks de archivos. |

### 3.12 Auditoría / Logs / Outbox

| Colección | Docs | Observación |
|---|---|---|
| `audit_log` | 1,457 | Auditoría del partner. |
| `user_activity_logs` | 1,278 | Actividad de usuarios. |
| `notification_log` | 141 | Notificaciones enviadas. |
| `outbox` | 7 | Outbox del CDC. |
| `click_events` | 330 | Eventos de tracking. |
| `data_quality_reports` | 1 | Reportes ETL. |
| `etl_executions` | 1 | Ejecuciones ETL. |

---

## 4. Listado completo de las 92 colecciones

| # | Colección | Docs | Dominio |
|---|---:|---:|---|
| 1 | `additional_charges` | 9 | Billing |
| 2 | `amenity_stock` | 0 | Legacy / por revisar |
| 3 | `audit_log` | 1,457 | Auditoría |
| 4 | `blackout_dates` | 1 | Inventario |
| 5 | `booking_guests` | 12 | Reservas |
| 6 | `booking_orders` | 12 | Reservas |
| 7 | `booking_room_guests` | 1 | Reservas |
| 8 | `booking_status_history` | 65 | Reservas |
| 9 | `chart_of_accounts` | 21 | Finanzas |
| 10 | `click_events` | 330 | Tracking |
| 11 | `commission_rates` | 0 | Configuración |
| 12 | `coupon_codes` | 16 | Revenue |
| 13 | `data_quality_reports` | 1 | ETL |
| 14 | `dim_booking_window_category` | 4 | Analytics |
| 15 | `dim_click_status` | 2 | Analytics |
| 16 | `dim_dates` | 242 | Analytics |
| 17 | `dim_destinations` | 7,609 | Analytics |
| 18 | `dim_hotels` | 93,990 | Analytics |
| 19 | `dim_occupancy_profile` | 148 | Analytics |
| 20 | `dim_price_category` | 4 | Analytics |
| 21 | `dim_promotions` | 2 | Analytics |
| 22 | `dim_reservation_status` | 2 | Analytics |
| 23 | `dim_sites` | 32 | Analytics |
| 24 | `dim_stay_length_category` | 3 | Analytics |
| 25 | `dim_visitor_countries` | 163 | Analytics |
| 26 | `email_verification_tokens` | 0 | Legacy |
| 27 | `employee_departments` | 5 | RRHH |
| 28 | `employee_documents` | 0 | Legacy |
| 29 | `employee_shifts` | 1 | RRHH |
| 30 | `employees` | 5 | RRHH |
| 31 | `etl_executions` | 1 | ETL |
| 32 | `expense_budget` | 0 | Finanzas |
| 33 | `expense_categories` | 0 | Finanzas |
| 34 | `expense_invoices` | 1 | Finanzas |
| 35 | `fact_hotel_reservations` | 800,000 | Analytics |
| 36 | `fact_reservation_invoices` | 8 | Analytics |
| 37 | `fact_reservation_payments` | 5 | Analytics |
| 38 | `fact_reviews` | 0 | Analytics |
| 39 | `fs.chunks` | 7 | GridFS |
| 40 | `fs.files` | 3 | GridFS |
| 41 | `geo_catalog` | 32 | Maestro |
| 42 | `guest_folios` | 6 | Billing |
| 43 | `hotel_content_changes` | 28 | Partner |
| 44 | `hotel_content_pages` | 6 | Partner |
| 45 | `hotel_images` | 0 | Partner |
| 46 | `hotel_policies` | 5 | Partner |
| 47 | `hotel_products` | 0 | Legacy |
| 48 | `hotel_profile_changes` | 4 | Partner |
| 49 | `hotel_rate_calendar` | 84 | Revenue |
| 50 | `hotel_rooms` | 48 | Habitaciones |
| 51 | `housekeeping_tasks` | 10 | Housekeeping |
| 52 | `kpi_summary` | 1 | Cache |
| 53 | `ledger_transactions` | 32 | Finanzas |
| 54 | `lost_and_found` | 0 | CRM |
| 55 | `maintenance_tasks` | 4 | Mantenimiento |
| 56 | `manual_reservations` | 0 | Reservas |
| 57 | `navigation` | 43 | UI |
| 58 | `notification_log` | 141 | Notificaciones |
| 59 | `outbox` | 7 | CDC |
| 60 | `password_recovery_tokens` | 0 | Legacy |
| 61 | `pending_registrations` | 5 | Auth |
| 62 | `permissions` | 119 | Auth |
| 63 | `platform_earnings` | 7 | Finanzas |
| 64 | `promotion_campaigns` | 6 | Revenue |
| 65 | `rate_plans` | 12 | Revenue |
| 66 | `rate_rules` | 1 | Revenue |
| 67 | `reception_shifts` | 0 | PMS |
| 68 | `refresh_tokens` | 3 | Auth |
| 69 | `reservation_invoices` | 8 | Billing |
| 70 | `reservation_payments` | 5 | Billing |
| 71 | `review_reports` | 0 | CRM |
| 72 | `reviews` | 0 | CRM |
| 73 | `roles` | 10 | Auth |
| 74 | `room_availability_blocks` | 0 | Inventario |
| 75 | `room_features` | 0 | Habitaciones |
| 76 | `room_inventory_calendar` | 105 | Inventario |
| 77 | `room_status_history` | 29 | Housekeeping |
| 78 | `room_status_log` | 48 | Housekeeping |
| 79 | `room_types` | 26 | Habitaciones |
| 80 | `stay_messages` | 0 | CRM |
| 81 | `stay_service_requests` | 51 | CRM |
| 82 | `stay_sessions` | 4 | CRM |
| 83 | `system_catalogs` | 4 | Maestro |
| 84 | `system_config` | 1 | Configuración |
| 85 | `system_currencies` | 17 | Maestro |
| 86 | `tax_rates` | 0 | Configuración |
| 87 | `two_factor_codes` | 0 | Legacy |
| 88 | `user_2fa` | 0 | Legacy |
| 89 | `user_activity_logs` | 1,278 | Auditoría |
| 90 | `user_favorites` | 4 | Auth |
| 91 | `user_sessions` | 501 | Auth |
| 92 | `users` | 13 | Auth |

---

## 5. Relaciones por ID que faltan o son débiles

| Colección | Campo actual | Problema | FK recomendada |
|---|---|---|---|
| `housekeeping_tasks` | `room_label` | String no enlazable | `room_id` → `hotel_rooms._id` |
| `maintenance_tasks` | `room_label` | String no enlazable | `room_id` → `hotel_rooms._id` |
| `room_status_history` | `room_label` | String no enlazable | `room_id` → `hotel_rooms._id` |
| `stay_service_requests` | `room_label` | String no enlazable | `room_id` → `hotel_rooms._id` |
| `expense_invoices` | `category` | String libre | `category_id` → `expense_categories._id` |
| `booking_orders` | `room_type_id` | Solo tipo, no habitación | `room_id` → `hotel_rooms._id` (opcional) |
| `geo_catalog` | — | No referenciado | `geo_catalog_id` en hoteles/destinos |
| `navigation` | `required_permission` | String libre | `permission_id` → `permissions._id` |

---

## 6. Colecciones legacy o candidatas a eliminación

### Probables legacy (vacías y no documentadas)

| Colección | Docs | Acción recomendada |
|---|---|---|
| `hotel_products` | 0 | Eliminar tras verificar que ningún código la usa. |
| `amenity_stock` | 0 | Revisar si es reemplazo de `hotel_amenities`; si no, eliminar. |
| `employee_documents` | 0 | Eliminar si no hay endpoints que la usen. |
| `password_recovery_tokens` | 0 | Verificar flujo de recuperación; si se usa otra colección, eliminar. |
| `two_factor_codes` | 0 | Legacy, eliminar. |
| `user_2fa` | 0 | Legacy, eliminar. |
| `email_verification_tokens` | 0 | Revisar si `pending_registrations` la reemplazó. |

### Vacías pero del modelo actual (no eliminar sin confirmar)

| Colección | Docs | Nota |
|---|---|---|
| `manual_reservations` | 0 | Documentada en `knowledge.md`. |
| `room_features` | 0 | Documentada. |
| `hotel_images` | 0 | Documentada; puede usar GridFS. |
| `room_availability_blocks` | 0 | Documentada. |
| `reception_shifts` | 0 | Documentada. |
| `tax_rates` | 0 | Documentada. |
| `commission_rates` | 0 | Documentada. |
| `expense_categories` | 0 | Documentada. |
| `expense_budget` | 0 | Documentada. |
| `lost_and_found` | 0 | Documentada como `lost_items`. |
| `reviews` / `review_reports` / `fact_reviews` | 0 | Módulo CRM no activo. |

---

## 7. Conclusiones y próximos pasos

1. **Prioridad alta**: agregar `room_id` real a `housekeeping_tasks`, `maintenance_tasks`, `room_status_history` y `stay_service_requests` para dejar de depender de `room_label`.
2. **Prioridad media**: decidir si los duplicados `fact_reservation_invoices`/`fact_reservation_payments` se mantienen o se consolidan.
3. **Limpieza**: eliminar o confirmar el uso de las colecciones legacy vacías listadas arriba.
4. **Conexión geográfica**: vincular `geo_catalog` con `dim_hotels`/`dim_destinations` para aprovechar el catálogo geográfico.
