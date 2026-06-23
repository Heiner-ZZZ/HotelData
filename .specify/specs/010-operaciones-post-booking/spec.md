# Especificación: Operaciones Post-Booking

**Versión**: 1.0 | **Estado**: Implementado

**Casos de uso TAF06**: CU-O08 (Registrar reserva manual), CU-O22 (Registro de reseñas), CU-O23 (Moderación de reseñas)

## 1. Objetivo

Gestionar operaciones que ocurren fuera del flujo digital estándar de reserva: reservas manuales (walk-in, teléfono, cortesía) creadas por staff, y reseñas de huéspedes con moderación y respuesta del hotel. Unifica dos funcionalidades post-booking que comparten el contexto de "operaciones posteriores a la estancia o alternativas al canal digital".

## 2. Contexto

No todas las reservas llegan por el canal digital. El staff necesita registrar reservas directamente (walk-in, teléfono). Adicionalmente, los huéspedes que completaron su estancia pueden dejar reseñas que pasan por moderación antes de ser públicas. Ambos flujos extienden el ciclo de vida de la reserva hacia atrás (reserva manual) y hacia adelante (reseña post-estancia).

## 3. Actores

| Actor | Descripción |
|-------|-------------|
| Gerente de hotel / Staff | Crea reservas manuales, modera reseñas, responde a reseñas |
| Cliente / Huésped | Reseña después de su estancia |

## 4. Requisitos funcionales

### Reserva Manual

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Formulario con selección de hotel, tipo habitación, fechas, huéspedes, tarifa | Alta |
| RF-002 | Crear booking_order con estado "confirmed" directamente (salta pending) | Alta |
| RF-003 | Asociar huéspedes en booking_guests | Alta |
| RF-004 | Registrar en booking_status_history con razón "manual_reservation" | Alta |
| RF-005 | GET/POST /partner/manual-reservations/new (web) | Alta |
| RF-006 | POST /api/management/manual-reservations (API) | Alta |
| RF-007 | Listar reservas manuales con filtros | Media |

### Reseñas

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-101 | Crear reseña para un booking completado | Alta |
| RF-102 | Listar reseñas con filtros (prop_id, user_id, moderation_status) | Alta |
| RF-103 | Obtener detalle de reseña | Alta |
| RF-104 | Moderar reseña (approved/rejected) | Alta |
| RF-105 | Responder como staff a reseñas aprobadas | Alta |
| RF-106 | Eliminar reseña | Media |
| RF-107 | Dual-write: operacional → reviews, analítico → fact_reviews | Alta |
| RF-108 | Una reseña por reserva (unique por booking_id) | Alta |

## 5. Endpoints API

### Reserva Manual

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/partner/manual-reservations/new` | Formulario web de reserva manual |
| POST | `/partner/manual-reservations/new` | Crear reserva manual (web) |
| POST | `/api/management/manual-reservations` | Crear reserva manual (API) |
| GET | `/partner/manual-reservations` | Listar reservas manuales |

### Reseñas

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/reviews/?user_id={id}` | Crear reseña |
| GET | `/api/reviews/` | Listar reseñas (filtros) |
| GET | `/api/reviews/{id}` | Detalle de reseña |
| PATCH | `/api/reviews/{id}/moderate` | Moderar (approved/rejected) |
| PATCH | `/api/reviews/{id}/respond` | Responder como staff |
| DELETE | `/api/reviews/{id}` | Eliminar reseña |

## 6. Modelo de datos

### manual_reservations

| Campo | Tipo | Descripción |
|-------|------|-------------|
| manual_reservation_id | string | MR-XXXXXX |
| booking_id | string | BK-XXXXXX (referencia a booking_orders) |
| prop_id | int | ID del hotel |
| created_by | string | Staff que creó la reserva |
| note | string | Nota opcional |
| status | string | pending / confirmed / cancelled (synced con booking) |

### reviews (operacional)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| booking_id | ObjectId | Referencia a la reserva (único) |
| prop_id | int | ID del hotel |
| user_id | ObjectId | Usuario que reseña |
| rating | int (1-5) | Puntuación |
| title | str | Título opcional |
| comment | str | Comentario |
| moderation_status | str | pending / approved / rejected |
| staff_response | str? | Respuesta del hotel |
| staff_response_at | datetime? | Fecha de respuesta |

## 7. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-001 | Una reserva manual se crea directamente como "confirmed" (no pasa por pending) |
| RN-002 | Una reseña por reserva (unique por booking_id) |
| RN-003 | Solo el usuario que hizo la reserva puede reseñar |
| RN-004 | Moderación inicial: pending — staff debe aprobar/rechazar |
| RN-005 | El staff solo puede responder a reseñas aprobadas |
| RN-006 | Dual-write: datos operacionales → reviews, datos analíticos → fact_reviews |

## 8. Dependencias

- `booking_orders` — Reservas asociadas
- `manual_reservations` — Reservas manuales
- `reviews` — Reseñas operacionales
- `fact_reviews` — Reseñas analíticas (dual-write)
- `server/src/app/modules/partner/routes/manual_reservations.py` — Rutas de reserva manual
- `server/src/app/modules/reviews/service/` — Lógica de reseñas
- `server/src/app/modules/reservations/service/lifecycle.py` — Creación de booking con flag manual

## 9. Fuera de alcance

### Cubiertos por otros specs
- Pago integrado al crear reserva manual → spec 009 (Facturación y Cancelaciones)
- Notificación automática al cliente sobre reserva manual → spec 054 (Alertas operativas)
- Notificación automática al huésped sobre respuesta a reseña → spec 054 (Alertas operativas)
- Validación de datos de huéspedes (pasaportes, visas, etc.) → spec 031 (Contratos API)
- CHAT IA para sugerir respuestas a reseñas → spec 038 (IA y Machine Learning)
- CHAT IA $para sugerir tarifas o promociones al crear reserva manual → spec 038 (IA y Machine Learning)
- Integración con Channel Managers, OTAs → spec 037 (Integraciones API)
- Reportes de reseñas (promedio por hotel, etc.) → spec 029 (Reportes de Calidad)

### Pendientes de evaluar (posibles specs dedicados)
#### Reserva Manual
- Gestión de reservas manuales para grupos o eventos especiales
- Gestión de solicitudes especiales (cama extra, accesibilidad, mascotas) durante reserva manual
- Reservas manuales con múltiples tipos de habitación en una sola solicitud 
- IA para sugerir tarifas o promociones al crear reserva manual
- Validación de disponibilidad en tiempo real al crear reserva manual

#### Reseñas
- Web UI de reseñas (actualmente solo API REST)
- Reseñas con imágenes
- Votación de utilidad de reseñas (útil / no útil)
- IA para sugerir respuestas automáticas a reseñas
- IA para análisis de sentimiento en reseñas
- IA para detección de fraude o spam en reseñas
- IA para clasificación automática de reseñas por categoría (limpieza, servicio, ubicación, etc.)
- IA para resumen automático de reseñas largas
- IA para predicción de satisfacción del huésped basada en reseñas
- Moderación de reseñas con inteligencia artificial (filtro de lenguaje ofensivo, spam)
- Estadísticas de reseñas por hotel (promedio, distribución)
