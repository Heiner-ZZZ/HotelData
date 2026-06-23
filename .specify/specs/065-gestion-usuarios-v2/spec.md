# Especificación: Gestión de Usuarios v2

**Versión**: 1.0 | **Estado**: Draft

**Casos de uso TAF06**: CU-T09, CU-T10, CU-T11

## 1. Objetivo

Extender la gestión de usuarios del sistema con cuatro funcionalidades nuevas: edición de perfil de usuario (admin + auto-servicio), invitación por email con contraseña temporal, panel de auditoría de cambios en usuarios, y políticas de contraseña configurables.

## 2. Contexto

Actualmente el sistema permite listar usuarios, activar/desactivar cuentas (`/system/users`) y gestionar permisos por rol (`/system/permissions`). Sin embargo:

- No hay forma de editar nombre, email o contraseña de un usuario desde la UI
- No hay flujo de invitación: crear un usuario requiere que el admin defina la contraseña
- No hay un panel de auditoría centralizado para cambios en usuarios
- Las políticas de contraseña están hardcodeadas (mín 6 caracteres, sin expiración)

Este spec describe las funcionalidades faltantes para completar el módulo de gestión de usuarios.

## 3. Actores

| Actor | Descripción | Permisos |
|-------|-------------|----------|
| Super Admin | Administrador global del sistema | CRUD cualquier usuario, configurar políticas |
| Admin Sistema | Administrador del sistema | CRUD cualquier usuario (excepto super_admin), leer políticas |
| Usuario regular | Cualquier rol (hotel_partner, gerente, etc.) | Editar su propio perfil, ver su propia auditoría |

## 4. Requisitos funcionales

### Módulo 1: Edición de Perfil de Usuario

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir a super_admin/admin_sistema editar nombre, email y rol de cualquier usuario | Alta |
| RF-002 | El sistema debe permitir a cualquier usuario editar su propio nombre y email | Alta |
| RF-003 | El sistema debe permitir a cualquier usuario cambiar su propia contraseña (requiere contraseña actual) | Alta |
| RF-004 | El sistema debe permitir a un admin resetear la contraseña de cualquier usuario (genera temporal) | Alta |
| RF-005 | El sistema debe requerir verificación por email cuando un usuario cambia su email | Alta |
| RF-006 | El sistema debe permitir cambios de nombre sin verificación | Media |
| RF-007 | El sistema debe permitir a un admin desactivar su propia cuenta solo con doble confirmación | Media |
| RF-008 | El sistema debe impedir que un admin se desactive a sí mismo sin la confirmación explícita | Alta |

### Módulo 2: Invitación por Email

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-009 | El sistema debe permitir crear un usuario ingresando solo email, nombre y rol | Alta |
| RF-010 | El sistema debe generar una contraseña temporal segura (12+ chars, alfanumérica) | Alta |
| RF-011 | El sistema debe enviar un email con link de activación + contraseña temporal | Alta |
| RF-012 | El link de activación debe expirar en 24 horas | Alta |
| RF-013 | El sistema debe exigir cambio de contraseña en el primer inicio de sesión tras invitación | Alta |
| RF-014 | El sistema debe rechazar un link de invitación expirado con mensaje claro | Media |

### Módulo 3: Auditoría de Usuarios

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-015 | El sistema debe registrar todos los cambios en usuarios: creación, edición, activación/desactivación, cambios de rol, cambios de password | Alta |
| RF-016 | El sistema debe exponer un panel visual con tabla de auditoría filtrable por fecha, usuario afectado, tipo de acción y admin que realizó el cambio | Alta |
| RF-017 | El sistema debe permitir exportar la auditoría a CSV y JSON | Media |
| RF-018 | El sistema debe preservar el valor anterior y el nuevo valor en cada cambio registrado | Alta |

### Módulo 4: Políticas de Contraseña

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-019 | El sistema debe permitir configurar longitud mínima de contraseña (rango 6-32, default 8) | Alta |
| RF-020 | El sistema debe permitir exigir mayúsculas, minúsculas, números y símbolos (toggle por tipo) | Alta |
| RF-021 | El sistema debe permitir configurar expiración de contraseña en N días (0 = sin expiración, default 0) | Alta |
| RF-022 | El sistema debe forzar cambio de contraseña al expirar según la política configurada | Alta |
| RF-023 | El sistema debe permitir configurar historial de N contraseñas anteriores no reutilizables (0 = sin historial, default 3) | Alta |
| RF-024 | Las políticas deben ser configurables solo por super_admin desde una UI específica | Alta |
| RF-025 | Al cambiar una política, las contraseñas existentes no se invalidan retroactivamente | Media |

## 5. Requisitos no funcionales

| ID | Requisito | Descripción |
|----|-----------|-------------|
| RNF-001 | Seguridad | Contraseñas siempre hasheadas con bcrypt, nunca en texto plano ni en logs |
| RNF-002 | Seguridad | Tokens de invitación: 48 bytes secrets.token_urlsafe, hash SHA-256 en DB |
| RNF-003 | Seguridad | Link de invitación expira en 24h (TTL index en MongoDB) |
| RNF-004 | Rendimiento | Panel de auditoría debe cargar en < 2s con 10k registros |
| RNF-005 | UX | Confirmación de desactivación propia debe ser modal con doble clic |
| RNF-006 | Trazabilidad | Todo cambio de perfil debe quedar registrado en colección de auditoría |

## 6. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-001 | Un admin no puede cambiar el rol de otro admin a un rol inferior si ese admin tiene más permisos |
| RN-002 | El email de verificación para cambio de email debe enviarse al NUEVO email, no al anterior |
| RN-003 | Al resetear la contraseña de un usuario, todas sus sesiones activas deben invalidarse |
| RN-004 | Un usuario invitado que no complete el primer login dentro de 24h debe ser notificado con opción de reenviar invitación |
| RN-005 | Las políticas de contraseña se almacenan en una colección `password_policies` con un solo documento (singleton) |
| RN-006 | Los campos `password_changed_at` y `password_history` se agregan al documento del usuario |

## 7. Entradas

| Módulo | Dato | Tipo | Origen |
|--------|------|------|--------|
| Perfil | user_id | string (ObjectId) | URL param |
| Perfil | display_name | string | Formulario |
| Perfil | email | string | Formulario |
| Perfil | current_password | string | Formulario (solo cambio propio) |
| Perfil | new_password | string | Formulario |
| Invitación | email | string | Formulario |
| Invitación | display_name | string | Formulario |
| Invitación | primary_role | string (select) | Formulario |
| Auditoría | filtros | varios | Query params |
| Políticas | min_length | int (6-32) | Formulario |
| Políticas | require_uppercase | boolean | Toggle |
| Políticas | require_lowercase | boolean | Toggle |
| Políticas | require_numbers | boolean | Toggle |
| Políticas | require_symbols | boolean | Toggle |
| Políticas | expiration_days | int (0-365) | Formulario |
| Políticas | history_count | int (0-24) | Formulario |

## 8. Salidas

| Escenario | Respuesta |
|-----------|-----------|
| Perfil actualizado | 200 + mensaje "Perfil actualizado" |
| Email cambiado | 200 + "Verifica tu nuevo email" + email enviado |
| Contraseña cambiada | 200 + sesiones invalidadas + redirección a login |
| Invitación creada | 201 + mensaje "Invitación enviada a {email}" |
| Invitación expirada | 410 + mensaje "Link expirado. Solicita una nueva invitación." |
| Políticas actualizadas | 200 + mensaje "Políticas actualizadas" |
| Error de validación | 400 + detalle del error |

## 9. Escenarios

### Escenario 1: Admin edita perfil de usuario
```gherkin
Dado que super_admin está en la página de detalle del usuario "jperez"
Cuando cambia el nombre a "Juan Pérez" y el email a "juan@nuevo.com"
Entonces el sistema actualiza el nombre inmediatamente
Y envía un email de verificación a "juan@nuevo.com"
Y registra el cambio en la auditoría con valor anterior y nuevo
```

### Escenario 2: Usuario cambia su propia contraseña
```gherkin
Dado que el usuario "jperez" está en su página de perfil
Cuando ingresa su contraseña actual correcta y una nueva contraseña que cumple las políticas
Entonces el sistema actualiza el password_hash
Y invalida todas sus sesiones activas excepto la actual
Y registra el cambio en la auditoría
```

### Escenario 3: Admin invita a un nuevo usuario
```gherkin
Dado que super_admin está en el formulario de nuevo usuario
Cuando ingresa email "nuevo@hotel.com", nombre "Carlos López" y rol "hotel_partner"
Entonces el sistema crea el usuario con is_active=false y email_verified=false
Y genera una contraseña temporal de 12 caracteres
Y envía un email con link de activación (válido 24h) y la contraseña temporal
Y registra la creación en la auditoría
```

### Escenario 4: Usuario invitado completa su primer login
```gherkin
Dado que "carlos@hotel.com" recibió un email de invitación
Y el link no ha expirado
Cuando hace clic en el link y es redirigido a /set-password
Y establece una nueva contraseña que cumple las políticas
Entonces el sistema marca el usuario como activo (is_active=true)
Y registra el primer inicio de sesión exitoso
```

### Escenario 5: Admin configura políticas de contraseña
```gherkin
Dado que super_admin está en la página de políticas de seguridad
Cuando establece: longitud mínima 10, requiere mayúsculas, expiración 90 días, historial 5
Entonces el sistema guarda la configuración en password_policies
Y las nuevas reglas aplican desde el próximo cambio de contraseña
Y las contraseñas existentes no se invalidan
```

### Escenario 6: Admin se desactiva a sí mismo
```gherkin
Dado que super_admin "admin1" está en su propio perfil
Cuando hace clic en "Desactivar cuenta"
Entonces el sistema muestra un modal de confirmación: "¿Estás seguro? No podrás acceder de nuevo."
Y requiere un segundo clic en "Confirmar desactivación"
Y solo entonces desactiva la cuenta y redirige al login
```

## 10. Criterios de aceptación

| ID | Criterio |
|----|----------|
| CA-001 | Admin puede editar nombre de cualquier usuario sin verificación |
| CA-002 | Admin puede cambiar email de cualquier usuario, se envía verificación al nuevo email |
| CA-003 | Usuario puede cambiar su propio nombre sin verificación |
| CA-004 | Usuario puede cambiar su propio email, se envía verificación al nuevo email |
| CA-005 | Usuario puede cambiar su contraseña solo si ingresa la actual correctamente |
| CA-006 | Admin puede resetear contraseña de cualquier usuario (genera temporal) |
| CA-007 | Admin puede desactivar su propia cuenta solo con doble confirmación modal |
| CA-008 | Invitación por email genera contraseña temporal de 12+ caracteres |
| CA-009 | Link de invitación expira en 24 horas |
| CA-010 | Primer login con invitación requiere cambio de contraseña |
| CA-011 | Invitación expirada muestra mensaje claro con opción de reenviar |
| CA-012 | Panel de auditoría muestra tabla con filtros por fecha, usuario, acción y admin |
| CA-013 | Exportación a CSV incluye todos los campos visibles en el panel |
| CA-014 | Políticas de contraseña configurables desde UI por super_admin |
| CA-015 | Contraseña nueva validada contra todas las políticas activas |
| CA-016 | Contraseña expirada redirige al usuario a cambiar contraseña antes de acceder |
| CA-017 | Historial de contraseñas impide reutilizar las últimas N contraseñas |

## 11. Restricciones

- Contraseñas siempre con bcrypt (passlib), núnca en texto plano
- Tokens de invitación: 48 bytes secrets.token_urlsafe, hash SHA-256, TTL 24h
- Colecciones nuevas: `password_policies`, `user_audit_log` (reemplaza/log específico)
- La colección `user_audit_log` debe tener TTL index para limpieza automática (opcional)
- Cada documento de auditoría debe incluir: `user_id`, `changed_by`, `action`, `field`, `old_value`, `new_value`, `timestamp`
- El modal de autodesactivación debe tener dos estados: (1) advertencia, (2) confirmación

## 12. Dependencias

- `server/src/app/security/session.py` — invalidate_user_sessions()
- `server/src/app/security/password_policies.py` — Nueva: validación y políticas
- `server/src/app/modules/admin/service/users.py` — toggle_user_active existente
- `server/src/app/modules/account/service/profile.py` — Nuevo: edición de perfil
- `server/src/app/modules/account/routes.py` — Nuevos endpoints de perfil
- `server/src/app/email/service.py` — Envío de emails de invitación y verificación
- `server/src/app/security/route_permissions.py` — Nuevas reglas RBAC
- `frontend/src/app/features/system-admin/` — Nuevas páginas de edición y políticas
- `frontend/src/app/features/account/` — Nueva página de perfil de usuario
- Colección `password_policies` — Documento singleton con configuración
- Colección `user_audit_log` — Registro de cambios en usuarios

## 13. Fuera de alcance (v1)

- SSO / OAuth / Google Login
- Bloqueo geográfico o detección de anomalías en login
- Rate limiting configurable por usuario (solo por IP existe)
- Grupos de usuarios para asignación masiva de permisos
- Self-service de recuperación de cuenta (ya existe en spec 001)
- Integración con LDAP / Active Directory

## 14. Datos semilla

### Colección `password_policies` (documento único)
```json
{
  "_id": "global",
  "min_length": 8,
  "require_uppercase": true,
  "require_lowercase": true,
  "require_numbers": true,
  "require_symbols": false,
  "expiration_days": 0,
  "history_count": 3,
  "updated_by": "system",
  "updated_at": "<now>"
}
```

### Campos nuevos en documento `users`
```json
{
  "password_changed_at": "<datetime>",
  "password_history": ["<hash_1>", "<hash_2>", "<hash_3>"],
  "invitation_token_hash": "<sha256>",
  "invitation_expires_at": "<datetime>",
  "must_change_password": false
}
```
