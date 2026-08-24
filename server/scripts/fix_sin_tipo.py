"""Fix "Sin tipo" — reasigna reservas sin tipo de habitación al tipo base.

Autorizado por el dueño: las reservas de ``booking_orders`` con
``room_type_id`` vacío (hoteles reales, nunca demo/test) se asignan a la
"Habitación Standard" del hotel, y ``strat_plan_monthly`` se recalcula
quirúrgicamente (fusión de las filas vacías en la fila del tipo base).

NO toca ``hotel_policies`` / ``maintenance_tasks`` / ``amenity_stock`` (ahí el
vacío significa "toda la propiedad", no es un error) ni hoteles fuera del
mapeo.

Seguridad: por defecto es DRY-RUN (imprime el plan sin escribir). Con
``--apply`` sí actualiza Mongo y ClickHouse.

Uso:
    python scripts/fix_sin_tipo.py            # dry-run
    python scripts/fix_sin_tipo.py --apply    # escribe
"""

from __future__ import annotations

import sys
from datetime import date
from typing import Any

from config.settings import get_settings
from clickhouse_connect import get_client
from pymongo import MongoClient

# Columnas (KEEP IN SYNC con load.TABLES_DDL["strat_plan_monthly"]).
PLAN_COLUMNS = [
    "month", "prop_id", "hotel_label", "room_type_id", "room_type_label",
    "currency", "bookings", "rooms_sold", "room_nights", "revenue",
    "discount_amount", "adults", "children", "cancelled_rooms",
]
MERGE_COLS = [
    "bookings", "rooms_sold", "room_nights", "revenue",
    "discount_amount", "adults", "children", "cancelled_rooms",
]

# Hoteles reales afectados -> tipo base objetivo.
SIN_TIPO_MAPPING: dict[int, dict[str, str]] = {
    1: {"id": "RT-1-standard", "label": "Habitación Standard"},
    2: {"id": "RT-2-standard", "label": "Habitación Standard"},
}


def merge_sin_tipo(rows: list[dict[str, Any]], mapping: dict[int, dict[str, str]]) -> list[dict[str, Any]]:
    """Fusiona filas de ``strat_plan_monthly`` con ``room_type_id`` vacío hacia
    el tipo base del hotel.

    - Pasada 1: TODAS las filas se conservan (tipos reales y vacíos de hoteles
      fuera del mapeo), indexadas por (mes, prop, room_type_id, currency) — la
      clave completa del sort, porque Deluxe y Doble Premiun comparten mes/prop.
    - Pasada 2: cada fila vacía de un hotel del ``mapping`` se suma a la fila
      del tipo base de su (mes, prop, currency); si no existe, se RENOMBRA al
      tipo base. Preserva el orden de inserción.
    """
    out_by_full: dict[tuple[Any, Any, str, str], dict[str, Any]] = {}
    order: list[tuple[Any, Any, str, str]] = []
    standard_full: dict[tuple[Any, Any, str], tuple[Any, Any, str, str]] = {}

    for r in rows:
        rid = str(r.get("room_type_id") or "").strip()
        pid = r.get("prop_id")
        # Las filas vacías de hoteles del mapeo NO se guardan aquí: la pasada 2
        # decide si se fusionan en el tipo base o se renombran (sin duplicar).
        if not rid and pid in mapping:
            continue
        key = (r["month"], r["prop_id"], rid, r["currency"])
        if key not in out_by_full:
            out_by_full[key] = dict(r)
            order.append(key)
        if pid in mapping and rid == mapping[pid]["id"]:
            standard_full[(r["month"], pid, r["currency"])] = key

    for r in rows:
        rid = str(r.get("room_type_id") or "").strip()
        pid = r.get("prop_id")
        if rid or pid not in mapping:
            continue
        s_key = standard_full.get((r["month"], pid, r["currency"]))
        if s_key is not None:
            target = out_by_full[s_key]
            for col in MERGE_COLS:
                target[col] = target.get(col, 0) + r.get(col, 0)
        else:
            relabel = dict(r)
            relabel["room_type_id"] = mapping[pid]["id"]
            relabel["room_type_label"] = mapping[pid]["label"]
            t_key = (r["month"], pid, relabel["room_type_id"], r["currency"])
            if t_key in out_by_full:
                for col in MERGE_COLS:
                    out_by_full[t_key][col] = out_by_full[t_key].get(col, 0) + relabel.get(col, 0)
            else:
                out_by_full[t_key] = relabel
                order.append(t_key)
                standard_full[(r["month"], pid, r["currency"])] = t_key
    return [out_by_full[k] for k in order]


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

    # 1) Mongo — reservas sin tipo (hoteles del mapeo).
    mongo_ids: list[str] = []
    for pid, t in SIN_TIPO_MAPPING.items():
        cur = db.booking_orders.find(
            {"prop_id": pid, "room_type_id": {"$in": ["", None]}},
            {"booking_id": 1},
        )
        for doc in cur:
            mongo_ids.append(f"{pid}:{doc.get('booking_id')}")

    # 2) ClickHouse — filas actuales de strat_plan_monthly.
    result = ch.query(f"SELECT {', '.join(PLAN_COLUMNS)} FROM strat_plan_monthly FINAL ORDER BY prop_id, month, room_type_id")
    names = [n.strip() for n in PLAN_COLUMNS]
    rows = [dict(zip(names, row)) for row in result.result_rows]
    merged = merge_sin_tipo(rows, SIN_TIPO_MAPPING)

    print(f"[DRY-RUN]" if not apply else "[APPLY]")
    print(f"Mongo: {len(mongo_ids)} reserva(s) sin tipo a reasignar:")
    for bid in mongo_ids:
        print(f"   {bid}")
    print(f"ClickHouse strat_plan_monthly: {len(rows)} -> {len(merged)} filas")
    for r in merged:
        flag = "  <-- sin tipo" if not str(r.get("room_type_id") or "").strip() else ""
        print(
            f"   {r['month']} prop={r['prop_id']:<3} rt={r.get('room_type_id') or '(vacio)':<28} "
            f"label={r.get('room_type_label') or '':<22} bk={r['bookings']} rev={r['revenue']}{flag}"
        )

    if not apply:
        mc.close()
        ch.close()
        print("\nDry-run: nada escrito. Usa --apply para aplicar.")
        return 0

    # 3) Aplicar Mongo.
    mongo_updated = 0
    for pid, t in SIN_TIPO_MAPPING.items():
        res = db.booking_orders.update_many(
            {"prop_id": pid, "room_type_id": {"$in": ["", None]}},
            {"$set": {"room_type_id": t["id"]}},
        )
        mongo_updated += res.modified_count

    # 4) Aplicar ClickHouse: reemplazo completo de la tabla con las filas fusionadas.
    ch.command(f"TRUNCATE TABLE strat_plan_monthly")
    if merged:
        data = [
            [r[c] for c in PLAN_COLUMNS]
            for r in merged
        ]
        ch.insert("strat_plan_monthly", data, column_names=PLAN_COLUMNS)

    # 5) Verificar.
    after = ch.query(
        f"SELECT {', '.join(PLAN_COLUMNS)} FROM strat_plan_monthly FINAL "
        f"WHERE prop_id IN ({','.join(str(p) for p in SIN_TIPO_MAPPING)}) "
        f"AND room_type_id = ''"
    )
    remaining = len(after.result_rows)
    print(f"\nMongo actualizadas: {mongo_updated}")
    print(f"ClickHouse filas con room_type_id vacio (props {sorted(SIN_TIPO_MAPPING)}): {remaining}")
    if remaining:
        print("  !! quedan filas vacías — revisar.")
    else:
        print("  OK: no quedan 'Sin tipo' para los hoteles afectados.")

    mc.close()
    ch.close()
    return 0 if remaining == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
