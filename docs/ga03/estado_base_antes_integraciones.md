# Estado base antes de integraciones GA03

## Proyecto

HotelData Hub Analytics

## Estado base

TA02/GA03 documentado y protegido como punto de partida antes de integrar nuevas funcionalidades.

## Datos y arquitectura vigente

- MongoDB: `hoteldata_hub`
- Fuente PocketBase actual: `hotel_reservation_events_03`
- Hecho principal: `fact_hotel_reservations`
- Dimensiones activas: 12
- Web actual:
  - `/ta02`
  - `/ta02/crud`
  - `/etl-status`

## Alcance protegido

- No se ejecuta ETL en este punto.
- No se modifican DAGs.
- No se modifica base de datos.
- No se borra evidencia existente.
- No se toca la colección TA02 `hotel_reservation_events__2`.

## Integraciones futuras

Docker y Redis estaban documentados como preparación futura. A partir de la rama `ga03-integraciones` se integrarán progresivamente, manteniendo separado el estado validado actual.

## Rama de trabajo

La rama `ga03-integraciones` será usada para nuevas funcionalidades e integraciones posteriores.
