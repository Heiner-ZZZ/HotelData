# Diccionario completo de colecciones (TA02/GA03)

Fecha de verificacion: 2026-05-26  
Base revisada: `hoteldata_hub` (MongoDB local)

## Alcance

Este documento incluye:

- Colecciones de dimensiones (`dim_*`)
- Colecciones de hechos (`fact_*`)
- Colecciones adicionales que no empiezan con `dim` ni con `fact`

## 1) Dimensiones (`dim_*`)

| Coleccion (tecnico) | Traduccion al espanol | Que hace |
| --- | --- | --- |
| `dim_hotels` | Dimension de hoteles | Describe cada hotel (`prop_id`) con atributos de negocio para analisis por hotel. |
| `dim_destinations` | Dimension de destinos | Catalogo de destinos de busqueda (`srch_destination_id`) para analisis geografico de demanda. |
| `dim_visitor_countries` | Dimension de paises de visitantes | Mapea el pais de origen del visitante para segmentacion por mercado emisor. |
| `dim_sites` | Dimension de sitios/canales | Identifica el sitio/canal (`site_id`) de origen de la busqueda o evento. |
| `dim_dates` | Dimension de fechas | Descompone el tiempo (`date_key`) en año, mes, dia, hora y soporta estacionalidad. |
| `dim_promotions` | Dimension de promociones | Clasifica eventos/reservas con o sin promocion. |
| `dim_click_status` | Dimension de estado de click | Clasifica si hubo click (`click_bool`) en la interaccion. |
| `dim_reservation_status` | Dimension de estado de reserva | Clasifica si la busqueda termino en reserva (`reserva_bool`). |
| `dim_occupancy_profile` | Dimension de perfil de ocupacion | Define perfiles por adultos, niños y habitaciones (`occupancy_profile_id`). |
| `dim_stay_length_category` | Dimension de categoria de estancia | Segmenta por duracion de estancia (corta, media, larga). |
| `dim_booking_window_category` | Dimension de categoria de anticipacion | Segmenta por anticipacion de compra (dias antes de reservar). |
| `dim_price_category` | Dimension de categoria de precio | Segmenta por rangos de precio (bajo, medio, alto, premium). |
| `dim_countries` | Dimension de paises (legada) | Coleccion historica/no usada actualmente en el flujo principal. |
| `dim_date` | Dimension de fecha (legada) | Coleccion historica/no usada; fue reemplazada por `dim_dates`. |

## 2) Hechos (`fact_*`)

| Coleccion (tecnico) | Traduccion al espanol | Que hace |
| --- | --- | --- |
| `fact_hotel_events` | Hechos de eventos hoteleros | Tabla de hechos de eventos de busqueda/interaccion (grano por evento), usada para analitica operacional. |
| `fact_hotel_reservations` | Hechos de reservas hoteleras | Tabla de hechos dimensional de reservas (grano por reserva/evento de reserva) para cruce con dimensiones. |

## 3) Otras colecciones (no `dim_*` ni `fact_*`)

| Coleccion (tecnico) | Traduccion al espanol | Que hace |
| --- | --- | --- |
| `hotels` | Hoteles (maestra operativa) | Entidad principal de hotel en modelo de colecciones de negocio (no estrella). |
| `locations` | Ubicaciones | Direccion, ciudad y datos geograficos por hotel. |
| `contacts` | Contactos | Telefonos/fax de hotel. |
| `websites` | Sitios web | URL del hotel. |
| `facilities` | Instalaciones/servicios | Facilidades del hotel (wifi, piscina, etc.) en formato desnormalizado por item. |
| `attractions` | Atracciones cercanas | Puntos de interes por hotel. |
| `hotel_quality` | Calidad de datos de hotel | Puntaje y nivel de calidad por hotel, con lista de issues. |
| `dataset_container` | Contenedor de dataset | Metadatos del dataset procesado (hash, total de filas, fuente). |
| `rejected_records` | Registros rechazados | Filas descartadas por reglas de calidad/llaves durante ETL. |
| `etl_executions` | Ejecuciones ETL | Bitacora de corridas ETL (estado, metricas, tiempos). |
| `data_quality_reports` | Reportes de calidad de datos | Evidencia consolidada de calidad por corrida. |
| `system_catalogs` | Catalogos del sistema | Maestras de apoyo/configuracion para el sistema. |
| `search_logs` | Bitacora de busquedas | Log de consultas/busquedas realizadas desde la app o servicios. |

## 4) Conteos observados en Mongo

Conteo de documentos por coleccion (2026-05-26):

- `attractions`: 2
- `contacts`: 1
- `data_quality_reports`: 11
- `dataset_container`: 0
- `dim_booking_window_category`: 4
- `dim_click_status`: 2
- `dim_countries`: 0
- `dim_date`: 0
- `dim_dates`: 6018
- `dim_destinations`: 13808
- `dim_hotels`: 119831
- `dim_occupancy_profile`: 204
- `dim_price_category`: 4
- `dim_promotions`: 4
- `dim_reservation_status`: 4
- `dim_sites`: 32
- `dim_stay_length_category`: 3
- `dim_visitor_countries`: 199
- `etl_executions`: 10
- `facilities`: 3
- `fact_hotel_events`: 100000
- `fact_hotel_reservations`: 0 (por andar con el ETL)
- `hotel_quality`: 1
- `hotels`: 1
- `locations`: 1
- `rejected_records`: 0
- `search_logs`: 4
- `system_catalogs`: 8
- `websites`: 1

## 5) Lectura rapida

- El modelo dimensional activo se apoya en `fact_hotel_events` + dimensiones `dim_*`.
- `fact_hotel_reservations` esta creada pero actualmente vacia.
- Existen colecciones legadas (`dim_date`, `dim_countries`) sin datos.
- Coexisten dos capas: modelo dimensional (`fact/dim`) y modelo documental de negocio (`hotels`, `locations`, `contacts`, etc.).
