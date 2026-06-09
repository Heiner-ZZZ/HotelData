import pandas as pd
from pathlib import Path

INPUT_CSV = Path(r"C:\HotelData\hoteldata_project\data\raw\hotels.csv")
OUTPUT_CSV = Path(r"C:\HotelData\hoteldata_project\data\processed\hotels_fact_reduced.csv")

OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

BASE_COLUMNS = [
    "srch_id",
    "date_time",
    "prop_id",
    "srch_destination_id",
    "visitor_location_country_id",
    "price_usd",
    "promotion_flag",
    "srch_length_of_stay",
    "srch_booking_window",
    "srch_adults_count",
    "srch_children_count",
    "srch_room_count",
]

BOOKING_CANDIDATES = [
    "booking_bool",
    "reserva_bool",
    "is_booking",
]

GROSS_BOOKING_CANDIDATES = [
    "gross_bookings_usd",
    "gross_booking_usd",
    "reservas_brutas_USD",
    "reservas_brutas_usd",
]

CHUNK_SIZE = 100_000
MAX_ROWS = 100_000


def find_first_existing(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def main():
    print("Leyendo encabezado del CSV...")
    header = pd.read_csv(INPUT_CSV, nrows=0)
    available_columns = list(header.columns)

    missing_base = [col for col in BASE_COLUMNS if col not in available_columns]

    if missing_base:
        raise ValueError(f"Faltan columnas obligatorias: {missing_base}")

    booking_col = find_first_existing(available_columns, BOOKING_CANDIDATES)
    gross_col = find_first_existing(available_columns, GROSS_BOOKING_CANDIDATES)

    if booking_col is None:
        print("Advertencia: no existe booking_bool/reserva_bool. Se creara reserva_bool = 0.")
    else:
        print(f"Columna usada para reserva_bool: {booking_col}")

    if gross_col is None:
        print("Advertencia: no existe gross_bookings_usd. Se calculara reservas_brutas_USD con price_usd si reserva_bool = 1.")
    else:
        print(f"Columna usada para reservas_brutas_USD: {gross_col}")

    usecols = BASE_COLUMNS.copy()

    if booking_col and booking_col not in usecols:
        usecols.append(booking_col)

    if gross_col and gross_col not in usecols:
        usecols.append(gross_col)

    first_write = True
    total_rows = 0

    print("Procesando CSV por bloques...")

    for chunk in pd.read_csv(INPUT_CSV, usecols=usecols, chunksize=CHUNK_SIZE):
        if MAX_ROWS is not None:
            remaining = MAX_ROWS - total_rows
            if remaining <= 0:
                break
            chunk = chunk.head(remaining)

        if booking_col:
            chunk["reserva_bool"] = chunk[booking_col].fillna(0).astype(int)
        else:
            chunk["reserva_bool"] = 0

        if gross_col:
            chunk["reservas_brutas_USD"] = chunk[gross_col].fillna(0)
        else:
            chunk["reservas_brutas_USD"] = chunk["price_usd"].fillna(0) * chunk["reserva_bool"]

        final_columns = [
            "srch_id",
            "date_time",
            "prop_id",
            "srch_destination_id",
            "visitor_location_country_id",
            "price_usd",
            "reserva_bool",
            "reservas_brutas_USD",
            "promotion_flag",
            "srch_length_of_stay",
            "srch_booking_window",
            "srch_adults_count",
            "srch_children_count",
            "srch_room_count",
        ]

        reduced = chunk[final_columns]

        reduced.to_csv(
            OUTPUT_CSV,
            mode="w" if first_write else "a",
            header=first_write,
            index=False,
            encoding="utf-8",
        )

        first_write = False
        total_rows += len(reduced)

        print(f"Filas procesadas: {total_rows}")

        if MAX_ROWS is not None and total_rows >= MAX_ROWS:
            break

    print("Archivo reducido generado correctamente:")
    print(OUTPUT_CSV)
    print(f"Total de filas guardadas: {total_rows}")


if __name__ == "__main__":
    main()
