# Plan de Expansión: Dynamic Pricing Engine

> **Módulo:** Pricing & Revenue (C. PRICING & REVENUE DOMAIN)
> **Estado actual:** Tarifas estáticas con CRUD básico + promociones
> **Objetivo:** Motor de precios dinámicos semi-automático con señales de demanda
> **Modo operación:** Híbrido — auto-apply para cambios < 10%, revisión manual para ≥ 10%

---

## 1. Diagnóstico del estado actual

### Lo que ya existe (base sólida)

| Componente | Estado | Colección / Endpoint |
|---|---|---|
| Planes tarifarios | ✅ CRUD completo | `rate_plans`, `POST /rates/plans` |
| Calendario de tarifas | ✅ CRUD completo | `hotel_rate_calendar`, `POST /rates/calendar` |
| Reglas de tarifa | ⚠️ Solo regla "standard" auto-creada | `rate_rules` |
| Promociones (% descuento) | ✅ CRUD completo | `promotion_campaigns` |
| Cupones de descuento | ✅ CRUD completo | `coupon_codes` |
| Analytics (conversión, revenue) | ✅ Dashboard existente | `revenue_overview`, `conversion_overview` |
| Frontend tarifas | ✅ UI completa con KPI grid | `/management/rates` |

### Lo que NO existe

- ❌ Motor de precios dinámicos basado en demanda/ocupación
- ❌ Reglas estacionales (temporada alta/baja/media)
- ❌ Ajustes automáticos por ocupación proyectada
- ❌ Precios por duración de estancia (LOS)
- ❌ Precios last-minute / early-bird
- ❌ Segmentación de tarifas por perfil de huésped
- ❌ Dashboard de simulación "what-if"
- ❌ Historial de cambios de precio (auditoría)
- ❌ Reglas de restricciones avanzadas (min stay, closed-to-arrival, release window)
- ❌ Sugerencias automáticas de precio

---

## 2. Arquitectura propuesta

```
┌──────────────────────────────────────────────────────────────┐
│                    PRICING ENGINE CORE                        │
│  Servicio Python que se ejecuta on-demand + batch (Airflow)  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Capa 1: REGLAS ESTÁTICAS  (expandir rate_rules existente)   │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  • season:           alta/baja/media con rangos fecha │   │
│  │  • day_of_week:      multiplicador Lun-Vie vs Sáb-Dom │   │
│  │  • los_discount:     descuento por noches (3+, 7+, 14+)│   │
│  │  • last_minute:      ajuste X días antes (ej: -15%)   │   │
│  │  • early_bird:       descuento Y días antes (ej: -10%)│   │
│  │  • closed_to_arrival: bool por fecha/rango            │   │
│  │  • min_stay:         noches mínimas por fecha/rango   │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  Capa 2: SEÑALES DE DEMANDA  (nueva colección)              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  price_elasticity_signals                              │   │
│  │  • occupancy_forecast:  % proyección a 30/60/90 días  │   │
│  │  • booking_pace:        reservas/día vs histórico      │   │
│  │  • competitor_rates:    precio promedio del mercado    │   │
│  │  • demand_index:        1-100 basado en búsquedas      │   │
│  │  • events_calendar:     eventos locales que afectan    │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  Capa 3: PRICE SUGGESTIONS  (nueva colección)               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  price_suggestions                                     │   │
│  │  • Generado por el motor cada N horas                  │   │
│  │  • Sugiere: rate_amount, min_stay, is_closed           │   │
│  │  • Incluye: confidence_score, rationale_text           │   │
│  │  • Estado: pending → applied / rejected                │   │
│  │  • Auto-apply si confidence > 90% Y cambio < 10%      │   │
│  │  • Review manual si cambio ≥ 10% (notifica al partner) │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  Capa 4: AUDIT TRAIL  (nueva colección)                     │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  price_change_log                                      │   │
│  │  • Cada cambio de precio se registra aquí              │   │
│  │  • old_rate → new_rate, reason, changed_by, timestamp  │   │
│  │  • TTL: 365 días                                       │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Nuevas colecciones MongoDB

### 3.1 `price_elasticity_signals`

```json
{
  "_id": ObjectId,
  "prop_id": 1,
  "date": "2026-07-15",
  "occupancy_forecast": 72.5,
  "occupancy_forecast_30d": 68.0,
  "occupancy_forecast_60d": 75.0,
  "booking_pace": 3.2,
  "booking_pace_avg": 4.1,
  "competitor_avg_rate": 185.00,
  "demand_index": 67,
  "events_nearby": ["Festival de Verano"],
  "generated_at": ISODate("2026-06-23T12:00:00Z")
}
```

### 3.2 `price_suggestions`

```json
{
  "_id": ObjectId,
  "prop_id": 1,
  "rate_plan_id": "RP-1-estandar",
  "date": "2026-07-15",
  "current_rate": 150.00,
  "suggested_rate": 172.50,
  "change_pct": 15.0,
  "min_stay": 2,
  "is_closed": false,
  "confidence": 82,
  "rationale": "Temporada alta (1.3x) + demanda alta (1.15x) = 1.495x sobre base $115",
  "applied_rules": ["season:alta", "demand_index:67", "day_of_week:sab"],
  "status": "pending",
  "auto_appliable": false,
  "generated_at": ISODate("2026-06-23T12:00:00Z")
}
```

> **Regla híbrida:** `auto_appliable = true` si `confidence > 90` Y `|change_pct| < 10`.
> Si `auto_appliable`, se aplica automáticamente (status → `applied`).
> Si no, queda `pending` y se notifica al partner para revisión.

### 3.3 `price_change_log`

```json
{
  "_id": ObjectId,
  "prop_id": 1,
  "rate_plan_id": "RP-1-estandar",
  "date": "2026-07-15",
  "old_rate": 150.00,
  "new_rate": 172.50,
  "reason": "auto_demand",
  "source_suggestion_id": ObjectId,
  "changed_by": "pricing_engine",
  "changed_by_user": null,
  "created_at": ISODate("2026-06-23T12:00:00Z")
}
```

Índices: `prop_id + date` (compuesto), `rate_plan_id`, `created_at` (TTL 365 días).

---

## 4. Motor de Pricing: Estrategia por capas

El motor evalúa de menor a mayor prioridad. La regla de mayor prioridad gana.

```
Prioridad 1: REGLA MANUAL (precio fijado por el usuario manualmente)
  → Si el usuario marcó "fijado manualmente = true" para esa fecha, respetar

Prioridad 2: PROMOCIÓN ACTIVA
  → Si hay campaña activa que cubre la fecha, aplicar descuento % sobre el precio calculado

Prioridad 3: REGLA ESTACIONAL
  → Temporada alta:  1.30x
  → Temporada media: 1.00x
  → Temporada baja:  0.80x

Prioridad 4: DAY OF WEEK
  → Sábado:   1.20x
  → Viernes:  1.10x
  → Domingo:  1.05x
  → Lun–Jue:  1.00x

Prioridad 5: DEMAND INDEX (desde price_elasticity_signals)
  → demand_index ≥ 80:  1.20x
  → demand_index ≥ 60:  1.10x
  → demand_index ≥ 40:  1.00x
  → demand_index ≥ 20:  0.90x
  → demand_index < 20:  0.80x

Prioridad 6: LENGTH OF STAY (descuento progresivo)
  → 3–6 noches:  -5%
  → 7–13 noches: -10%
  → 14+ noches:  -15%

Prioridad 7: VENTANA DE RESERVA
  → Last minute (0–3 días antes):  -15%
  → Early bird (30+ días antes):  -10%
```

**Cálculo final:**

```
rate_sugerida = base_rate
  × season_mult
  × day_of_week_mult
  × demand_mult
  × (1 - los_discount)
  × (1 - window_discount)
```

---

## 5. Endpoints API

### Reglas de pricing dinámico

```
GET    /api/management/pricing/rules?prop_id=X
  → Lista de reglas configuradas para la propiedad

POST   /api/management/pricing/rules
  → Crear/actualizar regla
  → Body: { prop_id, rule_type, name, config (JSON), priority, is_active }

DELETE /api/management/pricing/rules/{rule_id}
  → Eliminar regla
```

### Sugerencias de precio

```
GET    /api/management/pricing/suggestions?prop_id=X&date=Y&status=pending
  → Sugerencias activas, filtrables por fecha y estado

POST   /api/management/pricing/suggestions/{id}/apply
  → Aplicar sugerencia (cambia status → applied, registra en price_change_log)

POST   /api/management/pricing/suggestions/{id}/reject
  → Rechazar sugerencia (status → rejected, opcionalmente con motivo)
```

### Motor

```
POST   /api/management/pricing/engine/run?prop_id=X
  → Ejecutar el motor para una propiedad (bajo demanda)

GET    /api/management/pricing/engine/status?prop_id=X
  → Última ejecución, resultados: sugerencias generadas, auto-applied, pending
```

### Auditoría y simulación

```
GET    /api/management/pricing/audit?prop_id=X&from=Y&to=Z&page=N
  → Historial de cambios con paginación

POST   /api/management/pricing/simulate
  → Simulador "what-if": probar config antes de aplicarla
  → Body: { prop_id, rate_plan_id, dates[], hypothetical_rate }
  → Response: revenue_impact, occupancy_impact_estimate
```

---

## 6. Roadmap de implementación

### Fase 1 — Fundación (semana 1–2)

| # | Tarea | Archivos impactados |
|---|---|---|
| 1.1 | Crear colecciones `price_elasticity_signals`, `price_suggestions`, `price_change_log` + índices | `server/.../revenue/services/common.py` |
| 1.2 | Expandir `rate_rules` con campos dinámicos (season, day_of_week, los, last_minute, early_bird, closed_to_arrival) | `server/.../revenue/services/pricing_rules.py` (nuevo) |
| 1.3 | API CRUD para reglas de pricing dinámico | `server/.../revenue/routes.py` |
| 1.4 | Frontend: editor visual de reglas (modal o página dedicada) | `frontend/.../pricing/pricing-rules-page/` |

### Fase 2 — Motor básico (semana 3–4)

| # | Tarea | Detalle |
|---|---|---|
| 2.1 | Motor v1: `calculate_suggested_rate()` que aplica reglas estáticas (season, dow, los) | `server/.../revenue/services/pricing_engine.py` |
| 2.2 | Motor v1: generar `price_suggestions` para próximos 90 días para cada rate_plan activo | Service batch reutilizable |
| 2.3 | Auto-apply: aplicar sugerencias que cumplan criterio híbrido (confianza > 90% Y cambio < 10%) | Dentro del mismo motor |
| 2.4 | API: listar sugerencias + apply/reject manual | Endpoints + `pricing_suggestions.py` |
| 2.5 | Frontend: tabla de sugerencias con acciones (Aplicar/Rechazar) + indicador auto-applied | `frontend/.../pricing/pricing-suggestions-page/` |

### Fase 3 — Señales de demanda (semana 5–6)

| # | Tarea | Detalle |
|---|---|---|
| 3.1 | Pipeline ETL para `price_elasticity_signals` desde `fact_hotel_reservations` + `room_inventory_calendar` | `server/.../pricing_signals.py` |
| 3.2 | Motor v2: incorporar `demand_index` y `occupancy_forecast` en el cálculo | Actualizar `pricing_engine.py` |
| 3.3 | Dashboard "Demand Signals": booking pace, ocupación proyectada, demanda vs mercado | `frontend/.../pricing/pricing-signals-page/` |
| 3.4 | Simulador "what-if": probar cambios antes de aplicarlos | `pricing_engine.py` + nuevo endpoint `POST /simulate` |

### Fase 4 — Automatización y monitoreo (semana 7–8)

| # | Tarea | Detalle |
|---|---|---|
| 4.1 | DAG de Airflow: ejecutar motor cada N horas para todas las propiedades activas | `server/dags/hoteldata_pricing_engine.py` |
| 4.2 | Price change log + timeline visual en UI | `frontend/.../pricing/pricing-audit-page/` |
| 4.3 | Notificaciones al partner vía `notification_log` cuando hay sugerencias pendientes | Reutilizar sistema existente |
| 4.4 | Ajuste fino de umbrales híbridos (configurable por propiedad) | Campo `pricing_config` en la propiedad |

---

## 7. Nuevos archivos

```
server/src/app/modules/revenue/
├── services/
│   ├── __init__.py                    ← actualizar exports
│   ├── pricing_rules.py               ← NUEVO: CRUD reglas dinámicas
│   ├── pricing_engine.py              ← NUEVO: motor de cálculo
│   ├── pricing_suggestions.py         ← NUEVO: gestión de sugerencias
│   ├── pricing_signals.py             ← NUEVO: ETL señales de demanda
│   └── pricing_audit.py               ← NUEVO: cambio log + consultas
├── routes.py                          ← actualizar con nuevos endpoints

server/dags/
├── hoteldata_pricing_engine.py         ← NUEVO: DAG de Airflow

frontend/src/app/features/
├── pricing/                            ← NUEVO feature module
│   ├── pricing.routes.ts
│   ├── pages/
│   │   ├── pricing-rules-page/         ← Editor de reglas
│   │   ├── pricing-suggestions-page/   ← Sugerencias pendientes
│   │   ├── pricing-signals-page/       ← Dashboard de demanda
│   │   └── pricing-audit-page/         ← Historial de cambios
│   ├── services/
│   ├── models/
│   └── mappers/
```

---

## 8. Modo híbrido: reglas de auto-apply

| Condición | Acción |
|---|---|
| `confidence > 90` Y `|change_pct| < 10` | **Auto-apply**: la sugerencia se aplica automáticamente, se registra en `price_change_log` con `reason: "auto_demand"`, se envía notificación informativa al partner |
| `confidence > 90` Y `|change_pct| ≥ 10` | **Pendiente + notificación**: la sugerencia queda `pending`, se envía notificación al partner pidiendo revisión |
| `confidence ≤ 90` | **Pendiente**: la sugerencia queda `pending`, el partner decide en el dashboard |

Los umbrales de confianza y cambio porcentual serán configurables por propiedad mediante un campo `pricing_config` en la colección `dim_hotels`:

```json
{
  "pricing_config": {
    "auto_apply_enabled": true,
    "max_auto_change_pct": 10,
    "min_confidence": 90,
    "engine_frequency_hours": 6
  }
}
```

---

## 9. Principios de diseño

1. **El partner siempre tiene la última palabra** — el motor sugiere, el humano decide (excepto cambios pequeños y seguros)
2. **Auditabilidad total** — cada cambio de precio se registra con quién, cuándo y por qué
3. **Progresividad** — empezar con reglas estáticas simples, agregar complejidad después
4. **Rendimiento** — el motor se ejecuta en batch, no en línea; las sugerencias se precalculan
5. **Sin dependencias externas** — TODO el motor es Python puro + MongoDB, sin APIs de terceros
6. **Reutilización** — usar `notification_log` existente para alertar al partner, no crear sistema nuevo
