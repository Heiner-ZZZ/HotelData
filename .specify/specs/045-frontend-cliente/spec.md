# Especificacion: Frontend - Experiencia Cliente

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O02 al CU-O07 (Busqueda, filtros, detalle, reserva, mis reservas, cancelacion)

## 1. Objetivo

UI de cliente: busqueda de hoteles, filtros, comparacion, detalle, reserva y cancelacion.

## 2. Componentes

| Componente | Ruta | CU asociado |
|------------|------|-------------|
| HotelSearchPage | /hotels/search | CU-O02 |
| HotelDetailPage | /hotels/:id | CU-O04 |
| ComparePage | /hotels/compare | CU-O03 |
| BookingForm | /reservations/new | CU-O05 |
| MyReservationsPage | /reservations | CU-O06 |
| CancelDialog | - | CU-O07 |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | HotelSearchPage con filtros (precio, rating, amenities, destino) | Alta |
| RF-002 | HotelDetailPage con galeria, tarifas, resenas | Alta |
| RF-003 | ComparePage con tabla lado a lado de hasta 3 hoteles | Alta |
| RF-004 | BookingForm con seleccion de tipo habitacion | Alta |
| RF-005 | MyReservationsPage con lista de reservas y estados | Alta |
| RF-006 | CancelDialog con confirmacion | Alta |

## 4. Dependencias

- frontend/src/app/features/booking/
