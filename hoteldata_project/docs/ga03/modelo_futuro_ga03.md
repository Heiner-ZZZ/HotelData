# Modelo futuro GA03

Este documento define el crecimiento planificado de HotelData Hub Analytics hacia una plataforma web/responsiva de reservas hoteleras. No describe funcionalidades ya implementadas salvo cuando se indique explícitamente.

## Alcance real de GA03

GA03 no implementa login real, pasarela de pagos, reservas transaccionales, partner central ni sincronización con PMS. El avance real se concentra en:

- Preparación administrativa CSV -> PocketBase.
- ETL principal PocketBase -> JSONL -> Parquet -> MongoDB.
- `TARGET_RECORDS=300000`.
- Panel `/etl-status` para operar y monitorear GA03.
- Dashboard, consulta, calidad, auditoría y CRUD analítico existente.

## Futuro de seguridad y administración de usuarios

Colecciones planificadas:

- `users`
- `roles`
- `permissions`
- `role_permissions`
- `user_sessions`
- `user_activity_logs`
- `password_reset_tokens`
- `api_keys`

Estas colecciones permitirán registro, inicio de sesión, validación de rol, auditoría por usuario y seguridad por permisos. No existen como control funcional real en GA03.

## Futuro de experiencia de viajero

Colecciones planificadas:

- `traveler_profiles`
- `traveler_preferences`
- `traveler_saved_hotels`
- `traveler_search_history`
- `traveler_notifications`

Estas colecciones permitirán perfiles de viajero, hoteles guardados, preferencias y notificaciones.

## Futuro Partner Central

Colecciones planificadas:

- `hotel_partners`
- `hotel_partner_users`
- `hotel_ownerships`
- `hotel_staff_members`
- `partner_contracts`
- `commission_rules`
- `hotel_images`
- `hotel_policies`
- `hotel_content_pages`
- `hotel_content_changes`
- `hotel_amenities`
- `hotel_faqs`
- `destination_content`

Estas colecciones permitirán administrar propiedades, contenido, políticas, contratos y rendimiento hotelero desde una experiencia tipo partner central.

## Futuro de inventario, disponibilidad y tarifas

Colecciones planificadas:

- `room_types`
- `hotel_rooms`
- `room_amenities`
- `room_inventory_calendar`
- `room_availability_blocks`
- `blackout_dates`
- `rate_plans`
- `hotel_rate_calendar`
- `rate_rules`
- `tax_fee_rules`

Estas colecciones permitirán disponibilidad por calendario, bloqueos, tarifas por fecha y reglas comerciales.

## Futuro de promociones y reservas

Colecciones planificadas:

- `promotion_campaigns`
- `coupon_codes`
- `marketing_campaigns`
- `partner_performance_targets`
- `booking_orders`
- `booking_guests`
- `booking_status_history`
- `manual_reservations`
- `reservation_payments`
- `payment_transactions`
- `refund_requests`
- `invoices`

Estas colecciones soportarán campañas, cupones, creación de reservas, estados, pagos, reembolsos y facturación.

## Futuro de integraciones y plataforma

Colecciones planificadas:

- `pms_connections`
- `channel_manager_sync_logs`
- `external_channel_mappings`
- `webhook_events`
- `notification_events`
- `email_delivery_logs`
- `redis_cache_keys`
- `task_configurations`
- `uploaded_files`
- `system_settings`
- `feature_flags`
- `docker_service_status`

Estas colecciones permitirán integración con PMS/channel manager, eventos, notificaciones, configuración operativa y observabilidad de servicios.

## Redis planificado

Redis se considera para:

- Cache de dashboard.
- Cache de búsquedas frecuentes.
- Sesiones futuras.
- Estado temporal de jobs.
- Rate limiting futuro.

Redis no queda conectado al ETL validado de GA03.

## Docker planificado

Docker queda documentado para fases posteriores con servicios `mongo`, `redis`, `pocketbase` y `app`. La ejecución actual del proyecto no depende de Docker.
