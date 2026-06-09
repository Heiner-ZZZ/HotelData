# Login básico GA03

## Objetivo

Agregar autenticación web básica en FastAPI + Jinja2 usando el modelo MongoDB de seguridad creado para GA03.

## Rutas creadas

- `GET /auth/login`
- `POST /auth/login`
- `GET /auth/logout`
- `GET /auth/me`

## Funcionamiento

1. El usuario ingresa email o username y contraseña.
2. La app busca el usuario en `users`.
3. La app valida `password_hash` con `passlib` y bcrypt.
4. Si las credenciales son válidas, crea un documento en `user_sessions`.
5. La app guarda la cookie `hoteldata_session` con `HttpOnly` y `SameSite=Lax`.
6. La app registra login exitoso, login fallido y logout en `user_activity_logs`.
7. Login exitoso redirige a `/ta02`.
8. Login fallido muestra mensaje claro.

## Alcance

El login es funcional y visible, pero todavía no obliga autenticación en:

- `/ta02`
- `/ta02/crud`
- `/etl-status`

La protección de rutas queda para una fase posterior.

## Archivos principales

- `src/app/modules/auth/routes.py`
- `src/app/security/session.py`
- `src/app/templates/auth/login.html`
- `src/app/templates/auth/me.html`

## Crear superadmin

Primero inicializar el modelo de seguridad:

```powershell
python scripts/init_security_model_ga03.py
```

Usuario inicial:

- username: `superadmin`
- email: `admin@hoteldata.local`
- password temporal: `Admin12345*`

## Probar login

1. Abrir la app.
2. Ir a `/auth/login`.
3. Ingresar `superadmin` o `admin@hoteldata.local`.
4. Ingresar la contraseña temporal.
5. Confirmar redirección a `/ta02`.
6. Abrir `/auth/me` para ver la sesión activa.
7. Abrir `/auth/logout` para cerrar sesión.

## Colecciones usadas

- `users`
- `user_sessions`
- `user_activity_logs`

No se toca `fact_hotel_reservations`, dimensiones, ETL ni Airflow.
