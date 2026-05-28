# TA 02 - Modelo dimensional

## Hecho

Coleccion: `fact_hotel_reservations`

| Campo | Rol |
| --- | --- |
| `srch_id` | Identificador de busqueda |
| `date_time` | Fecha/hora original del evento |
| `date_key` | Llave dimensional de fecha |
| `prop_id` | Llave de hotel |
| `srch_destination_id` | Llave de destino |
| `visitor_location_country_id` | Llave de pais del visitante |
| `promotion_flag` | Llave de promocion |
| `reserva_bool` | Estado de reserva |
| `price_usd` | Precio observado |
| `reservas_brutas_usd` | Monto bruto reservado |
| `srch_length_of_stay` | Noches solicitadas |
| `srch_booking_window` | Dias de anticipacion |
| `srch_adults_count` | Adultos |
| `srch_children_count` | Ninos |
| `srch_room_count` | Habitaciones |
| `loaded_at` | Fecha/hora de carga |
| `execution_id` | Ejecucion ETL |

## Dimensiones

| Dimension | Llave | Proposito |
| --- | --- | --- |
| `dim_hotels` | `prop_id` | Describir hoteles |
| `dim_destinations` | `srch_destination_id` | Agrupar destinos buscados |
| `dim_visitor_countries` | `visitor_location_country_id` | Analizar origen de visitantes |
| `dim_dates` | `date_key` | Analisis temporal |
| `dim_promotions` | `promotion_flag` | Separar reservas con/sin promocion |
| `dim_reservation_status` | `reserva_bool` | Conversion de busqueda a reserva |
| `dim_stay_length_category` | `stay_length_category_id` | Clasificar estancias cortas, medias y largas |
| `dim_booking_window_category` | `booking_window_category_id` | Clasificar anticipacion |
| `dim_price_category` | `price_category_id` | Clasificar precio |
| `dim_occupancy_profile` | `occupancy_profile_id` | Describir adultos, ninos y habitaciones |

## Reglas de transformacion

- `date_key` se deriva de `date_time` con formato `YYYYMMDDHH`.
- `reserva_bool` usa `reserva_bool` si existe; si no, usa `booking_bool`; si no, toma `0`.
- `reservas_brutas_usd` usa `gross_bookings_usd` si existe; si no, usa `price_usd` solo cuando `reserva_bool = 1`.
- Las categorias se derivan desde precio, noches y anticipacion.
- Los registros sin llaves obligatorias se envian a `rejected_records`.
