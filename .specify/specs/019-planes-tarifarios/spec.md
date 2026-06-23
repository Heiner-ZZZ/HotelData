# Especificacion: Planes Tarifarios

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O17 (Crear planes tarifarios con reglas de precio), CU-T06 (Validar consistencia de tarifas)

## 1. Objetivo

Crear planes tarifarios con precio base por tipo de habitacion y reglas de precio por temporada, permitiendo definir tarifas diferenciadas segun la demanda estacional.

## 2. Contexto

Los planes tarifarios definen el precio base por noche para cada tipo de habitacion. Pueden incluir reglas por temporada (alta, baja, eventos especiales) que sobreescriben el precio base en fechas especificas.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Revenue manager | Crea y gestiona planes tarifarios con reglas de precio |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir crear plan tarifario con nombre, descripcion y base_price | Alta |
| RF-002 | El sistema debe asociar el plan a un tipo de habitacion | Alta |
| RF-003 | El sistema debe permitir definir reglas por temporada (fechas, precio override) | Alta |
| RF-004 | El sistema debe permitir editar plan tarifario | Alta |
| RF-005 | El sistema debe permitir eliminar plan (solo sin reservas activas) | Alta |
| RF-006 | El sistema debe listar planes tarifarios por propiedad | Alta |
| RF-007 | El sistema debe validar que base_price > 0 | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | CRUD de planes menos de 500ms |
| RNF-002 | Validacion de reglas por temporada menos de 300ms |

## 6. Reglas de negocio

- Un plan tarifario se asocia a un tipo de habitacion de una propiedad
- base_price define la tarifa base por noche
- Las reglas de temporada tienen: nombre, start_date, end_date, price_override
- El precio de una regla de temporada sobreescribe base_price para ese rango
- No se puede eliminar un plan con reservas activas

## 7. Entradas

```json
{
  "name": "Tarifa Estandar",
  "description": "Tarifa base sin restricciones",
  "room_type_id": "rt_001",
  "base_price": 150.00,
  "seasonal_rules": [
    { "name": "Temporada Alta", "start_date": "2026-12-15", "end_date": "2027-01-15", "price_override": 250.00 },
    { "name": "Temporada Baja", "start_date": "2026-03-01", "end_date": "2026-04-30", "price_override": 100.00 }
  ]
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "rate_plan_id": "rp_001",
    "hotel_id": "HOTEL001",
    "name": "Tarifa Estandar",
    "room_type_id": "rt_001",
    "base_price": 150.00,
    "seasonal_rules": [],
    "created_at": "2026-06-22T10:30:00Z"
  }
}
```

## 9. Escenarios

### Escenario 1: Crear plan tarifario con reglas de temporada
```gherkin
Dado que el partner selecciona un tipo de habitacion
Cuando crea un plan tarifario con base_price y reglas de temporada
Entonces el sistema guarda el plan
Y las reglas de temporada se asocian correctamente
```

### Escenario 2: Eliminar plan con reservas activas
```gherkin
Dado que existe un plan tarifario con reservas activas
Cuando el partner intenta eliminarlo
Entonces el sistema responde 409 Conflict
Y el plan no se elimina
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Plan tarifario se crea correctamente asociado a room_type |
| CA-002 | Reglas de temporada se guardan y aplican correctamente |
| CA-003 | No se puede eliminar plan con reservas activas |
| CA-004 | base_price > 0 se valida |

## 11. Restricciones

- base_price en USD, positivo, maximo 99999.99
- Nombre del plan unico por propiedad
- Maximo 10 reglas de temporada por plan

## 12. Dependencias

- Coleccion rate_plans
- Coleccion rate_rules (reglas de temporada)
- Modulo partner/services/rates.py
- Depende de: tipos de habitacion (spec 016)

## 13. Fuera de alcance

- Pricing dinamico automatico basado en demanda
- Reglas de estancia minima por plan tarifario
