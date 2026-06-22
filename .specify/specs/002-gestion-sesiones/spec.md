# Especificación: Gestión de Sesiones y Cierre Seguro

**Versión**: 1.0 | **Estado**: Draft | **Última actualización**: 2026-06-21

**Casos de uso TAF06**: CU-O28 (Administrar cuenta, sesión y cierre seguro)

## 1. Objetivo

Permitir que cualquier usuario autenticado cierre su sesión de forma segura, invalidando el token activo y eliminando la cookie del navegador, además de consultar el estado de su sesión actual.

## 2. Contexto

Una vez que el usuario inició sesión, necesita poder cerrarla explícitamente al terminar su trabajo. El sistema debe invalidar la sesión en el servidor (no solo borrar la cookie del lado cliente) para evitar reuso del token. También debe exponer el estado de la sesión actual para que el frontend pueda verificar autenticación.

## 3. Actores

| Actor | Descripción |
|-------|-------------|
| Todos los usuarios autenticados | Cualquier usuario con sesión activa |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe invalidar la sesión al hacer logout (marcar is_active=false en user_sessions) | Alta |
| RF-002 | El sistema debe eliminar la cookie `hoteldata_session` del navegador | Alta |
| RF-003 | El sistema debe redirigir al usuario a la página de login después del logout | Alta |
| RF-004 | El sistema debe exponer endpoint GET /api/auth/me para consultar sesión actual | Alta |
| RF-005 | El sistema debe registrar el logout en `user_activity_logs` | Alta |
| RF-006 | El sistema debe rechazar peticiones con sesión inválida o expirada (HTTP 401) | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | El logout debe ser inmediato (< 100ms) |
| RNF-002 | Las sesiones expiradas deben limpiarse automáticamente via TTL index de MongoDB |
| RNF-003 | El endpoint /api/auth/me no debe exponer el hash de la contraseña ni el token |

## 6. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-001 | Una sesión expirada no puede usarse para acceder a rutas protegidas |
| RN-002 | Al hacer logout, la sesión se invalida en servidor (no confiar solo en borrar cookie cliente) |
| RN-003 | Si un usuario hace login con sesión activa previa, la sesión anterior se invalida automáticamente |

## 7. Entradas

| Dato | Tipo | Origen |
|------|------|--------|
| Cookie `hoteldata_session` | string (token) | Navegador / Header HTTP |

## 8. Salidas

| Escenario | Respuesta |
|-----------|-----------|
| Logout exitoso | Cookie eliminada + redirección a /login + registro en activity_logs |
| Sesión expirada | HTTP 401 + redirección a /login |
| Sesión válida (me) | JSON con user_id, email, role, display_name |
| Logout sin sesión | Redirección a /login sin error |

## 9. Escenarios

### Escenario 1: Logout exitoso
```gherkin
Dado que el usuario tiene una sesión activa
Cuando accede a GET /auth/logout
Entonces el sistema elimina el documento de user_sessions
Y elimina la cookie hoteldata_session
Y redirige a /login
```

### Escenario 2: Sesión expirada
```gherkin
Dado que la sesión del usuario ha expirado (más de 8 horas)
Cuando intenta acceder a una ruta protegida
Entonces el sistema responde con HTTP 401
Y redirige al login
```

### Escenario 3: Consultar sesión actual
```gherkin
Dado que el usuario tiene una sesión activa
Cuando consulta GET /api/auth/me
Entonces el sistema responde con JSON que incluye user_id, email, role, display_name
```

## 10. Criterios de aceptación

| ID | Criterio |
|----|----------|
| CA-001 | Logout invalida la sesión en user_sessions (is_active=false) |
| CA-002 | Logout elimina la cookie del navegador |
| CA-003 | Usuario redirigido a login después de logout |
| CA-004 | GET /api/auth/me devuelve datos del usuario autenticado |
| CA-005 | GET /api/auth/me devuelve 401 si no hay sesión válida |
| CA-006 | Logout registrado en user_activity_logs |
| CA-007 | Sesión expirada automáticamente por TTL index después de 8 horas |

## 11. Restricciones

- No confiar en cookie del lado cliente para validar sesión — siempre verificar en servidor
- TTL index en `user_sessions.expires_at` para limpieza automática

## 12. Dependencias

- `server/src/app/security/session.py` — invalidate_session()
- `server/src/app/security/dependencies.py` — require_login(), get_current_user()
- `user_sessions` collection con TTL index en expires_at
- `user_activity_logs` collection para auditoría

## 13. Fuera de alcance

- Sesión persistente entre reinicios del servidor (las sesiones se pierden al reiniciar si no hay respaldo)
- Single sign-on (SSO)
- Notificación de sesión expirada vía websocket
