# Especificación: Cambio de Contraseña y Actualización de Perfil

**Versión**: 1.0 | **Estado**: Draft | **Última actualización**: 2026-06-21

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
| RF-002 | El sistema debe validar que la nueva contraseña cumpla políticas de seguridad (mín. 8 caracteres) | Alta |
| RF-003 | El sistema debe hashear la nueva contraseña con bcrypt antes de almacenar | Alta |
| RF-004 | El sistema debe invalidar todas las sesiones activas después del cambio de contraseña | Media |
| RF-005 | El sistema debe permitir actualizar display_name, email, phone, address, preferencias | Alta |
| RF-006 | El sistema debe permitir subir avatar (imagen) | Baja |
| RF-007 | El sistema debe registrar cambios de perfil y contraseña en user_activity_logs | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | La contraseña nunca debe viajar en texto plano por la URL (solo en body de POST/PUT) |
| RNF-002 | El avatar debe validarse como imagen (Content-Type, tamaño máximo 5MB) |
| RNF-003 | Respuesta del perfil no debe incluir el hash de la contraseña |

## 6. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-001 | La nueva contraseña no puede ser igual a la actual |
| RN-002 | Contraseña debe tener al menos 8 caracteres |
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
Y hashea la nueva contraseña
Y la almacena en users.password_hash
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
Entonces el sistema actualiza el sub-documento profile del usuario
Y responde con el perfil actualizado
```

## 10. Criterios de aceptación

| ID | Criterio |
|----|----------|
| CA-001 | Cambio de contraseña funciona con contraseña actual correcta |
| CA-002 | Cambio de contraseña falla con contraseña actual incorrecta |
| CA-003 | Nueva contraseña hasheada con bcrypt (verificable en DB) |
| CA-004 | Perfil actualizado se refleja en GET /api/account/profile |
| CA-005 | Cambios registrados en user_activity_logs |
| CA-006 | Avatar se almacena y es accesible por URL |

## 11. Restricciones

- Contraseñas almacenadas con bcrypt passlib
- Archivo de avatar: máximo 2MB, formatos image/jpeg, image/png
- No enviar contraseñas en GET o URL params

## 12. Dependencias

- `server/src/app/modules/account/` — Profile management routes + services
- `server/src/app/modules/settings/` — Password change routes + services
- `passlib[bcrypt]` — Hash de contraseñas
- `users` collection — Almacenamiento de perfil y contraseña
- `user_activity_logs` collection — Auditoría

## 13. Fuera de alcance

- Recuperación de contraseña por email (enlace de reset)
- Verificación de email después del cambio
- Autenticación de dos factores
- Historial de contraseñas anteriores
