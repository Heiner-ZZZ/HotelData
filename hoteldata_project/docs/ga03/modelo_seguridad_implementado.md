# Modelo de seguridad implementado GA03

## Objetivo

Inicializar un modelo base de seguridad en MongoDB para HotelData Hub Analytics sin romper TA02/GA03 y sin tocar ETL, Airflow, hechos ni dimensiones.

## Script

```powershell
python scripts/init_security_model_ga03.py
```

El script usa `MONGO_URI` y `MONGO_DATABASE` desde `.env`.

## Colecciones creadas o verificadas

- `users`
- `roles`
- `permissions`
- `role_permissions`
- `user_sessions`
- `user_activity_logs`

## Índices únicos

- `users.email`
- `users.username`
- `roles.role_name`
- `permissions.permission_code`
- `role_permissions.role_id + role_permissions.permission_id`
- `user_sessions.session_token` con índice sparse
- `user_activity_logs.event_key` con índice sparse

## Roles base

- `super_admin`
- `admin_sistema`
- `operador_datos`
- `auditor_datos`
- `hotel_partner`
- `gerente_hotel`
- `revenue_manager`
- `marketing_hotelero`
- `cliente`

## Permisos base

- `dashboard.read`
- `crud.read`
- `crud.write`
- `etl.execute`
- `etl.read`
- `audit.read`
- `users.manage`
- `hotels.manage`
- `reservations.manage`
- `revenue.read`
- `revenue.manage`

## Usuario inicial

El script crea el usuario inicial solo si no existe:

- username: `superadmin`
- email: `admin@hoteldata.local`
- role: `super_admin`
- password temporal: definida por el script y almacenada como hash bcrypt con `passlib`

El usuario se crea con:

- `temporary_password=true`
- `must_change_password=true`
- `is_active=true`

## Auditoría

El script registra la inicialización en `user_activity_logs` con el evento:

- `ga03_security_model_initialized`

La acción se registra de forma idempotente para evitar duplicar el evento base.

## Reglas de seguridad de la inicialización

- Es idempotente.
- No borra usuarios existentes.
- No modifica `fact_hotel_reservations`.
- No modifica dimensiones.
- No ejecuta ETL.
- No modifica DAGs.

## Estado funcional

Este modelo crea las colecciones reales de seguridad y sus datos base. La autenticación web completa, sesiones reales y protección de rutas quedan para la siguiente fase de integración.
