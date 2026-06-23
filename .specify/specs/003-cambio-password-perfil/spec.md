# Especificación: Cambio de Contraseña y Actualización de Perfil

**Versión**: 2.0 | **Estado**: Implementado | **Última actualización**: 2026-06-22

**Casos de uso TAF06**: CU-O29 (Cambiar contraseña y actualizar perfil de usuario)

## 1. Objetivo

Permitir que cualquier usuario autenticado cambie su contraseña (verificando la actual primero), actualice su perfil (display_name, email, datos personales), y suba un avatar. Toda modificación debe quedar registrada en auditoría.

## 2. Contexto

Los usuarios necesitan mantener su cuenta segura mediante cambios periódicos de contraseña, y actualizar sus datos de perfil (nombre, email, preferencias). El sistema debe validar la contraseña actual antes de permitir el cambio, y registrar la actividad para trazabilidad.

## 3. Actores

| Actor | Descripción |
|-------|-------------|
| Todos los usuarios autenticados | Cualquier usuario con sesión activa |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir cambiar contraseña verificando la contraseña actual | Alta |
| RF-002 | El sistema debe validar que la nueva contraseña cumpla políticas de seguridad (mín. 8 caracteres, mayúscula, minúscula, dígito, no común) | Alta |
| RF-003 | El sistema debe hashear la nueva contraseña con bcrypt antes de almacenar | Alta |
| RF-004 | El sistema debe invalidar todas las sesiones activas después del cambio de contraseña | Media |
| RF-005 | El sistema debe permitir actualizar display_name, email, phone, address, preferencias | Alta |
| RF-006 | El sistema debe permitir subir avatar (imagen) | Baja |
| RF-007 | El sistema debe registrar cambios de perfil y contraseña en user_activity_logs | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | La contraseña nunca debe viajar en texto plano por la URL (solo en body de POST/PUT) |
| RNF-002 | El avatar debe validarse como imagen (Content-Type, tamaño máximo 2MB) |
| RNF-003 | Respuesta del perfil no debe incluir el hash de la contraseña |

## 6. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-001 | La nueva contraseña no puede ser igual a la actual ni a ninguna de las últimas 5 |
| RN-002 | Contraseña debe tener al menos 8 caracteres, 1 mayúscula, 1 minúscula, 1 dígito |
| RN-003 | El cambio de contraseña invalida sesiones activas (obliga a re-login) |
| RN-004 | El email es único en el sistema — no se puede cambiar a un email ya registrado |

## 7. Entradas

| Dato | Tipo | Endpoint |
|------|------|----------|
| current_password | string | PUT /api/settings/password |
| new_password | string | PUT /api/settings/password |
| display_name | string | PUT /api/account/profile |
| phone | string | PUT /api/account/profile |
| address | string | PUT /api/account/profile |
| avatar | file (image) | POST /api/account/profile/avatar |

## 8. Salidas

| Escenario | Respuesta |
|-----------|-----------|
| Contraseña cambiada | 200 OK + mensaje confirmación + invalidación de sesiones |
| Contraseña actual incorrecta | 400 Bad Request + "Contraseña actual incorrecta" |
| Perfil actualizado | 200 OK + JSON con perfil actualizado |
| Avatar subido | 200 OK + URL del avatar |

## 9. Escenarios

### Escenario 1: Cambio de contraseña exitoso
```gherkin
Dado que el usuario está autenticado
Y conoce su contraseña actual
Cuando envía current_password y new_password a PUT /api/settings/password
Entonces el sistema valida la contraseña actual con bcrypt
Y valida que no sea una contraseña común
Y valida que no esté en el historial de últimas 5 contraseñas
Y valida fuerza (mayúscula, minúscula, dígito, 8+ caracteres)
Y hashea la nueva contraseña
Y la almacena en users.password_hash
Y agrega la anterior a password_history
Y invalida todas las sesiones activas
Y envía email de notificación
Y registra el cambio en user_activity_logs
```

### Escenario 2: Contraseña actual incorrecta
```gherkin
Dado que el usuario está autenticado
Y no recuerda su contraseña actual
Cuando envía una contraseña actual incorrecta
Entonces el sistema responde 400
Y no modifica la contraseña
```

### Escenario 3: Actualización de perfil
```gherkin
Dado que el usuario está autenticado
Cuando envía datos de perfil a PUT /api/account/profile
Entonces el sistema valida formato de teléfono
Y actualiza el sub-documento profile del usuario
Y si el email cambió, envía verificación al nuevo + notificación al antiguo
Y responde con el perfil actualizado
```

## 10. Criterios de aceptación

| ID | Criterio |
|----|----------|
| CA-001 | Cambio de contraseña funciona con contraseña actual correcta |
| CA-002 | Cambio de contraseña falla con contraseña actual incorrecta |
| CA-003 | Cambio de contraseña falla con contraseña común (12345678, password, etc.) |
| CA-004 | Cambio de contraseña falla si está en historial de últimas 5 |
| CA-005 | Nueva contraseña hasheada con bcrypt (verificable en DB) |
| CA-006 | Todas las sesiones activas se invalidan tras cambio de contraseña |
| CA-007 | Email de notificación se envía al cambiar contraseña |
| CA-008 | Perfil actualizado se refleja en GET /api/account/profile |
| CA-009 | Cambios registrados en user_activity_logs |
| CA-010 | Avatar se almacena y es accesible por URL |
| CA-011 | Teléfono inválido es rechazado con 400 |

## 11. Restricciones

- Contraseñas almacenadas con bcrypt passlib
- Archivo de avatar: máximo 2MB, formatos image/jpeg, image/png
- No enviar contraseñas en GET o URL params
- Teléfono: solo dígitos, espacios, +, -, (, ) — 7 a 20 caracteres

## 12. Dependencias

- `server/src/app/modules/account/routes.py` — Profile management routes + services
- `server/src/app/modules/settings/routes.py` — Password change routes + services
- `server/src/app/modules/settings/schemas.py` — PasswordChange con validación de fuerza Pydantic
- `server/src/app/security/session.py` — invalidate_user_sessions()
- `passlib[bcrypt]` — Hash de contraseñas
- `users` collection — Almacenamiento de perfil y contraseña
- `user_activity_logs` collection — Auditoría
- `gridfs` (pymongo) — Almacenamiento y servicio de avatares en MongoDB

## 13. Implementaciones adicionales

### Recuperación de contraseña por email
| ID | Requisito |
|----|-----------|
| RF-008 | El sistema debe enviar email con enlace de recuperación |
| RF-009 | El sistema debe generar token con expiración de 1 hora |
| RF-010 | El sistema debe invalidar sesiones activas al restablecer contraseña |

**Endpoints**: `POST /api/auth/recover`, `POST /api/auth/recover/reset`
**Colección**: `password_recovery_tokens`

### Verificación de email después del cambio
| ID | Requisito |
|----|-----------|
| RF-011 | El sistema debe enviar verificación al nuevo email cuando el usuario lo cambia |
| RF-012 | El sistema debe notificar al email antiguo del cambio |

### Historial de contraseñas anteriores
| ID | Requisito |
|----|-----------|
| RF-013 | El sistema debe mantener historial de últimas 5 contraseñas hasheadas |
| RF-014 | El sistema debe rechazar nueva contraseña si está en el historial |

**Campo**: `password_history` (array de bcrypt hashes) en documento `users`

### Validación de fuerza de contraseña
| ID | Requisito |
|----|-----------|
| RF-015 | El sistema debe validar mín. 8 caracteres, 1 mayúscula, 1 minúscula, 1 dígito |
| RF-016 | El sistema debe rechazar contraseñas comunes (blacklist de 15+ passwords) |

**Implementación**: `@field_validator` en Pydantic `PasswordChange` + blacklist en ruta

### Validación de formato de teléfono en perfil
| ID | Requisito |
|----|-----------|
| RF-017 | El sistema debe validar formato de teléfono (solo dígitos, espacios, +, -, (, ) — 7 a 20 caracteres) |
| RF-018 | El sistema debe validar formato básico de notification_email |

### Notificaciones por email en cambios de cuenta
| ID | Requisito |
|----|-----------|
| RF-019 | El sistema debe enviar email al cambiar contraseña |
| RF-020 | El sistema debe enviar notificación al email antiguo cuando se cambia el email |

### Invalidación de sesiones post-cambio de contraseña
| ID | Requisito |
|----|-----------|
| RF-021 | El sistema debe invalidar TODAS las sesiones activas del usuario al cambiar contraseña |

## 14. Fuera de alcance (implementable, merece spec propio)

- Autenticación de dos factores (2FA) — ya esbozado en spec 001
- Políticas de expiración de contraseña (obligar cambio cada N días)
- Eliminación o desactivación de cuenta
- Internacionalización / localización de mensajes
- Cambios masivos de perfil por administradores
- Pruebas de carga o rendimiento específicas

→ Ver `ideas-para-specs-dedicados.md` en la raíz del proyecto para detalles.

## 15. Nota

Items de "logout con X", "soporte para Y", "integración con Z" generados por IA fueron descartados por no aportar valor al dominio hotelero o ser duplicaciones conceptuales.
