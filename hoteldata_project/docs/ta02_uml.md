# TA 02 - UML, componentes y despliegue

## UML funcional

```mermaid
classDiagram
  class FactHotelReservation {
    srch_id
    date_key
    prop_id
    srch_destination_id
    visitor_location_country_id
    promotion_flag
    reserva_bool
    price_usd
    reservas_brutas_usd
    execution_id
  }
  class DimHotel { prop_id hotel_name hotel_rating }
  class DimDestination { srch_destination_id destination_name }
  class DimVisitorCountry { visitor_location_country_id country_name }
  class DimDate { date_key year month day hour }
  class DimPromotion { promotion_flag promotion_label }
  class DimReservationStatus { reserva_bool reservation_status }
  FactHotelReservation --> DimHotel
  FactHotelReservation --> DimDestination
  FactHotelReservation --> DimVisitorCountry
  FactHotelReservation --> DimDate
  FactHotelReservation --> DimPromotion
  FactHotelReservation --> DimReservationStatus
```

## Componentes

```mermaid
flowchart TB
  subgraph Fuente
    PB[PocketBase]
  end
  subgraph Orquestacion
    AF[Airflow DAG TA 02]
  end
  subgraph Python_ETL
    EX[pocketbase.py]
    PQ[parquet_io.py]
    TR[reservations.py]
    LD[load_reservations.py]
  end
  subgraph Datos
    MG[(MongoDB hoteldata_hub)]
  end
  subgraph Web
    API[FastAPI CRUD y dashboard]
  end
  AF --> EX --> PQ --> TR --> LD --> MG --> API
  PB --> EX
```

## Despliegue

```mermaid
flowchart LR
  U[Usuario empresarial] --> WEB[FastAPI / Uvicorn]
  WEB --> MONGO[(MongoDB)]
  AIR[Airflow Scheduler/Webserver] --> ETL[Python ETL]
  ETL --> PB[PocketBase]
  ETL --> FS[Staging JSONL y Parquet]
  ETL --> MONGO
```

## Restricciones

- Airflow no importa `src.app`.
- La web no ejecuta ETL principal.
- MongoDB es la persistencia final.
- Parquet es el formato intermedio obligatorio.
