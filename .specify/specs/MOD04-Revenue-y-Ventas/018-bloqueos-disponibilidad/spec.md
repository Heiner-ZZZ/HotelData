# Especificacion: Bloqueos de Disponibilidad

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O16 (Registrar bloqueos de disponibilidad y blackout dates), CU-T05 (Validar consistencia de inventario y disponibilidad)

## 1. Objetivo

Registrar bloqueos de disponibilidad y blackout dates por rangos de fecha, para impedir reservas en periodos especificos (mantenimiento, eventos privados, temporada cerrada).

## 2. Contexto

Los bloqueos de disponibilidad permiten al partner marcar rangos de fecha donde ciertos tipos de habitacion (o toda la propiedad) no estan disponibles para reserva. Al crear un bloqueo, se actualiza automaticamente room_inventory_calendar.blocked.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Gerente de hotel | Registra bloqueos de disponibilidad y blackout dates |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir crear bloqueo por rango de fechas | Alta |
| RF-002 | El sistema debe permitir especificar tipo de habitacion (o toda la propiedad) | Alta |
| RF-003 | El sistema debe permitir definir motivo del bloqueo | Media |
| RF-004 | El sistema debe validar que rangos no se solapen para el mismo room_type | Alta |
| RF-005 | El sistema debe actualizar room_inventory_calendar.blocked al crear bloqueo | Alta |
| RF-006 | El sistema debe permitir eliminar bloqueo | Alta |
| RF-007 | El sistema debe listar bloqueos activos de la propiedad | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Creacion de bloqueo (incluyendo actualizacion de calendario) menos de 1s |
| RNF-002 | Validacion de solapamiento menos de 300ms |

## 6. Reglas de negocio

- Un bloqueo aplica a un tipo de habitacion especifico o a toda la propiedad (room_type_id = null)
- Los rangos de fecha no pueden solaparse para el mismo room_type
- Al crear bloqueo, se actualiza room_inventory_calendar.blocked sumando las habitaciones bloqueadas
- Al eliminar bloqueo, se revierte la actualizacion en room_inventory_calendar
- No se pueden crear bloqueos en fechas pasadas

## 7. Entradas

```json
{
  "room_type_id": "rt_001",
  "start_date": "2026-08-01",
  "end_date": "2026-08-15",
  "reason": "Mantenimiento anual programado",
  "blocked_rooms": 5
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "blackout_id": "bk_001",
    "hotel_id": "HOTEL001",
    "room_type_id": "rt_001",
    "start_date": "2026-08-01",
    "end_date": "2026-08-15",
    "reason": "Mantenimiento anual programado",
    "blocked_rooms": 5,
    "created_at": "2026-06-22T10:30:00Z",
    "affected_days": 15
  }
}
```

## 9. Escenarios

### Escenario 1: Crear bloqueo exitosamente
```gherkin
Dado que el partner selecciona un rango de fecha futuro
Y un tipo de habitacion especifico
Cuando envia POST /api/management/properties/HOTEL001/blackouts
Entonces el sistema crea el bloqueo
Y actualiza room_inventory_calendar.blocked para las fechas afectadas
```

### Escenario 2: Bloqueo solapado
```gherkin
Dado que existe un bloqueo del 1 al 15 de agosto para rt_001
Cuando el partner intenta crear otro bloqueo del 10 al 20 de agosto para rt_001
Entonces el sistema responde 409 Conflict
Y el mensaje indica que los rangos se solapan
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Bloqueo se crea correctamente con rango de fechas |
| CA-002 | room_inventory_calendar se actualiza al crear bloqueo |
| CA-003 | Validacion de solapamiento funciona |
| CA-004 | Bloqueo se elimina y se revierte calendario |

## 11. Restricciones

- start_date debe ser mayor o igual a fecha actual
- end_date debe ser mayor o igual a start_date
- Rango maximo: 365 dias
- blocked_rooms debe ser > 0

## 12. Dependencias

- Coleccion blackout_dates
- Coleccion room_availability_blocks
- Coleccion room_inventory_calendar (actualizacion)
- Modulo partner/services/blackouts.py

## 13. Fuera de alcance

- Bloqueos recurrentes automaticos (ej. todos los lunes)
- Notificaciones al crear bloqueo
- notificaciones de cambios a usuarios
- ingreso de dias de blackout en el calendario de reservas (solo afecta disponibilidad)
- management de estrategias de negocio basadas en inventario
- mantenimientos programados de forma automatica/manual
