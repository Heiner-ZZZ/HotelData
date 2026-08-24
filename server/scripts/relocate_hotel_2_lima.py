"""Reubica el hotel 2 (Resort Cancún Playa) a Lima-Perú — académico.

Motivo (aprobado por el dueño): demostrar el funcionamiento del posicionamiento
competitivo IE-H02. Con prop 2 en una ciudad cercana a Lima y coordenadas
dentro del ``RADIO_KM`` (5 km) de prop 1 (Hotel Lima Centro), ambos se vuelven
competidores reales por Haversine y la banda de precio / percentil / mapa se
pueblan. Actualiza ``dim_hotels`` (fuente) y ``strat_hotel_monthly`` (reporte),
y registra "Lima" en ``geo_catalog`` (type=city) para que el ETL resuelva la
ciudad en futuras corridas (mismo patrón que Cancún).

Seguridad: dry-run por defecto; ``--apply`` escribe.

Uso:
    python scripts/relocate_hotel_2_lima.py            # dry-run
    python scripts/relocate_hotel_2_lima.py --apply    # escribe
"""

from __future__ import annotations

import sys
from typing import Any

from config.settings import get_settings
from clickhouse_connect import get_client
from pymongo import MongoClient

# KEEP IN SYNC con load.TABLES_DDL["strat_hotel_monthly"].
HOTEL_COLUMNS = [
    "month", "prop_id", "hotel_label", "currency", "bookings", "rooms_sold",
    "room_nights", "revenue", "discount_amount", "adults", "children",
    "cancelled_rooms", "total_rooms", "city", "city_lat", "city_lng",
]

# Plaza San Martín, Lima Centro — ~1 km del Hotel Lima Centro (prop 1), dentro
# del RADIO_KM competitivo (5 km). Perú = visitor_location_country_id 219;
# Lima = srch_destination_id 89 (dim_destinations).
RELOCATE: dict[str, Any] = {
    "prop_id": 2,
    "city": "Lima",
    "latitude": -12.0509,
    "longitude": -77.0348,
    "country_id": 219,
    "country_label": "Perú",
    "destination_id": 89,
}


def main() -> int:
    apply = "--apply" in sys.argv
    settings = get_settings()
    mc = MongoClient(settings.mongo_uri)
    db = mc[settings.mongo_database]
    ch = get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )

    print("[DRY-RUN]" if not apply else "[APPLY]")
    print(f"Hotel 2 -> {RELOCATE['city']} ({RELOCATE['latitude']}, {RELOCATE['longitude']}), "
          f"país {RELOCATE['country_id']} ({RELOCATE['country_label']}), destino {RELOCATE['destination_id']}")

    # ClickHouse: reubicar las filas de prop 2 en strat_hotel_monthly.
    result = ch.query(
        f"SELECT {', '.join(HOTEL_COLUMNS)} FROM strat_hotel_monthly FINAL ORDER BY prop_id, month"
    )
    rows = [dict(zip(HOTEL_COLUMNS, row)) for row in result.result_rows]
    changed = 0
    for r in rows:
        if r["prop_id"] == RELOCATE["prop_id"]:
            r["city"] = RELOCATE["city"]
            r["city_lat"] = RELOCATE["latitude"]
            r["city_lng"] = RELOCATE["longitude"]
            changed += 1
    print(f"ClickHouse strat_hotel_monthly: {changed} fila(s) de prop 2 reubicada(s)")

    if not apply:
        mc.close()
        ch.close()
        print("\nDry-run: nada escrito. Usa --apply para aplicar.")
        return 0

    # 1) dim_hotels (fuente de verdad de la ubicación del hotel).
    db.dim_hotels.update_one(
        {"prop_id": RELOCATE["prop_id"]},
        {"$set": {
            "city": RELOCATE["city"],
            "latitude": RELOCATE["latitude"],
            "longitude": RELOCATE["longitude"],
            "prop_country_id": RELOCATE["country_id"],
            "display_country_label": RELOCATE["country_label"],
            "srch_destination_id": RELOCATE["destination_id"],
        }},
    )
    # 2) geo_catalog: entrada de ciudad Lima (idempotente, patrón de Cancún).
    db.geo_catalog.update_one(
        {"type": "city", "name": RELOCATE["city"]},
        {"$set": {"type": "city", "name": RELOCATE["city"],
                  "latitude": RELOCATE["latitude"], "longitude": RELOCATE["longitude"]}},
        upsert=True,
    )
    # 3) ClickHouse: reemplazo con las filas reubicadas.
    ch.command("TRUNCATE TABLE strat_hotel_monthly")
    if rows:
        data = [[r[c] for c in HOTEL_COLUMNS] for r in rows]
        ch.insert("strat_hotel_monthly", data, column_names=HOTEL_COLUMNS)

    # 4) Verificar.
    h = db.dim_hotels.find_one({"prop_id": RELOCATE["prop_id"]},
                               {"city": 1, "latitude": 1, "longitude": 1,
                                "prop_country_id": 1, "display_country_label": 1})
    print(f"\ndim_hotels prop 2 -> {h}")
    geo = db.geo_catalog.find_one({"type": "city", "name": "Lima"}, {"latitude": 1, "longitude": 1})
    print(f"geo_catalog Lima -> {geo}")
    ch_rows = ch.query(
        "SELECT DISTINCT city, city_lat, city_lng FROM strat_hotel_monthly FINAL WHERE prop_id = 2"
    ).result_rows
    print(f"strat_hotel_monthly prop 2 -> {ch_rows}")

    mc.close()
    ch.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
