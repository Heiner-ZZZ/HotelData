# Especificacion: Tipos de Habitacion

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O14 (Gestionar tipos de habitacion y habitaciones fisicas), CU-T04 (Validar integridad de datos de habitaciones)

## 1. Objetivo

Crear y gestionar tipos de habitacion y habitaciones fisicas por propiedad, permitiendo definir nombre, capacidad maxima, tarifa base, amenities y cantidad de habitaciones de ese tipo.

## 2. Contexto

Cada propiedad hotelera tiene uno o mas tipos de habitacion (ej. Simple, Doble, Suite). Cada tipo tiene una capacidad maxima de huespedes, una tarifa base (por noche), amenidades incluidas y un numero de habitaciones fisicas de ese tipo.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Hotel partner | Crea y gestiona tipos de habitacion para su propiedad |

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
Cuando envia POST /api/management/properties/HOTEL001/room-types
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
