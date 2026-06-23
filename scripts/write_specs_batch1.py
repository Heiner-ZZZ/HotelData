#!/usr/bin/env python3
"""Write detailed spec content to all 37 spec files (014-050)."""
import os

BASE = os.path.join(os.path.dirname(__file__), '..', '.specify', 'specs')

specs = {}

specs['014-editar-nombre-comercial'] = """# Especificacion: Editar Nombre Comercial

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O12 (Actualizar perfil de propiedad), CU-T03 (Validar y auditar cambios en datos de propiedad)

## 1. Objetivo

Permitir que el hotel partner edite el nombre comercial de su propiedad con manual_override, preservando el prop_id tecnico y registrando todos los cambios en el historial de auditoria.

## 2. Contexto

Las propiedades hoteleras tienen un prop_id tecnico (asignado por el sistema o el ETL) que no debe modificarse. El nombre comercial es un campo de presentacion que el partner puede personalizar. Los cambios se guardan en manual_override para no pisar datos provenientes del ETL. Cada cambio queda registrado en hotel_profile_changes para trazabilidad.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Hotel partner | Edita nombre comercial de sus propiedades asignadas |
| Gerente de hotel | Edita nombre comercial de las propiedades que gestiona |
| Super Admin | Edita nombre comercial de cualquier propiedad |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir editar el nombre comercial de la propiedad | Alta |
| RF-002 | El sistema debe preservar el prop_id tecnico sin modificaciones | Alta |
| RF-003 | El sistema debe guardar el cambio en manual_override.nombre_comercial | Alta |
| RF-004 | El sistema debe registrar cada cambio en hotel_profile_changes con old/new value | Alta |
| RF-005 | El sistema debe actualizar verified_at al modificar el nombre | Media |
| RF-006 | El sistema debe validar que el hotel pertenece al partner que edita | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | La operacion debe completarse en menos de 500ms |
| RNF-002 | Solo campos en whitelist pueden ser modificados (proteccion contra mass assignment) |
| RNF-003 | El historial de cambios debe conservarse indefinidamente |

## 6. Reglas de negocio

- prop_id no se puede modificar bajo ninguna circunstancia
- El nombre comercial se almacena en manual_override para no sobrescribir datos ETL
- Cada cambio se registra en hotel_profile_changes con hotel_id, field, old_value, new_value, changed_by, changed_at
- Solo hotel_partner, gerente_hotel y super_admin pueden editar
- El hotel debe estar asignado al partner (verificacion de propiedad)
- verified_at se actualiza a now() cuando cambia el nombre

## 7. Entradas

```json
{
  "nombre_comercial": "Hotel Vista Hermosa Premium"
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "prop_id": "HOTEL001",
    "nombre_comercial": "Hotel Vista Hermosa Premium",
    "manual_override": {
      "nombre_comercial": "Hotel Vista Hermosa Premium",
      "updated_by": "user_abc123",
      "updated_at": "2026-06-22T10:30:00Z"
    },
    "verified_at": "2026-06-22T10:30:00Z"
  }
}
```

## 9. Escenarios

### Escenario 1: Edicion exitosa de nombre comercial
```gherkin
Dado que el hotel partner esta autenticado
Y tiene asignada la propiedad HOTEL001
Cuando envia PUT /api/partner/properties/HOTEL001/profile
Y el body contiene el nuevo nombre comercial
Entonces el sistema responde 200
Y el campo nombre_comercial se actualiza en hotels.manual_override
Y se registra el cambio en hotel_profile_changes
```

### Escenario 2: Partner intenta editar propiedad no asignada
```gherkin
Dado que el hotel partner esta autenticado
Y NO tiene asignada la propiedad HOTEL999
Cuando envia PUT /api/partner/properties/HOTEL999/profile
Entonces el sistema responde 403 Forbidden
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | El nombre comercial se actualiza correctamente |
| CA-002 | prop_id permanece sin cambios despues de la edicion |
| CA-003 | El cambio queda registrado en hotel_profile_changes |
| CA-004 | verified_at se actualiza al modificar el nombre |
| CA-005 | Partner sin asignacion recibe 403 |

## 11. Restricciones

- El nombre comercial no puede estar vacio
- Longitud maxima: 200 caracteres
- No se permiten caracteres especiales no imprimibles

## 12. Dependencias

- Coleccion hotels (lectura/escritura)
- Coleccion hotel_profile_changes (insert)
- Modulo partner/services/profile.py
- Middleware de autenticacion y verificacion de propiedad

## 13. Fuera de alcance

- Edicion de otros campos del perfil (cubierto en otros specs)
- Sincronizacion con PocketBase o fuente ETL
"""

specs['015-historial-cambios'] = """# Especificacion: Historial de Cambios

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O13 (Consultar historial de cambios de propiedad), CU-T10 (Auditar cambios y actividad del sistema)

## 1. Objetivo

Consultar el historial de cambios de la propiedad (perfil y contenido) con filtros por fecha, campo y usuario, para fines de auditoria y trazabilidad.

## 2. Contexto

Cada cambio en el perfil de la propiedad (hotel_profile_changes) o en el contenido (hotel_content_changes) se registra automaticamente. Este spec permite consultar ese historial de forma filtrada y paginada.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Hotel partner | Consulta cambios de sus propiedades |
| Gerente de hotel | Consulta cambios de propiedades que gestiona |
| Super Admin | Consulta cambios de cualquier propiedad |
| Auditor de datos | Revisa trazabilidad de cambios |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe listar cambios por propiedad con paginacion | Alta |
| RF-002 | El sistema debe permitir filtrar por rango de fechas | Alta |
| RF-003 | El sistema debe permitir filtrar por campo modificado | Media |
| RF-004 | El sistema debe permitir filtrar por usuario que realizo el cambio | Media |
| RF-005 | El sistema debe mostrar old_value y new_value por campo | Alta |
| RF-006 | El sistema debe mostrar quien realizo el cambio y cuando | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | La consulta debe responder en menos de 1s con indices adecuados |
| RNF-002 | El historial debe conservarse indefinidamente |

## 6. Reglas de negocio

- Los datos son inmutables (solo lectura, no se pueden modificar ni eliminar registros de auditoria)
- El historial incluye cambios de perfil (hotel_profile_changes) y contenido (hotel_content_changes)
- Los registros se ordenan por changed_at descendente (mas reciente primero)

## 7. Entradas

GET /api/partner/properties/{id}/history?from=2026-01-01&to=2026-06-22&field=nombre_comercial&user=user_abc&page=1&per_page=20

## 8. Salidas

```json
{
  "data": [
    {
      "id": "change_001",
      "field": "nombre_comercial",
      "old_value": "Hotel Vista Hermosa",
      "new_value": "Hotel Vista Hermosa Premium",
      "changed_by": "user_abc123",
      "changed_by_name": "Carlos Lopez",
      "changed_at": "2026-06-22T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "pages": 3
  }
}
```

## 9. Escenarios

### Escenario 1: Consultar historial con filtros
```gherkin
Dado que el hotel partner esta autenticado
Y tiene asignada la propiedad HOTEL001
Cuando consulta GET /api/partner/properties/HOTEL001/history?from=2026-01-01&field=nombre_comercial
Entonces el sistema responde 200
Y la respuesta incluye solo cambios del campo nombre_comercial
Y los resultados estan paginados
```

### Escenario 2: Consultar detalle de un cambio especifico
```gherkin
Dado que existe un cambio con ID change_001 en HOTEL001
Cuando el partner consulta GET /api/partner/properties/HOTEL001/history/change_001
Entonces el sistema responde 200
Y la respuesta incluye old_value, new_value, changed_by y changed_at
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | La lista paginada funciona correctamente |
| CA-002 | Los filtros por fecha reducen correctamente los resultados |
| CA-003 | Los filtros por campo funcionan correctamente |
| CA-004 | El detalle de cambio muestra old/new value correctamente |

## 11. Restricciones

- Solo se puede consultar historial de propiedades a las que se tiene acceso
- No se pueden modificar ni eliminar registros de auditoria

## 12. Dependencias

- Coleccion hotel_profile_changes (lectura)
- Coleccion hotel_content_changes (lectura)
- Indice compuesto: { hotel_id: 1, changed_at: -1 }
- Indice compuesto: { hotel_id: 1, field: 1, changed_at: -1 }

## 13. Fuera de alcance

- Exportacion del historial a CSV/PDF
- Auditoria de actividad de usuarios (sesiones, logins)
"""

specs['016-tipos-habitacion'] = """# Especificacion: Tipos de Habitacion

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O14 (Gestionar tipos de habitacion y habitaciones fisicas), CU-T04 (Validar integridad de datos de habitaciones)

## 1. Objetivo

Crear y gestionar tipos de habitacion y habitaciones fisicas por propiedad, permitiendo definir nombre, capacidad maxima, tarifa base, amenities y cantidad de habitaciones de ese tipo.

## 2. Contexto

Cada propiedad hotelera tiene uno o mas tipos de habitacion (ej. Simple, Doble, Suite). Cada tipo tiene una capacidad maxima de huespedes, una tarifa base (por noche), amenidades incluidas y un numero de habitaciones fisicas de ese tipo.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Hotel partner | Gestiona tipos de habitacion de sus propiedades |
| Gerente de hotel | Gestiona tipos de habitacion de propiedades a su cargo |
| Recepcionista | Consulta tipos de habitacion (solo lectura) |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir crear tipo de habitacion con nombre, descripcion, max_guests y base_rate | Alta |
| RF-002 | El sistema debe permitir editar tipo de habitacion | Alta |
| RF-003 | El sistema debe permitir eliminar tipo de habitacion (solo sin reservas activas) | Alta |
| RF-004 | El sistema debe listar tipos de habitacion por propiedad | Alta |
| RF-005 | El sistema debe validar que max_guests mayor o igual a 1 | Alta |
| RF-006 | El sistema debe validar que base_rate > 0 | Alta |
| RF-007 | El sistema debe validar que el nombre del tipo es unico dentro de la misma propiedad | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | CRUD completo responde en menos de 500ms |
| RNF-002 | Validacion de eliminacion contra reservas activas en menos de 200ms |

## 6. Reglas de negocio

- Un tipo de habitacion pertenece a una sola propiedad
- No se puede eliminar un tipo de habitacion con reservas activas o futuras
- max_guests debe ser mayor o igual a 1 (adultos maximo)
- base_rate debe ser > 0 (tarifa base por noche en USD)
- El nombre del tipo debe ser unico dentro de la misma propiedad
- Al crear un tipo, se pueden crear N habitaciones fisicas en hotel_rooms

## 7. Entradas (creacion)

```json
{
  "name": "Suite Presidencial",
  "description": "Suite de lujo con vista al mar",
  "max_guests": 4,
  "base_rate": 350.00,
  "amenities": ["wifi", "tv", "minibar", "jacuzzi"],
  "total_rooms": 5,
  "room_size_sqm": 65
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "room_type_id": "rt_001",
    "hotel_id": "HOTEL001",
    "name": "Suite Presidencial",
    "max_guests": 4,
    "base_rate": 350.00,
    "amenities": ["wifi", "tv", "minibar", "jacuzzi"],
    "total_rooms": 5,
    "created_at": "2026-06-22T10:30:00Z"
  }
}
```

## 9. Escenarios

### Escenario 1: Crear tipo de habitacion exitosamente
```gherkin
Dado que el hotel partner esta autenticado
Y tiene asignada la propiedad HOTEL001
Cuando envia POST /api/partner/properties/HOTEL001/room-types
Y el body contiene un tipo de habitacion valido
Entonces el sistema responde 201
Y se crea el tipo en room_types
Y se crean N habitaciones fisicas en hotel_rooms
```

### Escenario 2: Eliminar tipo con reservas activas
```gherkin
Dado que existe un tipo de habitacion con reservas activas
Cuando el partner intenta eliminarlo
Entonces el sistema responde 409 Conflict
Y el tipo no se elimina
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | CRUD completo de tipos de habitacion funciona |
| CA-002 | Validacion de max_guests mayor o igual a 1 funciona |
| CA-003 | Validacion de base_rate > 0 funciona |
| CA-004 | Validacion de nombre unico por propiedad funciona |
| CA-005 | Validacion de eliminacion con reservas activas funciona |

## 11. Restricciones

- base_rate en USD, positivo, maximo 99999.99
- max_guests maximo 20
- Nombre maximo 100 caracteres, unico por propiedad

## 12. Dependencias

- Coleccion room_types
- Coleccion hotel_rooms (creacion de habitaciones fisicas)
- Modulo partner/services/rooms.py
- Verificacion de reservas activas en booking_orders

## 13. Fuera de alcance

- Amenities por tipo de habitacion (incluido en el spec)
- Tarifas dinamicas por tipo (cubierto en spec 019-020)
"""

specs['017-inventario-disponibilidad'] = """# Especificacion: Inventario y Disponibilidad

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O15 (Actualizar inventario diario de habitaciones), CU-T05 (Validar consistencia de inventario y disponibilidad)

## 1. Objetivo

Actualizar el inventario diario de habitaciones por fecha con optimistic locking y control de concurrencia, permitiendo modificar total de habitaciones, disponibles y bloqueadas.

## 2. Contexto

El inventario se gestiona por tipo de habitacion y fecha en room_inventory_calendar. Cada documento tiene un _id semantico {hotel_id}_{room_type_id}_{date}. Se usa optimistic locking (campo version) para evitar condiciones de carrera.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Hotel partner | Actualiza inventario diario |
| Gerente de hotel | Actualiza inventario de propiedades a su cargo |
| Recepcionista | Consulta disponibilidad (solo lectura) |

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
Cuando envia POST /api/partner/properties/HOTEL001/inventory/batch
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
"""

specs['018-bloqueos-disponibilidad'] = """# Especificacion: Bloqueos de Disponibilidad

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O16 (Registrar bloqueos de disponibilidad y blackout dates), CU-T05 (Validar consistencia de inventario y disponibilidad)

## 1. Objetivo

Registrar bloqueos de disponibilidad y blackout dates por rangos de fecha, para impedir reservas en periodos especificos (mantenimiento, eventos privados, temporada cerrada).

## 2. Contexto

Los bloqueos de disponibilidad permiten al partner marcar rangos de fecha donde ciertos tipos de habitacion (o toda la propiedad) no estan disponibles para reserva. Al crear un bloqueo, se actualiza automaticamente room_inventory_calendar.blocked.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Hotel partner | Crea y elimina bloqueos de disponibilidad |
| Gerente de hotel | Gestiona bloqueos de propiedades a su cargo |

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
Cuando envia POST /api/partner/properties/HOTEL001/blackouts
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
"""

specs['019-planes-tarifarios'] = """# Especificacion: Planes Tarifarios

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O17 (Crear planes tarifarios con reglas de precio), CU-T06 (Validar consistencia de tarifas)

## 1. Objetivo

Crear planes tarifarios con precio base por tipo de habitacion y reglas de precio por temporada, permitiendo definir tarifas diferenciadas segun la demanda estacional.

## 2. Contexto

Los planes tarifarios definen el precio base por noche para cada tipo de habitacion. Pueden incluir reglas por temporada (alta, baja, eventos especiales) que sobreescriben el precio base en fechas especificas.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Hotel partner | Crea y gestiona planes tarifarios |
| Revenue manager | Define estrategia de precios |
| Gerente de hotel | Aprueba cambios de tarifas |

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
"""

specs['020-tarifas-calendario'] = """# Especificacion: Tarifas Calendario

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O18 (Configurar tarifas por fecha en calendario de precios), CU-T06 (Validar consistencia de tarifas)

## 1. Objetivo

Configurar tarifas por fecha y plan tarifario en el calendario de precios, permitiendo establecer precios especificos por dia que pueden diferir del base_price del plan.

## 2. Contexto

El calendario de tarifas (hotel_rate_calendar) almacena el precio por noche para cada combinacion de hotel, plan tarifario y fecha. Cada entrada tiene un _id semantico {hotel_id}_{rate_plan_id}_{date}.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Hotel partner | Configura tarifas por fecha |
| Revenue manager | Define precios por temporada |
| Gerente de hotel | Revisa y aprueba tarifas |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar calendario mensual de precios por plan tarifario | Alta |
| RF-002 | El sistema debe permitir editar precio por fecha individual | Alta |
| RF-003 | El sistema debe permitir actualizacion batch por rango de fechas | Alta |
| RF-004 | El sistema debe validar que price > 0 | Alta |
| RF-005 | El sistema debe generar entradas automaticas basadas en base_price + reglas de temporada | Media |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Actualizacion batch (30 dias) menos de 2s |
| RNF-002 | Carga de calendario mensual menos de 1s |

## 6. Reglas de negocio

- El precio por fecha puede diferir del base_price del plan tarifario
- _id semantico: {hotel_id}_{rate_plan_id}_{YYYY-MM-DD}
- Si no hay entrada en el calendario para una fecha, se usa base_price del plan
- Las reglas de temporada se precargan al crear el plan, pero el partner puede sobreescribir

## 7. Entradas

```json
{
  "date": "2026-07-15",
  "price": 180.00
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "_id": "HOTEL001_rp_001_2026-07-15",
    "hotel_id": "HOTEL001",
    "rate_plan_id": "rp_001",
    "date": "2026-07-15",
    "price": 180.00,
    "source": "manual_override"
  }
}
```

## 9. Escenarios

### Escenario 1: Actualizar precio para una fecha especifica
```gherkin
Dado que el partner ve el calendario de julio para el plan rp_001
Cuando actualiza el precio del 15 de julio a 180.00
Entonces el sistema guarda el precio en hotel_rate_calendar
Y el calendario muestra el nuevo precio
```

### Escenario 2: Actualizacion batch mensual
```gherkin
Dado que el partner selecciona un rango de 30 dias para el plan rp_001
Cuando aplica precio 200.00 para fines de semana
Entonces el sistema actualiza solo los sabados y domingos del rango
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Calendario mensual se muestra con precios por dia |
| CA-002 | Precio individual se actualiza correctamente |
| CA-003 | Actualizacion batch funciona para rangos |
| CA-004 | price > 0 se valida |

## 11. Restricciones

- price en USD, positivo, maximo 99999.99
- No se pueden modificar fechas pasadas
- Fechas sin entrada usan base_price del plan

## 12. Dependencias

- Coleccion hotel_rate_calendar
- Modulo partner/services/rates.py
- Depende de: planes tarifarios (spec 019)

## 13. Fuera de alcance

- Precios dinamicos automaticos basados en ocupacion
- Reglas de pricing por anticipacion (booking window)
"""

specs['021-promociones-cupones'] = """# Especificacion: Promociones y Cupones

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O19 (Crear promociones con porcentaje descuento), CU-T01 (Gestionar campanas promocionales)

## 1. Objetivo

Crear campanas promocionales con porcentaje de descuento y codigos de cupon asociados, para ofrecer tarifas especiales en periodos especificos.

## 2. Contexto

Las promociones permiten al partner ofrecer descuentos porcentuales sobre las tarifas base. Cada campana puede tener multiples codigos de cupon que los huespedes pueden canjear.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Revenue manager | Crea y gestiona campanas promocionales |
| Marketing hotelero | Define descuentos y segmentos objetivo |
| Cliente | Usa codigo de cupon al reservar |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir crear campana con nombre, descuento %, fechas vigencia | Alta |
| RF-002 | El sistema debe generar N codigos de cupon al crear la campana | Alta |
| RF-003 | El sistema debe permitir activar/desactivar campana | Alta |
| RF-004 | El sistema debe listar campanas por propiedad | Alta |
| RF-005 | El sistema debe validar descuento entre 1% y 100% | Alta |
| RF-006 | El sistema debe permitir editar campana | Media |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Creacion de campana con 100 cupones menos de 1s |
| RNF-002 | Validacion de cupon en reserva menos de 300ms |

## 6. Reglas de negocio

- Una promocion tiene un % de descuento (1-100)
- Al crear campana, se generan N codigos de cupon asociados
- Los cupones tienen fecha de expiracion (la misma de la campana)
- Un cupon solo puede usarse una vez
- Las promociones pueden ser por propiedad (hotel_id) o globales (hotel_id = null)

## 7. Entradas

```json
{
  "name": "Descuento Verano",
  "description": "20% de descuento en estancias de verano",
  "discount_percentage": 20,
  "start_date": "2026-07-01",
  "end_date": "2026-08-31",
  "hotel_id": "HOTEL001",
  "coupon_count": 100,
  "min_nights": 2
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "promotion_id": "promo_001",
    "name": "Descuento Verano",
    "discount_percentage": 20,
    "coupons_generated": 100,
    "coupons_used": 0,
    "status": "active",
    "valid_from": "2026-07-01",
    "valid_to": "2026-08-31"
  }
}
```

## 9. Escenarios

### Escenario 1: Crear campana con cupones
```gherkin
Dado que el revenue manager define una promocion de 20% para verano
Cuando crea la campana con 100 cupones
Entonces el sistema crea la campana en promotion_campaigns
Y genera 100 codigos unicos en coupon_codes
```

### Escenario 2: Usar cupon en reserva
```gherkin
Dado que existe un cupon valido
Cuando el cliente lo ingresa al reservar
Entonces el sistema aplica el descuento
Y marca el cupon como usado
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Campana se crea con cupones generados |
| CA-002 | Cupon se valida y descuenta correctamente |
| CA-003 | Cupon usado no puede reutilizarse |
| CA-004 | Campana expirada no aplica descuento |

## 11. Restricciones

- discount_percentage entre 1 y 100
- coupon_count maximo 1000 por campana
- Codigos de cupon: 8-12 caracteres alfanumericos

## 12. Dependencias

- Coleccion promotion_campaigns
- Coleccion coupon_codes
- Modulo revenue/services/promotions.py

## 13. Fuera de alcance

- Envio automatico de cupones por email
- Segmentacion avanzada de clientes para promociones
"""

specs['022-politicas-hoteleras'] = """# Especificacion: Politicas Hoteleras

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O20 (Gestionar politicas hoteleras), CU-T07 (Validar consistencia de politicas y contenido)

## 1. Objetivo

Gestionar las politicas del hotel: horarios de check-in/out, politica de cancelacion, mascotas, ninos y restricciones de estancia.

## 2. Contexto

Cada propiedad hotelera tiene politicas que definen las reglas de operacion. Se almacenan en hotel_policies y los cambios se registran en hotel_content_changes.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Hotel partner | Configura politicas de su propiedad |
| Gerente de hotel | Aprueba cambios de politicas |
| Cliente | Consulta politicas antes de reservar |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir configurar horario de check-in y check-out | Alta |
| RF-002 | El sistema debe permitir configurar politica de cancelacion (horas antes) | Alta |
| RF-003 | El sistema debe permitir indicar si se admiten mascotas y costo | Alta |
| RF-004 | El sistema debe permitir indicar politica de ninos y cargo por cama extra | Alta |
| RF-005 | El sistema debe permitir configurar estancia minima y maxima | Alta |
| RF-006 | El sistema debe validar que check-out > check-in | Alta |
| RF-007 | El sistema debe registrar cambios en hotel_content_changes | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Actualizacion de politicas menos de 500ms |
| RNF-002 | Las politicas deben ser accesibles sin autenticacion (lectura publica) |

## 6. Reglas de negocio

- check_out_time debe ser despues de check_in_time
- cancellation_hours define horas antes del check-in para cancelacion gratuita
- min_stay y max_stay en noches minimas/maximas
- Los cambios se registran en hotel_content_changes para trazabilidad

## 7. Entradas

```json
{
  "check_in_time": "15:00",
  "check_out_time": "12:00",
  "cancellation_hours": 48,
  "pets_allowed": true,
  "pet_fee": 25.00,
  "children_allowed": true,
  "extra_bed_fee": 30.00,
  "min_stay": 1,
  "max_stay": 30
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "hotel_id": "HOTEL001",
    "check_in_time": "15:00",
    "check_out_time": "12:00",
    "cancellation_hours": 48,
    "pets_allowed": true,
    "pet_fee": 25.00,
    "updated_at": "2026-06-22T10:30:00Z"
  }
}
```

## 9. Escenarios

### Escenario 1: Configurar politicas exitosamente
```gherkin
Dado que el partner esta en la pagina de politicas
Cuando completa el formulario con horarios y cargos
Entonces el sistema guarda las politicas en hotel_policies
Y registra el cambio en hotel_content_changes
```

### Escenario 2: Check-out antes que check-in
```gherkin
Dado que el partner ingresa check_in=15:00 y check_out=14:00
Cuando intenta guardar
Entonces el sistema responde 400 Bad Request
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Politicas se guardan correctamente |
| CA-002 | Check-out > check-in se valida |
| CA-003 | Politicas son accesibles sin autenticacion (lectura) |
| CA-004 | Cambios quedan registrados en hotel_content_changes |

## 11. Restricciones

- check_in_time y check_out_time en formato HH:MM
- cancellation_hours entero positivo, maximo 720 (30 dias)
- min_stay mayor o igual a 1, max_stay mayor o igual a min_stay, maximo 365

## 12. Dependencias

- Coleccion hotel_policies
- Coleccion hotel_content_changes (auditoria)
- Modulo partner/services/content/save.py

## 13. Fuera de alcance

- Politicas diferenciadas por temporada
- Politicas de cancelacion no reembolsable vs reembolsable
"""

specs['023-amenities-imagenes'] = """# Especificacion: Amenities e Imagenes

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O21 (Actualizar amenities, imagenes y contenido comercial), CU-T08 (Validar contenido multimedia de propiedades)

## 1. Objetivo

Actualizar amenities, imagenes y contenido comercial de la propiedad para mejorar la presentacion en el portal de busqueda y detalle del hotel.

## 2. Contexto

El contenido comercial del hotel incluye amenities (piscina, wifi, gym, etc.), imagenes (fotos de la propiedad) y descripciones. Este contenido se muestra al cliente en la busqueda y detalle del hotel.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Hotel partner | Actualiza contenido comercial de su propiedad |
| Marketing hotelero | Mejora descripciones y fotos |
| Gerente de hotel | Aprueba contenido |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir actualizar lista de amenities | Alta |
| RF-002 | El sistema debe permitir subir imagenes (multipart) | Alta |
| RF-003 | El sistema debe permitir eliminar imagenes | Alta |
| RF-004 | El sistema debe permitir reordenar imagenes (la primera es portada) | Alta |
| RF-005 | El sistema debe permitir editar descripcion larga y highlights | Alta |
| RF-006 | El sistema debe limitar a 10 imagenes por propiedad | Alta |
| RF-007 | El sistema debe registrar cambios en hotel_content_changes | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Subida de imagen menos de 2s (imagen menos de 5MB) |
| RNF-002 | El contenido debe servirse rapido con cache CDN |

## 6. Reglas de negocio

- Las imagenes se almacenan como base64 o URL (segun implementacion)
- Maximo 10 imagenes por propiedad
- La primera imagen es la principal (portada)
- Amenities son un array de strings (checkboxes en UI)
- Los cambios se registran en hotel_content_changes

## 7. Entradas

```json
{
  "amenities": ["wifi", "piscina", "gimnasio", "restaurante", "estacionamiento", "spa"],
  "description": "Hermoso hotel frente al mar con todas las comodidades...",
  "highlights": ["Vista al mar", "Desayuno incluido", "Piscina climatizada"]
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "hotel_id": "HOTEL001",
    "amenities": ["wifi", "piscina", "gimnasio", "restaurante", "estacionamiento", "spa"],
    "images_count": 5,
    "primary_image": "https://.../img_001.jpg",
    "updated_at": "2026-06-22T10:30:00Z"
  }
}
```

## 9. Escenarios

### Escenario 1: Actualizar amenities
```gherkin
Dado que el partner edita el contenido del hotel
Cuando selecciona amenities y escribe descripcion
Entonces el sistema guarda en hotel_content_pages
Y registra el cambio en hotel_content_changes
```

### Escenario 2: Subir imagen
```gherkin
Dado que el partner sube una imagen (multipart)
Cuando la imagen es valida (menos de 5MB)
Entonces el sistema la guarda en hotel_images
Y la muestra en la galeria
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Amenities se actualizan correctamente |
| CA-002 | Imagenes se suben y eliminan correctamente |
| CA-003 | Limite de 10 imagenes se respeta |
| CA-004 | Descripcion se guarda correctamente |
| CA-005 | Cambios quedan en hotel_content_changes |

## 11. Restricciones

- Imagen maxima 5MB, formatos: JPEG, PNG, WebP
- Descripcion maxima 5000 caracteres
- Maximo 10 imagenes, 50 amenities

## 12. Dependencias

- Coleccion hotel_content_pages
- Coleccion hotel_images
- Coleccion hotel_content_changes
- Modulo partner/services/content/save.py y content/images.py

## 13. Fuera de alcance

- Procesamiento automatico de imagenes (thumbnails, optimizacion)
- Videos de propiedad
"""

specs['024-registro-resenas'] = """# Especificacion: Registro de Resenas

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O22 (Registrar resena de estancia), CU-T13 (Gestionar resenas)

## 1. Objetivo

Permitir que los huespedes registren resenas de su estancia con calificacion (1-5), titulo y comentario, con dual-write a fact_reviews para analitica.

## 2. Contexto

Solo huespedes con estancia completada pueden resenar. Una resena por reserva. Las resenas pasan por moderacion (spec 025) antes de ser publicas.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Cliente | Registra resena post-estancia |
| Sistema | Valida elegibilidad y escribe dual-write |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir crear resena con rating, titulo y comentario | Alta |
| RF-002 | El sistema debe validar que solo huespedes post-estancia pueden resenar | Alta |
| RF-003 | El sistema debe validar una resena por reserva (unique booking_id) | Alta |
| RF-004 | El sistema debe asignar moderation_status = pending inicial | Alta |
| RF-005 | El sistema debe hacer dual-write a fact_reviews | Alta |
| RF-006 | El sistema debe mostrar top 5 resenas aprobadas en detalle del hotel | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Creacion de resena menos de 500ms incluyendo dual-write |
| RNF-002 | Carga de resenas en detalle del hotel menos de 300ms |

## 6. Reglas de negocio

- Solo huespedes con estancia completada pueden resenar (booking status = checked_out)
- Una resena por reserva (unique booking_id)
- Rating obligatorio (1-5), titulo y comentario opcionales
- Dual-write obligatorio a fact_reviews para analitica

## 7. Entradas

```json
{
  "booking_id": "BK-2026-001",
  "rating": 4,
  "title": "Excelente estancia",
  "comment": "Muy buen hotel, el personal fue atento.",
  "categories": { "cleanliness": 5, "location": 4, "service": 5 }
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "review_id": "rev_001",
    "booking_id": "BK-2026-001",
    "rating": 4,
    "moderation_status": "pending",
    "created_at": "2026-06-22T10:30:00Z"
  }
}
```

## 9. Escenarios

### Escenario 1: Registrar resena exitosamente
```gherkin
Dado que el huesped tiene una estancia completada en HOTEL001
Cuando envia POST /api/reviews con rating y comentario
Entonces el sistema responde 201
Y la resena queda en estado pending
Y se escribe en fact_reviews
```

### Escenario 2: Resena duplicada
```gherkin
Dado que ya existe una resena para la reserva BK-2026-001
Cuando el huesped intenta crear otra resena para la misma reserva
Entonces el sistema responde 409 Conflict
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Resena se crea con rating obligatorio |
| CA-002 | Una resena por booking_id |
| CA-003 | Dual-write a fact_reviews funciona |
| CA-004 | moderation_status inicia como pending |

## 11. Restricciones

- Rating: entero 1-5
- Titulo: maximo 200 caracteres
- Comentario: maximo 5000 caracteres

## 12. Dependencias

- Coleccion reviews
- Coleccion fact_reviews (dual-write)
- Modulo modules/reviews/services/reviews.py
- Verificacion de estatus de booking en booking_orders

## 13. Fuera de alcance

- Moderacion automatica con IA
- Notificaciones al hotel cuando recibe resena
"""

specs['025-moderacion-resenas'] = """# Especificacion: Moderacion de Resenas

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O23 (Moderar y responder resena), CU-T13 (Gestionar resenas, reputacion online y respuestas)

## 1. Objetivo

Permitir que marketing o super admin modere las resenas de huespedes (aprobar/rechazar) y que el hotel partner responda a resenas aprobadas.

## 2. Contexto

Las resenas pasan por un flujo de moderacion antes de ser publicas. Esto permite filtrar contenido inapropiado, spam o resenas fraudulentas.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Marketing hotelero | Modera resenas y responde en nombre del hotel |
| Super Admin | Moderacion general del sistema |
| Hotel partner | Responde a resenas de su propiedad |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe listar resenas pendientes de moderacion | Alta |
| RF-002 | El sistema debe permitir aprobar resena | Alta |
| RF-003 | El sistema debe permitir rechazar resena | Alta |
| RF-004 | El sistema debe permitir responder a resena aprobada | Alta |
| RF-005 | El sistema debe validar que solo marketing/super admin pueden moderar | Alta |
| RF-006 | El sistema debe validar que solo hotel_partner del hotel puede responder | Alta |

## 5. Reglas de negocio

- Solo marketing_hotelero y super_admin pueden moderar
- Solo hotel_partner del hotel puede responder
- No se puede responder una resena rechazada
- Las resenas aprobadas son visibles en el detalle del hotel
- Una vez aprobada o rechazada, no se puede cambiar

## 6. Entradas (moderacion)

```json
{
  "action": "approve",
  "moderation_note": "Resena verificada, cliente confirmado"
}
```

## 7. Salidas

```json
{
  "success": true,
  "data": {
    "review_id": "rev_001",
    "moderation_status": "approved",
    "moderated_by": "user_admin",
    "moderated_at": "2026-06-22T10:30:00Z"
  }
}
```

## 8. Escenarios

### Escenario 1: Moderar resena
```gherkin
Dado que marketing ve una resena pendiente
Cuando la aprueba
Entonces el sistema cambia moderation_status a approved
Y la resena se vuelve visible en el hotel
```

### Escenario 2: Rechazar resena
```gherkin
Dado que marketing ve una resena con contenido inapropiado
Cuando la rechaza
Entonces el sistema cambia moderation_status a rejected
Y la resena no se muestra publicamente
```

## 9. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Moderacion (aprobar/rechazar) funciona correctamente |
| CA-002 | Solo usuarios autorizados pueden moderar |
| CA-003 | Respuesta se guarda solo en resenas aprobadas |

## 10. Dependencias

- Coleccion reviews
- Modulo modules/reviews/services/reviews.py
- Depende de: registro de resenas (spec 024)

## 11. Fuera de alcance

- Moderacion automatica con IA
- Apelacion de resena rechazada por el cliente
"""

specs['026-facturacion'] = """# Especificacion: Facturacion

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O24 (Generar comprobante o factura de reserva)

## 1. Objetivo

Generar comprobantes y facturas asociados a reservas post-estancia con estados, numero de factura unico y dual-write a fact_invoices para analitica.

## 2. Contexto

Al completar el check-out, el sistema o el recepcionista puede generar una factura para la reserva. La factura incluye subtotal, impuestos y total.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Sistema | Genera factura automaticamente al check-out |
| Recepcionista | Genera factura manualmente |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe generar factura con booking_id, subtotal, taxes, total y numero unico | Alta |
| RF-002 | El sistema debe generar numero de factura unico (INV-YYYYMM-XXXX) | Alta |
| RF-003 | El sistema debe permitir listar facturas por booking_id y estado | Alta |
| RF-004 | El sistema debe permitir cancelar factura (solo en estado issued) | Alta |
| RF-005 | El sistema debe hacer dual-write a fact_reservation_invoices | Alta |
| RF-006 | El sistema debe calcular taxes automaticamente | Alta |

## 5. Reglas de negocio

- Factura requiere booking con check-out completado
- Numero unico INV-YYYYMM-XXXX (secuencial por mes)
- Subtotal, taxes y total calculados automaticamente
- Solo se puede cancelar en estado issued
- Dual-write obligatorio a fact_reservation_invoices

## 6. Entradas

```json
{
  "booking_id": "BK-2026-001",
  "tax_percentage": 19
}
```

## 7. Salidas

```json
{
  "success": true,
  "data": {
    "invoice_id": "inv_001",
    "invoice_number": "INV-202606-0001",
    "booking_id": "BK-2026-001",
    "subtotal": 450.00,
    "tax_percentage": 19,
    "taxes": 85.50,
    "total": 535.50,
    "status": "issued",
    "created_at": "2026-06-22T10:30:00Z"
  }
}
```

## 8. Escenarios

### Escenario 1: Generar factura post-checkout
```gherkin
Dado que la reserva BK-2026-001 tiene check-out completado
Cuando el recepcionista genera la factura
Entonces el sistema crea la factura con numero unico
Y escribe en fact_reservation_invoices
```

### Escenario 2: Cancelar factura
```gherkin
Dado que existe una factura en estado issued
Cuando el recepcionista la cancela
Entonces el sistema cambia status a cancelled
```

## 9. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Factura se genera con numero unico |
| CA-002 | Calculo de taxes y total es correcto |
| CA-003 | Solo se puede cancelar factura issued |
| CA-004 | Dual-write a fact_reservation_invoices funciona |

## 10. Dependencias

- Coleccion reservation_invoices
- Coleccion fact_reservation_invoices (dual-write)
- Modulo modules/billing/services/billing.py

## 11. Fuera de alcance

- Facturacion electronica (DFE, SAT, etc.)
- Multiples monedas
- Notas de credito
"""

specs['027-pagos'] = """# Especificacion: Pagos

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O25 (Registrar pago asociado a reserva)

## 1. Objetivo

Registrar pagos simulados asociados a reservas y facturas, con metodos de pago, estados y dual-write a fact_payments para analitica. Incluye reembolsos simulados.

## 2. Contexto

Los pagos en HotelData son simulados (sin integracion bancaria real). El sistema registra pagos contra facturas, permite reembolsos, y actualiza el estado de la factura.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Recepcionista | Registra pago en recepcion |
| Sistema | Asocia pago a factura automaticamente |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir registrar pago con booking_id, amount, method | Alta |
| RF-002 | El sistema debe generar referencia unica de pago (PAY-XXXXXX) | Alta |
| RF-003 | El sistema debe asociar pago a una factura (invoice_id) | Alta |
| RF-004 | El sistema debe actualizar estado de la factura a paid al registrar pago | Alta |
| RF-005 | El sistema debe permitir reembolsar pago | Alta |
| RF-006 | El sistema debe hacer dual-write a fact_reservation_payments | Alta |

## 5. Reglas de negocio

- Pagos simulados (sin integracion bancaria real)
- Metodos: cash, credit_card, bank_transfer (simulados)
- Al registrar pago, factura pasa a paid
- Un reembolso cambia payment.status a refunded, invoice.status a refunded
- No se cumple PCI DSS (proyecto educacional)

## 6. Entradas

```json
{
  "booking_id": "BK-2026-001",
  "invoice_id": "inv_001",
  "amount": 535.50,
  "method": "credit_card"
}
```

## 7. Salidas

```json
{
  "success": true,
  "data": {
    "payment_id": "pay_001",
    "payment_reference": "PAY-A3F2K1",
    "booking_id": "BK-2026-001",
    "invoice_id": "inv_001",
    "amount": 535.50,
    "method": "credit_card",
    "status": "completed",
    "invoice_status": "paid",
    "created_at": "2026-06-22T10:30:00Z"
  }
}
```

## 8. Escenarios

### Escenario 1: Registrar pago exitoso
```gherkin
Dado que existe una factura issued para BK-2026-001
Cuando el recepcionista registra un pago
Entonces el sistema crea el pago con referencia unica
Y actualiza la factura a paid
Y escribe en fact_reservation_payments
```

### Escenario 2: Reembolsar pago
```gherkin
Dado que existe un pago completado para la factura inv_001
Cuando el recepcionista reembolsa el pago
Entonces el sistema cambia el pago a refunded
Y actualiza la factura a refunded
```

## 9. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Pago se registra con referencia unica |
| CA-002 | Factura se actualiza a paid |
| CA-003 | Reembolso cambia ambos estados |
| CA-004 | Dual-write a fact_reservation_payments funciona |

## 10. Dependencias

- Coleccion reservation_payments
- Coleccion fact_reservation_payments (dual-write)
- Coleccion reservation_invoices (actualizacion de estado)
- Modulo modules/billing/services/payments.py

## 11. Fuera de alcance

- Integracion con pasarelas de pago reales (Stripe, MercadoPago, etc.)
- PCI DSS compliance
- Pagos recurrentes
"""

# Write all spec files
written = 0
errors = 0
for folder, content in specs.items():
    filepath = os.path.join(BASE, folder, 'spec.md')
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content.lstrip('\n'))
        written += 1
        print(f'OK: {folder}')
    except Exception as e:
        errors += 1
        print(f'ERROR: {folder}: {e}')

print(f'\nTotal: {written} written, {errors} errors')
