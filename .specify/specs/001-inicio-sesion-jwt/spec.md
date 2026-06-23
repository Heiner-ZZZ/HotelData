# Especificación: Inicio de Sesión con JWT

**Versión**: 3.0 | **Estado**: Implementado | **Última actualización**: 2026-06-22

**Casos de uso TAF06**: CU-O01 (Iniciar sesión con autenticación JWT y rol)

## 1. Objetivo

Permitir que cualquier usuario registrado del sistema (cliente, hotel partner, gerente, revenue manager, marketing, super admin, operador datos, auditor datos) acceda a la plataforma mediante autenticación JWT con validación de credenciales y asignación de sesión segura por rol.

## 2. Contexto

Todo usuario del sistema necesita autenticarse para acceder a funcionalidades protegidas. El sistema debe validar credenciales (email + contraseña), verificar el estado de la cuenta (activa/inactiva), crear una sesión segura con TTL y redirigir al usuario a su página de inicio según su rol.

## 3. Actores

| Actor | Descripción |
|-------|-------------|
| Todos los usuarios | Cliente, hotel partner, gerente, revenue manager, marketing, super admin, admin sistema, operador datos, auditor datos |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe validar email y contraseña contra la colección `users` | Alta |
| RF-002 | El sistema debe verificar que la cuenta del usuario esté activa (is_active = true) | Alta |
| RF-003 | El sistema debe crear una sesión con token seguro de 48 bytes (secrets.token_urlsafe) | Alta |
| RF-004 | El sistema debe almacenar el hash SHA-256 del token en `user_sessions` con TTL de 8 horas | Alta |
| RF-005 | El sistema debe establecer una cookie httponyl llamada `hoteldata_session` con el token | Alta |
| RF-006 | El sistema debe redirigir al usuario a su página de inicio según su rol (navigation.py) | Alta |
| RF-007 | El sistema debe rechazar credenciales inválidas sin revelar si falló email o contraseña | Alta |
| RF-008 | El sistema debe rechazar cuentas inactivas con mensaje "Cuenta desactivada" | Media |
| RF-009 | El sistema debe registrar el intento de login en `user_activity_logs` | Alta |

## 5. Requisitos no funcionales

| ID | Requisito | Descripción |
|----|-----------|-------------|
| RNF-001 | Seguridad | Contraseñas validadas con bcrypt via passlib |
| RNF-002 | Seguridad | Cookie con flags httponly, samesite=lax, secure en producción |
| RNF-003 | Rendimiento | Login debe responder en menos de 500ms |
| RNF-004 | Trazabilidad | Todo login exitoso/fallido registrado en activity logs |

## 6. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-001 | El mensaje de error para credenciales inválidas debe ser genérico: "Credenciales inválidas" |
| RN-002 | Una cuenta inactiva no puede iniciar sesión |
| RN-003 | Sesión expira después de 8 horas de inactividad |
| RN-004 | Cada usuario solo puede tener una sesión activa (se invalida la anterior al hacer login) |

## 7. Entradas

| Dato | Tipo | Origen |
|------|------|--------|
| email | string | Formulario web HTML o JSON API |
| password | string | Formulario web HTML o JSON API |

## 8. Salidas

| Escenario | Respuesta |
|-----------|-----------|
| Login exitoso | Cookie `hoteldata_session` + redirección a homepage del rol |
| Credenciales inválidas | Mensaje: "Credenciales inválidas" (sin especificar cuál campo falló) |
| Cuenta inactiva | Mensaje: "Cuenta desactivada. Contacte al administrador." |
| Error interno | HTTP 500 + log |

## 9. Escenarios

### Escenario 1: Login exitoso
```gherkin
Dado que existe un usuario registrado con email "admin@hoteldata.com"
Y su contraseña es correcta
Y su cuenta está activa
Cuando envía credenciales vía POST /api/auth/login
Entonces el sistema crea una sesión en user_sessions
Y establece la cookie hoteldata_session
Y redirige al usuario a su homepage según su rol
```

### Escenario 2: Login con credenciales inválidas
```gherkin
Dado que el usuario ingresa un email o contraseña incorrectos
Cuando intenta iniciar sesión
Entonces el sistema responde con "Credenciales inválidas"
Y no establece cookie de sesión
```

### Escenario 3: Login con cuenta inactiva
```gherkin
Dado que la cuenta del usuario está desactivada (is_active = false)
Cuando intenta iniciar sesión
Entonces el sistema responde con "Cuenta desactivada. Contacte al administrador."
```

## 10. Criterios de aceptación

| ID | Criterio |
|----|----------|
| CA-001 | Usuario con credenciales válidas y cuenta activa puede iniciar sesión |
| CA-002 | Usuario con credenciales inválidas recibe mensaje genérico sin revelar campo específico |
| CA-003 | Usuario con cuenta inactiva recibe mensaje específico de cuenta desactivada |
| CA-004 | Sesión queda registrada en user_sessions con hash SHA-256 |
| CA-005 | Login exitoso queda registrado en user_activity_logs |
| CA-006 | Redirección post-login coincide con el rol del usuario |

## 11. Restricciones

- Contraseñas almacenadas con bcrypt (passlib), nunca en texto plano
- Token de sesión: 48 bytes secrets.token_urlsafe
- Hash del token: SHA-256 antes de almacenar en DB
- Cookie httponly (no accesible desde JavaScript)
- Sesión TTL: 8 horas

## 12. Dependencias

- `server/src/app/security/session.py` — Creación y validación de sesiones
- `server/src/app/security/permissions.py` — Resolución de permisos por rol
- `passlib[bcrypt]` — Hash de contraseñas
- `python-jose` — JWT (si se requiere token además de cookie)
- `user_sessions` collection — Almacenamiento de sesiones con TTL index
- `users` collection — Datos de usuario y hash de contraseña
- `user_activity_logs` collection — Auditoría de intentos de login

## 13. Implementaciones adicionales

### Registro de usuario (CU-O01-ext)
| ID | Requisito |
|----|-----------|
| RF-010 | El sistema debe permitir registro con username, email, password mín 6 caracteres |
| RF-011 | El sistema debe asignar rol "cliente" por defecto y marcar email_verified=false |
| RF-012 | El sistema debe enviar email de verificación al registrarse |
| RF-013 | El sistema debe rechazar registro si username o email ya existen |

**Endpoint**: `POST /api/auth/register` + verificación por email

### Autenticación de dos factores (2FA) por email
| ID | Requisito |
|----|-----------|
| RF-014 | El sistema debe permitir a usuarios administradores activar 2FA |
| RF-015 | El sistema debe enviar código de 6 dígitos por email al login |
| RF-016 | El sistema debe exigir el código 2FA antes de completar autenticación |

**Endpoints**: `POST /api/auth/2fa/setup`, `/verify`, `/disable`, `/verify-login`
**Colecciones**: `two_factor_codes` (TTL), `user_2fa`

### Recuperación de contraseña
| ID | Requisito |
|----|-----------|
| RF-017 | El sistema debe enviar email con enlace de recuperación |
| RF-018 | El sistema debe generar token con expiración de 1 hora |
| RF-019 | El sistema debe invalidar sesiones activas al restablecer contraseña |

**Endpoints**: `POST /api/auth/recover`, `POST /api/auth/recover/reset`
**Colección**: `password_recovery_tokens`

### Bloqueo de cuenta por intentos fallidos
| ID | Requisito |
|----|-----------|
| RF-020 | El sistema debe incrementar `failed_login_attempts` en cada login fallido |
| RF-021 | El sistema debe bloquear la cuenta por 15 minutos tras 5 intentos fallidos |
| RF-022 | El sistema debe resetear el contador al iniciar sesión exitosamente |

**Campos**: `failed_login_attempts` (int), `locked_until` (datetime) en documento `users`

### Rate limiting en login
| ID | Requisito |
|----|-----------|
| RF-023 | El sistema debe limitar a 5 intentos por minuto por IP en POST /api/auth/login |
| RF-024 | El sistema debe devolver HTTP 429 al exceder el límite |

**Dependencia**: slowapi

### Verificación de email post-registro y cambio de email
| ID | Requisito |
|----|-----------|
| RF-025 | El sistema debe exponer GET /api/account/verify-email?token= para confirmar |
| RF-026 | El sistema debe marcar `email_verified=true` al verificar el token |
| RF-027 | El sistema debe enviar verificación al nuevo email cuando el usuario lo cambia |

**Colección**: `email_verification_tokens` (TTL index + unique token_hash)

### Gestión de sesiones del propio usuario
| ID | Requisito |
|----|-----------|
| RF-028 | El sistema debe exponer GET /api/auth/sessions para listar sesiones activas propias |
| RF-029 | El sistema debe permitir DELETE /api/auth/sessions/{id} para terminar una sesión específica |

### Refresh tokens para sesiones prolongadas
| ID | Requisito |
|----|-----------|
| RF-030 | El sistema debe generar un refresh token al hacer login con remember_me |
| RF-031 | El sistema debe exponer POST /api/auth/refresh para renovar sesión sin credenciales |
| RF-032 | El refresh token es de un solo uso con expiración de 30 días |

**Colección**: `refresh_tokens` (TTL index + unique token_hash)

### Fuera de alcance (implementable, merece spec propio)
- SSO / OAuth / Google Login
- Expiración de sesión basada en actividad
- JWT adicional al token de sesión
- Políticas de seguridad avanzadas (bloqueo geográfico, detección de anomalías)
- Rate limiting por usuario (no solo por IP)
- Pruebas de carga o rendimiento específicas

→ Ver `ideas-para-specs-dedicados.md` en la raíz del proyecto para detalles.

