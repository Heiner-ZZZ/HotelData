"""Fix de coordenadas de strat_hotel_monthly (IE-H02, mapa competitivo).

prop 1 (Hotel Lima Centro) quedó con city_lat/city_lng = None porque el ETL
corrió antes de que dim_hotels tuviera coordenadas. Este script recalcula las
coordenadas con la MISMA semántica del ETL (_enrich_strat_hotel_geo): coord
real por hotel (dim_hotels) si existe; si no, centro de ciudad (geo_catalog
type=city por nombre); si tampoco, None honesto. Reemplaza strat_hotel_monthly
con las filas corregidas (solo cambian las que les faltaba coordenada).

Seguridad: dry-run por defecto; ``--apply`` escribe.

Uso:
    python scripts/fix_strat_hotel_coords.py            # dry-run
    python scripts/fix_strat_hotel_coords.py --apply    # escribe
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


def resolve_strat_coords(
    rows: list[dict[str, Any]],
    dim_hotels: dict[Any, dict[str, Any]],
    geo_by_city: dict[str, tuple[float, float]],
) -> list[dict[str, Any]]:
    """Asigna ``city``/``city_lat``/``city_lng`` a filas de strat_hotel_monthly.

    Misma semántica que ``_enrich_strat_hotel_geo``: la coordenada real por
    hotel (dim_hotels.latitude/longitude) gana; si el hotel no la tiene, se
    usa el centro de ciudad (geo_catalog por nombre en minúsculas); si tampoco,
    queda ``None`` — honesto, nunca inventada. No pisa coordenadas ya
    presentes en la fila.
    """
    out: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        pid = r.get("prop_id")
        meta = dim_hotels.get(pid, {}) if dim_hotels else {}
        city = r.get("city") or meta.get("city") or ""
        if meta.get("city"):
            city = meta["city"]
        r["city"] = city
        if r.get("city_lat") is None or r.get("city_lng") is None:
            lat = meta.get("latitude")
            lng = meta.get("longitude")
            if lat is None or lng is None:
                point = geo_by_city.get(city.strip().lower())
                if point:
                    lat, lng = point
            if r.get("city_lat") is None:
                r["city_lat"] = lat
            if r.get("city_lng") is None:
                r["city_lng"] = lng
        out.append(r)
    return out


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

    result = ch.query(
        f"SELECT {', '.join(HOTEL_COLUMNS)} FROM strat_hotel_monthly FINAL ORDER BY prop_id, month"
    )
    rows = [dict(zip(HOTEL_COLUMNS, row)) for row in result.result_rows]

    dim_hotels: dict[Any, dict[str, Any]] = {}
    for doc in db.dim_hotels.find(
        {}, {"prop_id": 1, "city": 1, "latitude": 1, "longitude": 1}
    ):
        pid = doc.get("prop_id")
        if pid is None:
            continue
        dim_hotels[pid] = {
            "city": str(doc.get("city") or "").strip(),
            "latitude": doc.get("latitude"),
            "longitude": doc.get("longitude"),
        }
    geo_by_city: dict[str, tuple[float, float]] = {}
    for doc in db.geo_catalog.find(
        {"type": "city", "latitude": {"$ne": None}, "longitude": {"$ne": None}},
        {"name": 1, "latitude": 1, "longitude": 1},
    ):
        name = str(doc.get("name") or "").strip().lower()
        if name and doc.get("latitude") is not None and doc.get("longitude") is not None:
            geo_by_city[name] = (float(doc["latitude"]), float(doc["longitude"]))

    merged = resolve_strat_coords(rows, dim_hotels, geo_by_city)

    print("[DRY-RUN]" if not apply else "[APPLY]")
    changed = 0
    for before, after in zip(rows, merged):
        if (before.get("city_lat"), before.get("city_lng")) != (after.get("city_lat"), after.get("city_lng")):
            changed += 1
        print(
            f"   prop={after['prop_id']:<3} city={after.get('city') or '':<10} "
            f"lat={after.get('city_lat')} lng={after.get('city_lng')}"
        )
    print(f"filas con coordenada cambiada: {changed} de {len(rows)}")

    if not apply:
        mc.close()
        ch.close()
        print("\nDry-run: nada escrito. Usa --apply para aplicar.")
        return 0

    ch.command("TRUNCATE TABLE strat_hotel_monthly")
    if merged:
        data = [[r[c] for c in HOTEL_COLUMNS] for r in merged]
        ch.insert("strat_hotel_monthly", data, column_names=HOTEL_COLUMNS)

    after = ch.query(
        "SELECT count() FROM strat_hotel_monthly FINAL "
        "WHERE prop_id IN (1, 2) AND (city_lat IS NULL OR city_lng IS NULL)"
    )
    missing = after.result_rows[0][0]
    print(f"\nClickHouse filas prop 1,2 sin coordenada tras fix: {missing}")
    if missing:
        print("  !! quedan filas sin coordenada — revisar.")
    else:
        print("  OK: props 1 y 2 con coordenadas en strat_hotel_monthly.")

    mc.close()
    ch.close()
    return 0 if missing == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
