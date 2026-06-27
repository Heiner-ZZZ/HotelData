# Especificación: Gestionar Disponibilidad y Estado de Habitaciones

**Versión**: 1.0 | **Estado**: Draft | **Última actualización**: 2026-06-21

**Casos de uso TA07**: CU-O30 (Gestionar disponibilidad y estado de habitaciones)

## 1. Objetivo

Unificar en un solo caso de uso la consulta del estado operativo de todas las habitaciones (disponible, ocupada, limpieza, mantenimiento), la consulta de disponibilidad por habitación individual y la asignación de tipo de habitación a una habitación individual, centralizando la gestión del inventario físico del hotel.

## 2. Contexto

Este spec fusiona los antiguos CU-O30 (consultar estado), CU-O31 (asignar tipo) y CU-O32 (consultar disponibilidad x habitación) en un único caso de uso más cohesivo para simplificar la gestión del inventario hotelero.

## 3. Actores

| Actor | Descripción |
|-------|-------------|
| Recepcionista | Consulta estado de habitaciones y asigna tipos |
| Gerente de hotel | Supervisa disponibilidad y estado general |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar un grid con todas las habitaciones del hotel, su tipo, estado actual y última actualización | Alta |
| RF-002 | El sistema debe permitir filtrar por tipo de habitación, estado o rango de fechas | Alta |
| RF-003 | El sistema debe permitir cambiar el estado de una habitación (disponible, ocupada, limpieza, mantenimiento) | Alta |
| RF-004 | El sistema debe permitir asignar o reasignar tipo de habitación a una habitación individual | Media |
| RF-005 | El sistema debe mostrar el calendario de disponibilidad por habitación individual | Alta |
| RF-006 | El sistema debe registrar los cambios de estado en room_status_log con timestamp y usuario | Alta |

## 5. Requisitos no funcionales

| ID | Requisito | Descripción |
|----|-----------|-------------|
| RNF-001 | Rendimiento | Grid debe cargar en menos de 2s para hoteles con hasta 500 habitaciones |
| RNF-002 | Concurrencia | Cambios simultáneos desde recepción y housekeeping deben ser seguros |
| RNF-003 | Actualización | El grid debe refrescarse cada 30s (polling) |

## 6. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-001 | Una habitación en mantenimiento o limpieza no puede asignarse a un huésped |
| RN-002 | El cambio de estado queda registrado con timestamp y usuario |
| RN-003 | La disponibilidad se calcula desde room_inventory_calendar + room_status_log |

## 7. Entradas

prop_id, room_id (opcional), room_type_id (opcional), filtro_estado (opcional), fecha_desde, fecha_hasta

## 8. Salidas

Grid de estado de habitaciones con room_id, número, tipo, estado, última actualización, ocupante actual, fechas de ocupación. Calendario de disponibilidad por habitación.

## 9. Escenarios

### Escenario 1: Consultar estado de todas las habitaciones
```gherkin
Dado que el recepcionista está autenticado
Y el hotel tiene habitaciones configuradas
Cuando navega al panel de estado de habitaciones
Entonces el sistema muestra un grid con todas las habitaciones
Y cada habitación muestra número, tipo, estado y última actualización
```

### Escenario 2: Asignar tipo de habitación
```gherkin
Dado que la habitación 205 está en estado "disponible"
Cuando el recepcionista asigna el tipo "Suite Ejecutiva"
Entonces el sistema actualiza el tipo de habitación asignado
Y registra el cambio en room_status_log
```

### Escenario 3: Consultar disponibilidad
```gherkin
Cuando el recepcionista selecciona la habitación 205
Y solicita ver el calendario de disponibilidad
Entonces el sistema muestra disponibilidad por fecha para los próximos 30 días
```

## 10. Criterios de aceptación

| ID | Criterio |
|----|----------|
| CA-001 | Grid de estado se muestra correctamente con todas las habitaciones |
| CA-002 | Filtros funcionan correctamente |
| CA-003 | Cambio de estado queda registrado en room_status_log |
| CA-004 | Asignación de tipo de habitación funciona sin conflictos |

## 11. Restricciones

- Solo disponible para roles recepcionista y gerente_hotel
- Grid se actualiza con polling cada 30s

## 12. Dependencias

- `hotel_rooms` collection — Habitaciones físicas
- `room_status_log` collection — Log de cambios de estado
- `room_inventory_calendar` collection — Inventario por fecha
- `booking_orders` collection — Reservas activas

## 13. Fuera de alcance

- Gestión de limpieza y rotación (CU-T14)
- Programación de mantenimiento preventivo (CU-T15)