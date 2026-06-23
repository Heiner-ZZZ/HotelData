# Ideas para Specs Dedicados

Ideas rescatables de specs 001–004, 008–010 que merecen un spec completo propio.
Última actualización: 2026-06-22 (v3 — categorización AHORA / Fuera de alcance / Spec dedicado).

---

## Análisis de viabilidad — Spec 002 "Fuera de alcance"

Items auto-completados por IA en spec 002 que fueron categorizados según viabilidad actual:

### ✅ IMPLEMENTAR AHORA (sin dependencias externas)

| # | Idea | Esfuerzo | Ubicación |
|---|------|----------|-----------|
| 1 | **Logout remoto en todos los dispositivos** — Botón "Cerrar otras sesiones" en perfil con confirmación. Backend: `POST /api/auth/sessions/terminate-others`. Frontend: UI en profile page. Ya existe `invalidate_user_sessions()` | ⭐ (1 hora) | Profile page |
| 2 | **Force logout de sesiones por administrador** — Botón en /system/users que termina TODAS las sesiones de un usuario. Ya existe `terminate_user_sessions()` en sessions.py | ⭐ (1 hora) | System users page |
| 3 | **Expiración por inactividad (heartbeat)** — Backend: campo `last_activity_at` en sesión, middleware que actualiza cada 60s. Frontend: heartbeat cada 1-2 min + aviso "Sesión expirará pronto" | ⭐⭐ (2-3 horas) | Backend middleware + frontend service |

### 📋 SPEC DEDICADO (merecen diseño propio)

| # | Idea | Razón | Spec sugerido |
|---|------|-------|---------------|
| 4 | **2FA por email** — Ya hay flujo de código de 6 dígitos del registro; extenderlo al login para admins | Diseño de flujo completo | `spec-2fa-email` |
| 5 | **JWT como alternativa a cookie** — Access + Refresh token para API/mobile. python-jose ya instalado | Diseño de middleware + claims | `spec-jwt-api` |
| 6 | **Rate limiting por usuario** — Extender slowapi para limitar por user_id + IP usando Redis | Configuración Redis como backend | `spec-rate-limit-user` |
| 7 | **Detección de anomalías / Geolocalización** — Detectar login desde ubicaciones inusuales | Dependencia externa (MaxMind/ipapi) | `spec-anomaly-detection` |

### 🚫 FUERA DE ALCANCE (no implementar ahora)

| # | Idea | Razón |
|---|------|-------|
| 8 | **SSO / OAuth / Google Login** — Requiere Client ID + Secret de cada proveedor, flujo OAuth complejo | Requiere registro en proveedores externos |
| 9 | **Bloqueo geográfico** — Requiere API de geolocalización + diseño de UI admin | Dependencia externa, bajo impacto |
| 10 | **Políticas de seguridad avanzadas** — Bloqueo por país, hora, dispositivo | Dependencia externa |

---

## 1. SSO / OAuth / Inicio de Sesión con Proveedores Externos

**Origen**: Spec 001, Spec 002

**Descripción**: Integrar autenticación mediante proveedores externos (Google, Microsoft, Facebook, GitHub) usando OAuth 2.0 / OpenID Connect. El usuario puede vincular su cuenta HotelData con uno o más proveedores y autenticarse sin recordar otra contraseña.

**Lo que implicaría**:
- Frontend: Botones "Iniciar sesión con Google / Microsoft / etc" en login-page
- Backend: Flujo OAuth (redirect → callback → intercambiar code por tokens)
- Vincular cuentas externas a usuarios existentes
- `oauth_states` collection (TTL) para prevenir CSRF en el flujo OAuth
- `user_oauth_links` collection para vincular proveedores+ID externos a user_id interno

**Dependencias**: `httpx` (para llamar APIs de proveedores), credenciales de cada proveedor (Client ID + Secret)

**Estado**: 🚫 Fuera de alcance — requiere registro en proveedores externos

---

## 2. Expiración de Sesión por Inactividad (Session Timeout por Actividad)

**Origen**: Spec 001, Spec 002

**Descripción**: Cerrar la sesión automáticamente después de N minutos sin actividad del usuario. El frontend envía un heartbeat periódico al backend para actualizar `last_activity_at` en la sesión. Un job (o el propio middleware) verifica si la sesión superó el umbral de inactividad y la invalida.

**Lo que implicaría**:
- Campo `last_activity_at` en `user_sessions`
- Middleware que actualiza `last_activity_at` en cada request autenticado (con writes rate-limited, ej. cada 60s)
- Frontend: heartbeat cada 1-2 minutos, mostrar "Su sesión expirará pronto" cuando quede poco tiempo
- Configurable por usuario desde `/api/settings` (session_timeout_minutes ya existe)
- TTL index existente sigue funcionando como límite máximo absoluto

**Dependencias**: Ninguna externa. Solo código backend + frontend.

**Estado**: ✅ Implementar AHORA (2-3 horas)

---

## 3. Logout Remoto en Todos los Dispositivos ✅ IMPLEMENTADO

**Origen**: Spec 002

**Descripción**: Permitir al usuario cerrar todas sus sesiones activas (excepto la actual) desde un solo botón. Útil ante sospecha de compromiso de cuenta o cambio de contraseña.

**Lo que implicaría**:
- Endpoint `POST /api/auth/sessions/terminate-others` (mata todas excepto la actual)
- Confirmación en frontend ("¿Estás seguro? Se cerrarán X sesiones en otros dispositivos")
- `invalidate_user_sessions()` ya existe en session.py

**Dependencias**: Ninguna. Fácil de implementar (1 hora).

**Estado**: ✅ **IMPLEMENTADO** en profile page como sección "Seguridad"

---

## 4. Detección de Anomalías y Geolocalización de Sesiones

**Origen**: Spec 001, Spec 002

**Descripción**: Detectar actividades sospechosas basadas en geolocalización de IP, horarios atípicos, o patrones de uso inusuales. Enviar alertas o bloquear la sesión automáticamente.

**Lo que implicaría**:
- Servicio de geolocalización por IP (MaxMind GeoLite2 o API externa como ipapi.co, ipgeolocation.io)
- Almacenar `city`, `country`, `timezone` en `user_sessions`
- Reglas de detección: mismo usuario desde 2 países distintos en < 1 hora, login desde IP bloqueada, etc.
- Requiere API key para geolocalización (MaxMind es gratuita para downloads, las APIs REST son de paga)

**Dependencias**: API de geolocalización (MaxMind GeoLite2 gratuita, o ipapi.co/ipgeolocation.io con key)

**Estado**: 📋 Spec dedicado

---

## 5. JWT como Alternativa / Complemento a Cookie de Sesión

**Origen**: Spec 001

**Descripción**: Implementar autenticación mediante JWT (Access Token + Refresh Token) como alternativa a la cookie de sesión actual. Útil para integraciones API (third-party) y apps móviles donde las cookies no son ideales.

**Lo que implicaría**:
- `POST /api/auth/token` — Login devuelve `{ access_token, refresh_token, expires_in }`
- Middleware que acepta `Authorization: Bearer <token>` además de la cookie
- JWT con claims: `sub`, `role`, `exp`, `iat`
- Refresh token ya existe (ver spec 001, RF-030 a RF-032), se reutiliza
- La cookie actual (`hoteldata_session`) sigue funcionando para el SPA

**Dependencias**: `python-jose` ya está en requirements.txt

**Estado**: 📋 Spec dedicado

---

## 6. Rate Limiting por Usuario (No solo por IP)

**Origen**: Spec 001

**Descripción**: Extender el rate limiting actual para que también límite por usuario autenticado, no solo por IP. Esto protege contra abuso de endpoints autenticados (ej. un usuario malicioso que hace scraping).

**Lo que implicaría**:
- Cambiar slowapi de `get_remote_address` a una key personalizada que combine IP + user_id
- O implementar un rate limiter propio usando Redis (ya está en requirements.txt)
- Límites configurables por rol

**Dependencias**: `redis` ya está en requirements.txt, `slowapi` ya está instalado

**Estado**: 📋 Spec dedicado

---

## 7. Bloqueo Geográfico (Geo-Blocking)

**Origen**: Spec 001

**Descripción**: Bloquear inicios de sesión o accesos desde países o regiones no autorizadas. Configurable por administradores del sistema.

**Lo que implicaría**:
- Lista de países permitidos/restringidos en settings del sistema
- Resolución de IP a país en cada login
- Middleware que verifica país de origen en cada request (o solo en login)
- Interfaz admin para gestionar la lista

**Dependencias**: API de geolocalización (comparte dependencia con #4)

**Estado**: 🚫 Fuera de alcance

---

## 8. Autenticación de Dos Factores (2FA)

**Origen**: Spec 001 (Implementaciones adicionales), Spec 003 (Fuera de alcance)

**Descripción**: Permitir a usuarios (especialmente administradores) activar 2FA por email. Al iniciar sesión, después de credenciales válidas, se exige un código de 6 dígitos enviado por email antes de completar la autenticación.

**Lo que implicaría**:
- `POST /api/auth/2fa/setup` — Activar 2FA, genera secret
- `POST /api/auth/2fa/verify` — Verificar código de prueba durante setup
- `POST /api/auth/2fa/disable` — Desactivar 2FA (requiere contraseña)
- Flujo de login modificado: si usuario tiene 2FA activo, tras validar credenciales responde `"2fa_required": true` y espera `POST /api/auth/2fa/verify-login` con código
- `two_factor_codes` collection (TTL 5 min) + `user_2fa` collection
- Email con código de 6 dígitos

**Dependencias**: `secrets` (ya en stdlib), send_email (ya existe)

**Estado**: 📋 Spec dedicado

---

## 9. Políticas de Expiración de Contraseña

**Origen**: Spec 003 (Fuera de alcance)

**Descripción**: Obligar al usuario a cambiar su contraseña cada N días (ej. 90 días para administradores). El sistema verifica en cada login si la contraseña ha expirado y redirige a cambio forzoso.

**Lo que implicaría**:
- Campo `password_changed_at` en `users`
- Verificación en login: si ha pasado más de `PASSWORD_MAX_AGE_DAYS`, forzar cambio
- Endpoint de cambio de contraseña ya existe
- Configurable por rol (admins cada 90, clientes cada 180)
- Las contraseñas expiradas no pueden reutilizarse (password_history ya existe)

**Dependencias**: Ninguna. Solo lógica en login + settings.

**Estado**: 📋 Spec dedicado

---

## 10. Eliminación / Desactivación de Cuenta

**Origen**: Spec 003 (Fuera de alcance)

**Descripción**: Permitir al usuario solicitar la eliminación o desactivación temporal de su cuenta. Los administradores pueden gestionar estas solicitudes.

**Lo que implicaría**:
- `POST /api/account/deactivate` — Desactiva cuenta (is_active=false), mata sesiones
- `POST /api/account/delete` — Solicita eliminación (requiere confirmación por email)
- `user_activity_logs` para registrar solicitudes
- Política de retención de datos (no borrar inmediatamente, esperar N días)
- Admin puede cancelar solicitud de eliminación

**Dependencias**: Ninguna.

**Estado**: 📋 Spec dedicado

---

## 11. Internacionalización / Localización (i18n)

**Origen**: Spec 003 (Fuera de alcance)

**Descripción**: Soportar múltiples idiomas en la interfaz (UI) y mensajes del backend (errores, emails). El usuario selecciona su idioma preferido en perfil.

**Lo que implicaría**:
- Archivos de traducción (JSON) para cada idioma
- `Accept-Language` header para detectar idioma preferido
- Traducciones en emails (password change, verification, etc.)
- Los mensajes de error de Pydantic/FastAPI deben traducirse
- Frontend: ngx-translate o similar

**Dependencias**: Biblioteca de i18n para Angular (ej. @angular/localize), archivos de traducción

**Estado**: 📋 Spec dedicado

---

## 12. Búsqueda por Coordenadas Geográficas (Mapa)

**Origen**: Spec 004 (Fuera de alcance)

**Descripción**: Permitir buscar hoteles por cercanía a coordenadas (lat, lon) en lugar de solo por nombre de destino. Mostrar resultados en mapa interactivo.

**Lo que implicaría**:
- Campos `latitude`, `longitude` en `dim_hotels` (o colección separada)
- Índice 2dsphere de MongoDB para búsquedas geoespaciales
- Endpoint `GET /api/hotels/nearby?lat=40.4168&lon=-3.7038&radius=10`
- Frontend: mapa interactivo (Leaflet/Mapbox)
- **Nota**: Si dim_hotels no tiene coordenadas, primero hay que poblar desde fuente externa

**Dependencias**: Coordenadas en los datos de hoteles, librería de mapas en frontend

**Estado**: 📋 Spec dedicado

---

## 13. Tarifas Dinámicas Basadas en Demanda

**Origen**: Spec 004 (Fuera de alcance)

**Descripción**: Mostrar tarifas que varían según la demanda, ocupación actual, y eventos cercanos. En lugar de solo la tarifa mínima configurada, el sistema calcula precios dinámicos.

**Lo que implicaría**:
- Algoritmo de pricing que considera ocupación actual, histórica, eventos, estacionalidad
- Actualización frecuente de `hotel_rate_calendar` con precios dinámicos
- Reglas de negocio: precio mínimo, precio máximo, descuento por early booking
- Panel de configuración para revenue managers

**Dependencias**: Modelo de pricing, datos históricos

**Estado**: 📋 Spec dedicado

---

## 14. Pasarela de Pagos Real (Stripe / PayPal / Mercado Pago)

**Origen**: Spec 009 (Fuera de alcance)

**Descripción**: Integrar una pasarela de pagos real para reemplazar los pagos simulados actuales.

**Estado**: 🚫 Fuera de alcance

---

## 15. Cambios Masivos de Perfil por Administradores

**Origen**: Spec 003 (Fuera de alcance)

**Descripción**: Permitir a administradores del sistema modificar campos de perfil de múltiples usuarios simultáneamente (ej. cambiar rol, activar/desactivar, actualizar preferencias). Útil para operaciones de onboarding, migración o corrección masiva.

**Lo que implicaría**:
- Endpoint `POST /api/admin/users/bulk-update` — acepta lista de user_ids + campos a modificar
- Validación de permisos (solo super_admin/admin_sistema)
- Log en `user_activity_logs` para cada usuario modificado
- Opción de desactivación masiva (is_active=false)
- Interfaz admin con selector múltiple de usuarios + formulario de campos a actualizar
- Confirmación con resumen de cambios antes de ejecutar

**Dependencias**: Ninguna. `admin/routes.py` ya existe.

**Estado**: 📋 Spec dedicado

---

## 16. Recuperación de Contraseña por Email

**Origen**: Spec 003 (Implementaciones adicionales)

**Descripción**: Permitir al usuario solicitar un enlace de recuperación por email cuando olvida su contraseña. El enlace expira en 1 hora y permite establecer una nueva contraseña.

**Estado**: ✅ **IMPLEMENTADO** (2026-06-22) — Endpoints `POST /api/auth/recover` y `POST /api/auth/recover/reset`, frontend en `/recover` y `/reset`, enlace en login.

---

## 17. Destinos Alternativos cuando no hay Resultados

**Origen**: Spec 004 (Fuera de alcance — IA sugerir destinos alternativos)

**Descripción**: Cuando la búsqueda de hoteles no encuentra resultados, el sistema sugiere destinos alternativos relacionados (mismos términos/región) para que el usuario intente con otra opción.

**Lo que implicaría**:
- Función `_suggest_alternative_destinations()` en `lookups.py` que busca en `dim_destinations` por palabras compartidas
- Respuesta incluye `alternative_destinations[]` en el JSON de búsqueda vacía
- Frontend muestra chips clicables que actualizan la búsqueda

**Dependencias**: `dim_destinations` (ya existe con 6,460 registros)

**Estado**: ✅ **IMPLEMENTADO** (2026-06-22) — Backend + frontend completo.

---

## 18. Promociones y Descuentos en Resultados de Búsqueda

**Origen**: Spec 004 (Fuera de alcance)

**Descripción**: Mostrar promociones activas y descuentos directamente en los resultados de búsqueda (ej. "15% OFF en reserva anticipada"). El usuario ve el precio con descuento aplicado y la promoción destacada.

**Lo que implicaría**:
- Integración con spec 021 (promociones/cupones) para obtener promociones activas por hotel/fecha
- Campo `promotion_label`, `discounted_price` en los items de búsqueda
- Frontend: badge/tag en hotel-card con el descuento
- Lógica de pricing que aplique el mejor descuento disponible al `min_nightly_rate`

**Dependencias**: Spec 021 (promociones), `promotion_campaigns` collection

**Estado**: 📋 Spec dedicado

---

## Priorización sugerida

| # | Acción | Item | Esfuerzo | Impacto | Estado |
|---|--------|------|----------|---------|--------|
| 1 | ✅ YA | Logout remoto todos dispositivos | ⭐ (1h) | Alto | ✅ IMPLEMENTADO |
| 2 | ✅ YA | Force logout por admin | ⭐ (1h) | Alto | ✅ IMPLEMENTADO |
| 3 | ✅ YA | Recuperación de contraseña por email | ⭐⭐ (2-3h) | Alto | ✅ IMPLEMENTADO |
| 4 | ✅ YA | Destinos alternativos si no hay resultados | ⭐⭐ (1-2h) | Medio | ✅ IMPLEMENTADO |
| 5 | ✅ AHORA | Expiración por inactividad (heartbeat) | ⭐⭐ (2-3h) | Medio | Pendiente |
| 6 | 📋 Spec | 2FA por email | ⭐⭐ (2d) | Alto | Pendiente |
| 7 | 📋 Spec | JWT API | ⭐⭐ (2-3d) | Alto | Pendiente |
| 8 | 📋 Spec | Rate limiting por usuario | ⭐ (1d) | Medio | Pendiente |
| 9 | 📋 Spec | Cambios masivos de perfil por admins | ⭐⭐ (1-2d) | Medio | Pendiente |
| 10 | 📋 Spec | Promociones y descuentos en búsqueda | ⭐⭐ (1-2d) | Medio | Pendiente |
| 11 | 🚫 No | SSO/OAuth | ⭐⭐⭐⭐ | Alto | Futuro |
| 12 | 🚫 No | Bloqueo geográfico | ⭐⭐ | Bajo | Futuro |
| 13 | ✅ YA | Chatbot IA hoteles similares | ⭐⭐⭐ (3-4h) | Alto | ✅ IMPLEMENTADO |
| 14 | ✅ YA | Políticas cancelación en comparación | ⭐ (0.5h) | Medio | ✅ IMPLEMENTADO |
| 15 | 📋 Spec | Filtros personalizados por usuario | ⭐⭐ (1d) | Medio | Pendiente |
| 16 | 📋 Spec | Pricing en tiempo real | ⭐⭐⭐ (2d) | Alto | Pendiente |
| 17 | 📋 Spec | Búsqueda por coordenadas / mapa | ⭐⭐ (1-2d) | Medio | Pendiente |
| 18 | 📋 Spec | Comparación avanzada de políticas | ⭐ (0.5d) | Bajo | Pendiente |
| 19 | 📋 Spec | Filtros amenities por categorías | ⭐⭐ (1d) | Medio | Pendiente |
| 20 | 🚫 No | Comparación con OTAs externas | ⭐⭐⭐⭐ | Bajo | Futuro |
| 21 | 🚫 No | GANs / IA generación imágenes | ⭐⭐⭐⭐⭐ | Bajo | Futuro |

---

## Análisis de viabilidad — Spec 005 "Filtros y Comparación"

Items auto-completados por IA en spec 005, categorizados según viabilidad actual:

### ✅ YA IMPLEMENTADOS

| # | Idea | Ubicación |
|---|------|-----------|
| 1 | **Chatbot IA para sugerir hoteles similares** — Implementado como "Hoteles similares con IA" usando NVIDIA API, ranking por similitud en detalle del hotel | `server/src/app/modules/hotels/service/similar.py`, `GET /api/hotels/{prop_id}/similar` |
| 2 | **Políticas de cancelación/reembolso en comparación** — El endpoint `GET /api/hotels/compare` ya devuelve `policies` con `check_in`, `check_out`, y demás campos de `hotel_policies` | `server/src/app/modules/hotels/service/compare.py:82-94` |

### ✅ IMPLEMENTAR AHORA (sin dependencias externas)

Ninguno de los ítems restantes es implementable "AHORA" sin un spec dedicado. Todos requieren diseño adicional o dependencias externas.

### 📋 SPEC DEDICADO (merecen diseño propio)

| # | Idea | Razón | Spec sugerido |
|---|------|-------|---------------|
| 3 | **Personalización de filtros basada en preferencias del usuario** — Recordar filtros frecuentes por usuario (destino favorito, rango precio, amenities preferidas) | Requiere modelo de preferencias + UI de gestión | `066-filtros-preferencias-usuario` |
| 4 | **Comparación de precios en tiempo real (motor de pricing)** — Mostrar tarifas que varían según demanda/ocupación, no solo la tarifa configurada | Requiere algoritmo de pricing dinámico, depende de spec 021 (promociones) | `067-pricing-tiempo-real` |
| 5 | **Búsqueda por coordenadas geográficas (mapa)** — Buscar hoteles por cercanía a lat/lon en lugar de solo destino nominal. Mapa interactivo | Requiere coordenadas en dim_hotels + índice 2dsphere + librería de mapas | `068-busqueda-mapa` |
| 6 | **Comparación avanzada de políticas (desayuno, cancelación, mascotas)** — Mostrar diferencias específicas de políticas lado a lado con iconos | `hotel_policies` tiene datos, pero la UI de comparación mostraría filas específicas por política (no solo un objeto genérico) | `069-comparacion-politicas-avanzado` |
| 7 | **Filtros de amenities por categorías (checkboxes)** — Reemplazar el input de texto actual por checkboxes agrupados por tipo (WiFi, Piscina, Desayuno, Gimnasio, etc.) | Requiere mapeo de amenities_text a categorías + rediseño del FilterSidebar | `070-filtros-amenities-categorias` |

### 🚫 FUERA DE ALCANCE (no implementar ahora)

| # | Idea | Razón |
|---|------|-------|
| 8 | **Comparación con hoteles de otros sistemas (OTAs)** — Integrar datos de Booking, Expedia, etc. | Requiere APIs externas, contratos, y scraping; fuera del alcance del proyecto |
| 9 | **GANs para generar imágenes de habitaciones según descripción** — IA generativa de imágenes | Requiere GPU/API especializada (DALL-E, Stable Diffusion), alto costo, NVIDIA free tier no lo soporta |
| 10 | **IMG de habitaciones generadas por IA según descripción** — Similar al anterior | Misma razón que #9 |
