# Especificacion: Inventario y Disponibilidad

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O15 (Actualizar inventario diario de habitaciones), CU-T05 (Validar consistencia de inventario y disponibilidad)

## 1. Objetivo

Actualizar el inventario diario de habitaciones por fecha con optimistic locking y control de concurrencia, permitiendo modificar total de habitaciones, disponibles y bloqueadas.

## 2. Contexto

El inventario se gestiona por tipo de habitacion y fecha en room_inventory_calendar. Cada documento tiene un _id semantico {hotel_id}_{room_type_id}_{date}. Se usa optimistic locking (campo version) para evitar condiciones de carrera.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Gerente de hotel | Actualiza inventario diario de propiedades a su cargo |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar calendario mensual de inventario | Alta |
| RF-002 | El sistema debe permitir actualizar total/disponible/blocked por fecha | Alta |
| RF-003 | El sistema debe implementar optimistic locking con campo version | Alta |
| RF-004 | El sistema debe retornar 409 Conflict si hay conflicto de concurrencia | Alta |
| RF-005 | El sistema debe permitir actualizacion batch por rango de fechas | Alta |
| RF-006 | El sistema debe validar que available es menor o igual a total | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Actualizacion individual menos de 300ms |
| RNF-002 | Actualizacion batch (30 dias) menos de 2s |

## 6. Reglas de negocio

- available (disponibles) no puede ser mayor que total (totales)
- blocked (bloqueadas) no puede ser mayor que total
- El _id usa formato semantico: {hotel_id}_{room_type_id}_{YYYY-MM-DD}
- El campo version se incrementa en cada actualizacion
- Al hacer update: filter: { _id, version: current }, update: { ..., version: current + 1 }

## 7. Entradas

```json
{
  "total": 20,
  "available": 15,
  "blocked": 2,
  "version": 3
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "_id": "HOTEL001_rt_001_2026-07-15",
    "hotel_id": "HOTEL001",
    "room_type_id": "rt_001",
    "date": "2026-07-15",
    "total": 20,
    "available": 15,
    "blocked": 2,
    "booked": 3,
    "version": 4
  }
}
```

## 9. Escenarios

### Escenario 1: Actualizacion exitosa con optimistic locking
```gherkin
Dado que existe un registro de inventario con version=3
Cuando se actualiza con version=3
Entonces el sistema actualiza el registro
Y la version se incrementa a 4
```

### Escenario 2: Conflicto de concurrencia
```gherkin
Dado que existe un registro de inventario con version=3
Y otro usuario ya lo actualizo (version ahora es 4)
Cuando se intenta actualizar con version=3
Entonces el sistema responde 409 Conflict
```

### Escenario 3: Actualizacion batch mensual
```gherkin
Dado que el partner selecciona un rango de 30 dias
Y establece total=20 para todo el rango
Cuando envia POST /api/management/properties/HOTEL001/inventory/batch
Entonces el sistema actualiza los 30 registros
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Calendario mensual se muestra correctamente |
| CA-002 | Actualizacion individual funciona con optimistic locking |
| CA-003 | Conflicto de version retorna 409 |
| CA-004 | Available menor o igual a total se valida |
| CA-005 | Actualizacion batch funciona para rangos de fecha |

## 11. Restricciones

- total entero positivo, maximo 9999
- available y blocked enteros no negativos
- No se pueden modificar fechas pasadas (solo futuro)

## 12. Dependencias

- Coleccion room_inventory_calendar con _id semantico
- Modulo partner/services/inventory.py
- Indice: { hotel_id: 1, room_type_id: 1, date: 1 }

## 13. Fuera de alcance

- Sincronizacion automatica con reservas (el booked se calcula aparte)
- Bloqueos de disponibilidad por rango (cubierto en spec 018)
