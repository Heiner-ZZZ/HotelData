"""Cura timestamps demo de housekeeping con duraciones realistas.

Los documentos demo de ``housekeeping_tasks`` (started_at/completed_at) y de
``room_status_history`` (pares sucio→limpio) fueron generados con timestamps
casi idénticos (1–9 s), lo que contaminaba los promedios de
``kpi_housekeeping_daily`` (avg_cleaning_minutes, avg_checkout_to_available_minutes).

Este script es **idempotente**: solo reescribe pares cuya duración actual es
menor a un minuto (el mismo umbral de ruido que aplica el ETL), dejando intactos
los datos ya realistas. Acepta ``--dry-run`` para inspeccionar sin escribir.

Uso:
    docker compose --env-file .env -f infra/docker-compose.yml exec -T server \\
        python scripts/curate_housekeeping_demo_times.py --dry-run
    docker compose --env-file .env -f infra/docker-compose.yml exec -T server \\
        python scripts/curate_housekeeping_demo_times.py
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta
from typing import Any

sys.path.insert(0, "/app")

from config.settings import get_settings  # noqa: E402
from pymongo import MongoClient  # noqa: E402
# El umbral de ruido es el mismo que aplica el ETL (extract.py): importarlo
# evita que uno de los dos lados cambie sin el otro y vuelva a contaminar los
# promedios. 1.0 min == 60 s.
from src.etl.mongo_to_clickhouse.extract import MIN_MEASURABLE_MINUTES  # noqa: E402

MIN_MEASURABLE_SECONDS = MIN_MEASURABLE_MINUTES * 60.0
CLEANING_MIN_MINUTES = 20
CLEANING_MAX_MINUTES = 45
ROTATION_MIN_MINUTES = 15
ROTATION_MAX_MINUTES = 60

DIRTY_STATES = {"vacant_dirty", "occupied_dirty", "cleaning_in_progress"}
CLEAN_STATES = {"cleaning_completed", "vacant_clean", "inspected"}


def _parse(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if value is None:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _encode(value: datetime, original: Any) -> Any:
    """Devuelve el timestamp en el mismo tipo que el original (str o datetime)."""
    if isinstance(original, datetime):
        return value
    return value.isoformat()


def _duration_seconds(start: Any, end: Any) -> float | None:
    first = _parse(start)
    second = _parse(end)
    if not first or not second or second < first:
        return None
    return (second - first).total_seconds()


def _cure_tasks(db, dry_run: bool) -> dict[str, int]:
    """Reubica ``started_at`` hacia atrás para que la limpieza dure 20–45 min."""
    fixed = 0
    skipped = 0
    for doc in db.housekeeping_tasks.find(
        {"status": {"$ne": "deleted"}, "started_at": {"$ne": None}, "completed_at": {"$ne": None}}
    ):
        duration = _duration_seconds(doc.get("started_at"), doc.get("completed_at"))
        if duration is None or duration >= MIN_MEASURABLE_SECONDS:
            skipped += 1
            continue
        completed = _parse(doc.get("completed_at"))
        if completed is None:
            skipped += 1
            continue
        minutes = random.randint(CLEANING_MIN_MINUTES, CLEANING_MAX_MINUTES)
        new_started = completed - timedelta(minutes=minutes)
        if dry_run:
            print(
                f"  [dry-run] task {doc.get('_id')} (prop={doc.get('prop_id')}): "
                f"{duration:.1f}s → {minutes} min de limpieza"
            )
        else:
            db.housekeeping_tasks.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "started_at": _encode(new_started, doc.get("started_at")),
                    "metadata.migration_id": "curate_hk_demo_times",
                }},
            )
        fixed += 1
    return {"fixed": fixed, "already_realistic": skipped}


def _cure_history(db, dry_run: bool) -> dict[str, int]:
    """Abre la brecha de cada par sucio→limpio < 1 min a 15–60 min.

    Al desplazar la transición limpia hacia adelante, todas las transiciones
    posteriores de la misma habitación se corren el mismo delta para preservar
    el orden cronológico y las brechas internas del timeline.
    """
    from collections import defaultdict

    timeline: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for doc in db.room_status_history.find(
        {"room_label": {"$ne": None}, "created_at": {"$ne": None}}
    ):
        parsed = _parse(doc.get("created_at"))
        if parsed is None:
            continue
        room_key = str(doc.get("hotel_room_id") or doc.get("room_label") or "")
        try:
            prop_id = int(doc.get("prop_id") or 0)
        except (TypeError, ValueError):
            prop_id = 0
        if room_key:
            timeline[(prop_id, room_key)].append({**doc, "_parsed": parsed})

    fixed_pairs = 0
    rooms_touched = 0
    for (prop_id, room), events in sorted(timeline.items()):
        events.sort(key=lambda item: item["_parsed"])
        shifted = 0
        # Acumula el desplazamiento aplicado a eventos posteriores.
        for index in range(len(events) - 1):
            previous, current = events[index], events[index + 1]
            if previous.get("new_status") not in DIRTY_STATES:
                continue
            if current.get("new_status") not in CLEAN_STATES:
                continue
            duration = (current["_parsed"] - previous["_parsed"]).total_seconds()
            if duration >= MIN_MEASURABLE_SECONDS:
                continue
            extra_seconds = random.randint(ROTATION_MIN_MINUTES, ROTATION_MAX_MINUTES) * 60 - duration
            if dry_run:
                print(
                    f"  [dry-run] room {prop_id}:{room}: "
                    f"{previous.get('new_status')}→{current.get('new_status')} "
                    f"{duration:.1f}s → +{extra_seconds/60:.0f} min de rotación"
                )
            # En dry-run también se muta la copia en memoria: así las duraciones
            # impresas de pares posteriores de la misma habitación reflejan el
            # desplazamiento acumulado que aplicaría el modo real.
            for item in events[index + 1:]:
                item["_parsed"] += timedelta(seconds=extra_seconds)
                if not dry_run:
                    db.room_status_history.update_one(
                        {"_id": item["_id"]},
                        {"$set": {
                            "created_at": _encode(item["_parsed"], item.get("created_at")),
                            "metadata.migration_id": "curate_hk_demo_times",
                        }},
                    )
            fixed_pairs += 1
            shifted += 1
        if shifted:
            rooms_touched += 1
    return {"fixed_pairs": fixed_pairs, "rooms_touched": rooms_touched}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Solo inspecciona, no escribe.")
    args = parser.parse_args()

    settings = get_settings()
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=8000)
    db = client[settings.mongo_database]
    try:
        print(f"Modo: {'DRY-RUN' if args.dry_run else 'APLICAR'}")
        tasks = _cure_tasks(db, dry_run=args.dry_run)
        history = _cure_history(db, dry_run=args.dry_run)
        print(f"housekeeping_tasks: {tasks['fixed']} corregidas, {tasks['already_realistic']} ya realistas")
        print(f"room_status_history: {history['fixed_pairs']} pares corregidos en {history['rooms_touched']} habitaciones")
    finally:
        client.close()


if __name__ == "__main__":
    main()
