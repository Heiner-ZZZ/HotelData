# Análisis: 21 Colecciones Vacías — Resultados de pruebas E2E

> **Fecha:** 2026-07-23 (pruebas) / 2026-07-24 (actualización)
> **Base de datos:** `hoteldata_hub` (MongoDB, 94 colecciones totales)
> **Colecciones vacías originales:** 21 → **4 pobladas en pruebas** → 17 restantes

---

## 🔬 Metodología

En vez de seedear datos ciegamente, se probó CADA colección desde la API real:
1. Login como superadmin
2. Llamar al endpoint de creación (POST)
3. Verificar que el documento se guardó en MongoDB
4. Auditar tipos de datos (ObjectId vs int vs string)

---

## ✅ Colecciones PROBADAS y FUNCIONANDO (6)

| # | Colección | Endpoint probado | Resultado | Docs | FK Issues |
|---|-----------|-----------------|-----------|------|------------|
| 1 | `lost_and_found` | `POST /api/management/lost-and-found` | ✅ 200 — 1 doc creado | 1 | 🔴 `prop_id`=int, `reported_by`=str(name) |
| 2 | `hotel_products` | `POST /api/management/products/hotels/1` | ✅ 200 — 1 doc creado | 1 | 🔴 `prop_id`=int |
| 3 | `hotel_images` | `POST /api/management/properties/1/images` | ✅ 200 — 1 doc creado | 1 | 🔴 `prop_id`=int |
| 4 | `reception_shifts` | `POST /api/reception/shifts/open` | ✅ 200 — 1 doc creado | 1 | 🔴 `prop_id`=int, `employee`=str(name) |
| 5 | `room_features` | `GET /api/management/room-features` | ✅ 200 — retorna datos hardcodeados | 0 | N/A (usa catálogo estático, no BD) |
| 6 | `amenity_stock` | `GET /api/amenities/stock?prop_id=1` | ✅ 200 — retorna `[]` vacío | 0 | N/A (stock se crea vía `set_amenity_stock()`) |

---

## 🔴 BUG: FKs tipo incorrecto — prop_id int en vez de ObjectId

**4 colecciones** escriben `prop_id` como `int` en vez de `ObjectId` (FK a `dim_hotels._id`):

| Colección | Campo actual | Tipo | Debería ser |
|-----------|-------------|------|-------------|
| `lost_and_found` | `prop_id` | `int` (1) | `ObjectId` → `dim_hotels._id` |
| `hotel_products` | `prop_id` | `int` (1) | `ObjectId` → `dim_hotels._id` |
| `hotel_images` | `prop_id` | `int` (1) | `ObjectId` → `dim_hotels._id` |
| `reception_shifts` | `prop_id` | `int` (1) | `ObjectId` → `dim_hotels._id` |
| `reception_shifts` | `employee` | `str` ("Carlos Mendoza") | `ObjectId` → `employees._id` |

**Causa raíz:** Estas colecciones se diseñaron antes de la migración a ObjectId FKs. El `prop_id` numérico (1, 2, 3...) es legacy del ETL `dim_hotels.prop_id`, pero `dim_hotels._id` ya es ObjectId. Los write paths no se actualizaron.

---

## 🔧 BUG ENCONTRADO Y CORREGIDO

| Bug | Archivo | Fix |
|-----|---------|-----|
| `manual_reservations` no registrado | `partner/routes/__init__.py` | Agregado `manual_reservations` al import del módulo |

El módulo `manual_reservations` tenía CRUD completo (routes + services + indexes) pero nunca se importaba en `__init__.py`, así que FastAPI no registraba sus endpoints.

---

## 🟡 Colecciones SIN write path (4)

Estas colecciones tienen definición e índices pero **NO tienen endpoints para insertar datos**:

| # | Colección | Código que la lee | Problema |
|---|-----------|------------------|----------|
| 7 | `tax_rates` | ❌ Nadie | Sin implementación — 0 referencias en todo el código |
| 8 | `commission_rates` | `billing/invoices.py:33` | Solo lectura. No hay UI ni API para crear comisiones |
| 9 | `expense_budget` | ❌ Solo definición en `collections.py` | Sin rutas, sin servicios. Solo existe la colección |
| 10 | `employee_documents` | ❌ Solo definición en `collections.py` | Sin rutas. Módulo HR no implementó upload de docs |

**Acción necesaria:** Implementar endpoints CRUD + UI para estas 4 colecciones.

---

## 🟠 Colecciones bloqueadas por precondiciones (5)

Funcionan pero requieren datos que no existen en el sistema actual:

| # | Colección | Bloqueo | Cómo desbloquear |
|---|-----------|---------|-----------------|
| 11 | `reviews` | Requiere `booking.status == "checked_out"` | Hacer checkout de un booking real |
| 12 | `fact_reviews` | Vista materializada de reviews | Se llena cuando hay reviews |
| 13 | `review_reports` | Reportes sobre reviews | Se llena cuando hay reviews |
| 14 | `stay_messages` | Requiere `stay_session` activa | Hacer check-in de un booking |
| 15 | `manual_reservations` | Requiere inventario disponible | Crear disponibilidad real + rutas registradas |
| 16 | `room_availability_blocks` | Depende de flujo de booking | Se llena al bloquear habitaciones |

---

## 🟢 Colecciones transitorias legítimamente vacías (4)

Estas colecciones de auth son naturalmente transitorias. Está BIEN que estén vacías:

| # | Colección | Se llena cuando... |
|---|-----------|-------------------|
| 17 | `password_recovery_tokens` | Un usuario solicita "olvidé mi contraseña" |
| 18 | `email_verification_tokens` | Se registra un email nuevo sin verificar |
| 19 | `two_factor_codes` | Un usuario con 2FA activado hace login |
| 20 | `user_2fa` | Un usuario activa 2FA en su perfil |

---

## 📊 Resumen final

| Estado | Cantidad | Colecciones |
|--------|:-------:|-------------|
| ✅ Probadas y funcionando | 6 | lost_and_found, hotel_products, hotel_images, reception_shifts, room_features, amenity_stock |
| 🔴 Con FK issues (prop_id=int) | 4 | lost_and_found, hotel_products, hotel_images, reception_shifts |
| 🟡 Sin write path | 4 | tax_rates, commission_rates, expense_budget, employee_documents |
| 🟠 Bloqueadas por precondiciones | 5 | reviews, fact_reviews, review_reports, stay_messages, manual_reservations, room_availability_blocks |
| 🟢 Legítimamente vacías | 4 | password_recovery_tokens, email_verification_tokens, two_factor_codes, user_2fa |
| 🔧 Bug corregido | 1 | manual_reservations (no registrado en __init__.py) |

---

## 🎯 Plan de acción priorizado

### Fase 1 — Corregir FKs (HOY) 🔴
Corregir los write paths de 4 colecciones para que escriban `prop_id` como ObjectId:
1. `lost_and_found/service/lifecycle.py` → resolver `prop_id` → `dim_hotels._id`
2. `partner/services/hotel_products.py` → ídem
3. `partner/services/content/images.py` → ídem
4. `reception/shifts.py` → `prop_id` ObjectId + `employee` → `employees._id`

### Fase 2 — Implementar write paths (ALTA) 🟡
Crear endpoints CRUD para colecciones sin write path:
1. `commission_rates` — POST/PUT/DELETE + UI en Global Settings
2. `tax_rates` — decidir si se necesita o se elimina la colección
3. `expense_budget` — integrar con módulo expenses
4. `employee_documents` — integrar con módulo HR

### Fase 3 — Desbloquear features (MEDIA) 🟠
1. Hacer checkout de un booking → probar `reviews` completo
2. Hacer check-in → probar `stay_messages` (chat guest↔staff)
3. Probar `manual_reservations` con disponibilidad real

### Fase 4 — Probar auth flows (BAJA) 🟢
1. "Olvidé mi contraseña" → `password_recovery_tokens`
2. Registro con email → `email_verification_tokens`
3. 2FA → `two_factor_codes`, `user_2fa`
