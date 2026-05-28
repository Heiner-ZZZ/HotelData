# Diseño de base de datos GA03

## Estado técnico real

- TASK_NUMBER: `03`
- TARGET_RECORDS: `300000`
- PocketBase collection: `hotel_reservation_events_03`
- MongoDB database: `hoteldata_hub`
- Hecho principal: `fact_hotel_reservations`
- DAG real: `hoteldata_reservas_03_pipeline`
- JSONL real: `data/staging/reservas_hoteleras_03_extract.jsonl`
- Parquet real: `data/processed/reservas_hoteleras_03.parquet`
- Reportes reales:
  - `data/reports/reporte_ejecucion_reservas_03.json`
  - `data/reports/reporte_calidad_reservas_03.json`
  - `data/reports/validacion_dataset_reservas_03.json`

## Separación de flujo

CSV -> PocketBase es preparación administrativa de la fuente operacional. No carga directo a MongoDB.

PocketBase -> JSONL -> Parquet -> MongoDB es el ETL principal validado para GA03.

## 1. Modelo actual implementado

### Hechos

| Colección | Rol | Estado |
| --- | --- | --- |
| `fact_hotel_reservations` | Hecho principal de reservas hoteleras para análisis dimensional. | Implementado |
| `fact_hotel_events` | Hecho histórico de eventos hoteleros usado por vistas operativas existentes. | Implementado |

### 12 dimensiones activas

| Colección | Descripción | Estado |
| --- | --- | --- |
| `dim_hotels` | Dimensión de hoteles por `prop_id`. | Implementado |
| `dim_destinations` | Dimensión de destinos por `srch_destination_id`. | Implementado |
| `dim_visitor_countries` | País de origen del visitante. | Implementado |
| `dim_sites` | Sitio o canal de origen. | Implementado |
| `dim_dates` | Calendario analítico por `date_key`. | Implementado |
| `dim_promotions` | Estado de promoción. | Implementado |
| `dim_click_status` | Estado de clic. | Implementado |
| `dim_reservation_status` | Estado de reserva. | Implementado |
| `dim_occupancy_profile` | Perfil de ocupación. | Implementado |
| `dim_stay_length_category` | Categoría de duración de estancia. | Implementado |
| `dim_booking_window_category` | Categoría de anticipación de reserva. | Implementado |
| `dim_price_category` | Categoría de precio. | Implementado |

### Colecciones de control

| Colección | Descripción | Estado |
| --- | --- | --- |
| `etl_executions` | Bitácora de ejecuciones ETL. | Implementado |
| `data_quality_reports` | Reportes de calidad consolidados. | Implementado |
| `rejected_records` | Registros rechazados por reglas de calidad. | Implementado |

### Colecciones documentales/operativas actuales

| Colección | Descripción | Estado |
| --- | --- | --- |
| `hotels` | Entidad documental de hotel. | Implementado |
| `locations` | Ubicaciones de hotel. | Implementado |
| `contacts` | Contactos de hotel. | Implementado |
| `websites` | Sitios web de hotel. | Implementado |
| `facilities` | Servicios o instalaciones. | Implementado |
| `attractions` | Atracciones cercanas. | Implementado |
| `hotel_quality` | Calidad documental de hotel. | Implementado |
| `dataset_container` | Metadatos de dataset. | Implementado |
| `system_catalogs` | Catálogos operativos del sistema. | Implementado |
| `search_logs` | Registro de búsquedas o consultas. | Implementado |

### Colecciones legadas

| Colección | Descripción | Estado |
| --- | --- | --- |
| `dim_countries` | Dimensión legada sin uso principal actual. | Legada |
| `dim_date` | Dimensión legada reemplazada por `dim_dates`. | Legada |

## 2. Modelo futuro planificado

Las siguientes colecciones son diseño futuro. No forman parte del alcance implementado de GA03 y no deben interpretarse como tablas reales existentes.

### Seguridad, usuarios y sesiones

| Colección planificada | Propósito |
| --- | --- |
| `users` | Usuarios de la plataforma. |
| `roles` | Roles asignables. |
| `permissions` | Permisos atómicos. |
| `role_permissions` | Relación rol-permiso. |
| `user_sessions` | Sesiones activas e históricas. |
| `user_activity_logs` | Auditoría de acciones de usuario. |
| `password_reset_tokens` | Recuperación de contraseña. |
| `api_keys` | Llaves para integraciones controladas. |

### Perfil de viajero

| Colección planificada | Propósito |
| --- | --- |
| `traveler_profiles` | Perfil de viajero. |
| `traveler_preferences` | Preferencias de búsqueda y estadía. |
| `traveler_saved_hotels` | Hoteles guardados. |
| `traveler_search_history` | Historial de búsquedas. |
| `traveler_notifications` | Notificaciones del viajero. |

### Partner central y contenido hotelero

| Colección planificada | Propósito |
| --- | --- |
| `hotel_partners` | Socios hoteleros. |
| `hotel_partner_users` | Usuarios asociados a partner. |
| `hotel_ownerships` | Relación partner-hotel. |
| `hotel_staff_members` | Personal vinculado a hotel. |
| `partner_contracts` | Contratos comerciales. |
| `commission_rules` | Reglas de comisión. |
| `hotel_images` | Imágenes del hotel. |
| `hotel_policies` | Políticas del hotel. |
| `hotel_content_pages` | Contenido descriptivo. |
| `hotel_content_changes` | Historial de cambios de contenido. |
| `hotel_amenities` | Amenidades del hotel. |
| `hotel_faqs` | Preguntas frecuentes. |
| `destination_content` | Contenido editorial de destinos. |

### Habitaciones, inventario y disponibilidad

| Colección planificada | Propósito |
| --- | --- |
| `room_types` | Tipos de habitación. |
| `hotel_rooms` | Habitaciones o unidades por hotel. |
| `room_amenities` | Amenidades por habitación. |
| `room_inventory_calendar` | Inventario por fecha. |
| `room_availability_blocks` | Bloqueos de disponibilidad. |
| `blackout_dates` | Fechas no comercializables. |

### Tarifas, promociones y revenue

| Colección planificada | Propósito |
| --- | --- |
| `rate_plans` | Planes tarifarios. |
| `hotel_rate_calendar` | Tarifas por fecha. |
| `rate_rules` | Reglas de tarifa. |
| `tax_fee_rules` | Impuestos y cargos. |
| `promotion_campaigns` | Campañas promocionales. |
| `coupon_codes` | Cupones. |
| `marketing_campaigns` | Campañas de marketing. |
| `partner_performance_targets` | Objetivos por partner. |

### Reservas, pagos y documentos comerciales

| Colección planificada | Propósito |
| --- | --- |
| `booking_orders` | Órdenes de reserva. |
| `booking_guests` | Huéspedes por reserva. |
| `booking_status_history` | Historial de estados de reserva. |
| `manual_reservations` | Reservas manuales operativas. |
| `reservation_payments` | Pagos asociados a reserva. |
| `payment_transactions` | Transacciones de pago. |
| `refund_requests` | Solicitudes de reembolso. |
| `invoices` | Facturas. |

### Integraciones, eventos y plataforma

| Colección planificada | Propósito |
| --- | --- |
| `pms_connections` | Conexiones PMS. |
| `channel_manager_sync_logs` | Logs de sincronización con channel manager. |
| `external_channel_mappings` | Mapeos de canales externos. |
| `webhook_events` | Eventos recibidos por webhook. |
| `notification_events` | Eventos de notificación. |
| `email_delivery_logs` | Entrega de correos. |
| `redis_cache_keys` | Registro documental de claves cacheadas. |
| `task_configurations` | Configuraciones por tarea. |
| `uploaded_files` | Archivos cargados por administración. |
| `system_settings` | Configuración global. |
| `feature_flags` | Activación gradual de funcionalidades. |
| `docker_service_status` | Estado documentado de servicios Docker. |

## Lectura SDD

- Requisito: GA03 trabaja con `TARGET_RECORDS=300000`.
- Diseño: fuente operacional en PocketBase y persistencia analítica en MongoDB.
- Tareas: preparar fuente, validar dataset, ejecutar ETL, generar reportes.
- Evidencia: `/etl-status`, reportes GA03, DAG `hoteldata_reservas_03_pipeline`, Parquet y MongoDB.
