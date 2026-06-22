# Especificación: Búsqueda Operacional de Hoteles con Disponibilidad

**Versión**: 1.1 | **Estado**: Implementado

**Casos de uso TAF06**: CU-O02 (Buscar hoteles)

## 1. Objetivo

Permitir que un cliente busque hoteles disponibles por destino, fechas, número de huéspedes y otros criterios, visualizando resultados con tarifas en tiempo real, disponibilidad de inventario y datos relevantes de cada propiedad.

## 2. Contexto

El cliente accede a la plataforma para encontrar alojamiento. El sistema verifica disponibilidad real consultando `room_inventory_calendar` (habitaciones disponibles por fecha) y `hotel_rate_calendar` (tarifas por fecha y plan). Solo hoteles con inventario suficiente y tarifa configurada aparecen en resultados.

## 3. Actores

- Cliente / Viajero (público, no requiere autenticación)

## 4. Requisitos funcionales

| ID | Requisito |
|----|-----------|
| RF-001 | El sistema debe permitir buscar hoteles por nombre de destino o ciudad |
| RF-002 | El sistema debe filtrar por fechas de check_in y check_out |
| RF-003 | El sistema debe permitir especificar adultos, niños y habitaciones |
| RF-004 | El sistema debe mostrar resultados con nombre, precio mínimo por noche, rating, imagen |
| RF-005 | El sistema debe exponer GET /api/hotels/availability con parámetros de búsqueda |
| RF-006 | El sistema debe verificar disponibilidad real en room_inventory_calendar para todas las noches |
| RF-007 | El sistema debe obtener tarifa mínima desde hotel_rate_calendar |
| RF-008 | El sistema debe mostrar costo total estimado (tarifa mínima × noches) |
| RF-009 | El sistema debe incluir tipo de habitación disponible que cumple con capacidad de huéspedes |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Los resultados de búsqueda deben responder en menos de 2 segundos |
| RNF-002 | Las consultas a room_inventory_calendar usan índices compuestos (prop_id, room_type_id, date) |
| RNF-003 | Endpoint público (no requiere autenticación) |

## 6. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-001 | Solo hoteles con disponibilidad en TODAS las noches del rango solicitado aparecen |
| RN-002 | El precio mostrado es la tarifa nocturna mínima entre todos los planes tarifarios activos |
| RN-003 | Los tipos de habitación deben cumplir con la capacidad de adultos y niños solicitada |
| RN-004 | Resultados ordenados por tarifa mínima ascendente (más económico primero) |

## 7. Entradas

| Dato | Tipo | Endpoint |
|------|------|----------|
| destination | string | GET /api/hotels/availability?destination=Madrid |
| check_in | string (YYYY-MM-DD) | GET /api/hotels/availability?check_in=2026-07-15 |
| check_out | string (YYYY-MM-DD) | GET /api/hotels/availability?check_out=2026-07-20 |
| adults | int (default=1) | GET /api/hotels/availability?adults=2 |
| children | int (default=0) | GET /api/hotels/availability?children=1 |
| rooms | int (default=1) | GET /api/hotels/availability?rooms=1 |
| page | int (default=1) | GET /api/hotels/availability?page=1 |

## 8. Salidas

| Escenario | Respuesta |
|-----------|-----------|
| Búsqueda con resultados | 200 + lista de hoteles con precio, rating, imagen, tipo habitación |
| Sin resultados | 200 + lista vacía (items: []) |
| Sin fechas | 200 + todos los hoteles del destino (sin filtro disponibilidad) |

### Formato de resultado (item):
```json
{
  "prop_id": 12345,
  "hotel_name": "Hotel Ejemplo",
  "display_name": "Hotel Ejemplo Madrid",
  "prop_starrating": 4.0,
  "prop_review_score": 8.5,
  "image_url": "/static/hotels/12345/main.jpg",
  "matched_room_type": {
    "room_type_id": "RT-12345-estandar",
    "name": "Habitación Estándar",
    "max_adults": 2,
    "max_children": 1,
    "base_capacity": 2
  },
  "min_nightly_rate": 89.50,
  "min_nightly_rate_label": "$89.50",
  "total_estimated": 447.50,
  "total_estimated_label": "$447.50",
  "available_room_types_count": 3
}
```

## 9. Escenarios

### Escenario 1: Búsqueda con fechas y destino
```gherkin
Dado que el cliente ingresa "Madrid" como destino y fechas 15-20 julio
Y solicita 2 adultos, 0 niños, 1 habitación
Cuando consulta GET /api/hotels/availability
Entonces el sistema busca hoteles en Madrid con datos de dim_hotels
Y verifica disponibilidad en room_inventory_calendar para todas las noches
Y obtiene tarifas desde hotel_rate_calendar
Y devuelve solo hoteles con disponibilidad completa y tarifa configurada
```

### Escenario 2: Sin resultados
```gherkin
Dado que no hay hoteles disponibles para los criterios solicitados
Cuando consulta GET /api/hotels/availability
Entonces el sistema devuelve 200 con lista vacía
```

## 10. Criterios de aceptación

| ID | Criterio |
|----|----------|
| CA-001 | Búsqueda por destino + fechas devuelve hoteles con disponibilidad real |
| CA-002 | Hoteles sin inventario suficiente en todas las noches son excluidos |
| CA-003 | Hoteles sin tarifa configurada son excluidos |
| CA-004 | Resultados incluyen precio mínimo por noche y total estimado |
| CA-005 | Resultados incluyen tipo de habitación que cumple capacidad de huéspedes |
| CA-006 | Resultados ordenados por precio ascendente |

## 11. Restricciones

- Endpoint público: `/api/hotels/availability` (no requiere auth, en PUBLIC_PREFIXES)
- Fechas en formato ISO 8601 (YYYY-MM-DD)
- La disponibilidad se verifica contra `room_inventory_calendar.available_rooms >= rooms_solicitados`
- La tarifa se obtiene como mínimo de `hotel_rate_calendar.rate_amount` para todas las noches

## 12. Dependencias

- `server/src/app/modules/hotels/service/availability.py` — Lógica de búsqueda operacional
- `server/src/app/modules/hotels/service/lookups.py` — Resolución de destinos
- `server/src/app/modules/hotels/service/_helpers.py` — Formateo y utilidades
- `room_inventory_calendar` — Disponibilidad de habitaciones por fecha
- `hotel_rate_calendar` — Tarifas por fecha y plan
- `room_types` — Capacidad de habitaciones (adultos, niños)
- `dim_hotels` — Datos maestros de hoteles
- `hotel_images` — Imágenes de propiedad

## 13. Fuera de alcance

- Búsqueda por coordenadas geográficas (mapa)
- Búsqueda por texto libre en amenities
- Reserva directa desde resultados (CU-O05)
- Comparación simultánea de hoteles (CU-O03)
