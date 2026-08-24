"""Completa/corrige los hoteles destacados 1–5 (dim_hotels).

Los props 1–5 (Hotel Lima Centro, Resort Cancún Playa, Hotel Quito Histórico,
Hotel Buenos Aires Elegance, Hotel Santiago Business) fueron creados por
``seed_featured_hotels.py`` con datos incompletos y relaciones de país rotas
(ids legacy incorrectos → ``geo_country_code`` XX-N). Este seed idempotente:

- Agrega latitud/longitud, descripción (espejada a ``hotel_content_pages``),
  dirección, moneda local, rating y ``active``.
- Corrige la relación de PAÍS contra la tabla real ``dim_visitor_countries``
  (``prop_country_id``): Perú=219, México=148, Ecuador=60, Argentina=13,
  Chile=44. Opción B: NO escribe campos del catálogo curado
  (``geo_country_code``/``geo_catalog_id``/``geo_city_*``).
- Vincula la CIUDAD contra ``dim_destinations`` vía **``srch_destination_id``**
  (Lima=89, Cancún=311, Buenos Aires=7, Santiago=168).
  Quito no está en ``dim_destinations`` → queda solo como texto ``city``.

Contrato fijado por ``server/tests/test_seed_featured_hotels_geo.py``:
aborta ANTES de escribir si algún país del dataset no existe en
``dim_visitor_countries`` o una ciudad requerida no existe en ``geo_catalog``;
idempotente (2ª pasada = 0 inserciones).

Uso (dentro del contenedor server, apunta a la BD de la env var):

    python scripts/seed_featured_hotels_geo.py --dry-run
    python scripts/seed_featured_hotels_geo.py
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FEATURED_GEO: list[dict[str, Any]] = [
    {
        "prop_id": 1,
        "hotel_name": "Hotel Lima Centro",
        "display_name": "Hotel Lima Centro",
        "hotel_label": "Hotel Lima Centro",
        "prop_country_id": 219,  # Perú (dim_visitor_countries)
        "country_label": "Perú",
        "destination": "Lima",  # srch_destination_id=89
        "city": "Lima",
        "prop_starrating": 4,
        "prop_review_score": 4.6,
        "prop_location_score1": 4.5,
        "latitude": -12.0464,
        "longitude": -77.0428,
        "address": "Jr. de la Unión 123, Centro Histórico, Lima",
        "currency": "PEN",
        "description": (
            "Hotel en el corazón del Centro Histórico de Lima, a pasos de la Plaza "
            "Mayor, con fácil acceso a la Catedral, al Palacio de Gobierno y a la "
            "oferta gastronómica del Malecón de Miraflores."
        ),
    },
    {
        "prop_id": 2,
        "hotel_name": "Resort Cancún Playa",
        "display_name": "Resort Cancún Playa",
        "hotel_label": "Resort Cancún Playa",
        "prop_country_id": 148,  # México (dim_visitor_countries)
        "country_label": "México",
        "destination": "Cancún",  # srch_destination_id=311
        "city": "Cancún",
        "prop_starrating": 5,
        "prop_review_score": 4.8,
        "prop_location_score1": 5.5,
        "latitude": 21.1500,
        "longitude": -86.8100,
        "address": "Blvd. Kukulcán km 8.5, Zona Hotelera, Cancún, Q. Roo",
        "currency": "MXN",
        "description": (
            "Resort frente al mar en la Zona Hotelera de Cancún, con piscinas, spa "
            "y playa privada de arena blanca, ideal para familias y lunas de miel."
        ),
    },
    {
        "prop_id": 3,
        "hotel_name": "Hotel Quito Histórico",
        "display_name": "Hotel Quito Histórico",
        "hotel_label": "Hotel Quito Histórico",
        "prop_country_id": 60,  # Ecuador (dim_visitor_countries)
        "country_label": "Ecuador",
        "destination": None,  # Quito NO está en dim_destinations
        "city": "Quito",
        "prop_starrating": 3,
        "prop_review_score": 4.2,
        "prop_location_score1": 3.8,
        "latitude": -0.2202,
        "longitude": -78.5125,
        "address": "Calle Chile 222, Centro Histórico, Quito",
        "currency": "USD",
        "description": (
            "Hotel colonial en el Centro Histórico de Quito, Patrimonio de la "
            "Humanidad, cerca de la Plaza Grande y de la Basílica del Voto Nacional."
        ),
    },
    {
        "prop_id": 4,
        "hotel_name": "Hotel Buenos Aires Elegance",
        "display_name": "Hotel Buenos Aires Elegance",
        "hotel_label": "Hotel Buenos Aires Elegance",
        "prop_country_id": 13,  # Argentina (dim_visitor_countries)
        "country_label": "Argentina",
        "destination": "Buenos Aires",  # srch_destination_id=7
        "city": "Buenos Aires",
        "prop_starrating": 4,
        "prop_review_score": 4.5,
        "prop_location_score1": 4.8,
        "latitude": -34.6037,
        "longitude": -58.3816,
        "address": "Av. Corrientes 1250, San Nicolás, Buenos Aires",
        "currency": "ARS",
        "description": (
            "Hotel de estilo clásico en el centro de Buenos Aires, cerca del Teatro "
            "Colón y la Casa Rosada, con gastronomía argentina y recepción 24 horas."
        ),
    },
    {
        "prop_id": 5,
        "hotel_name": "Hotel Santiago Business",
        "display_name": "Hotel Santiago Business",
        "hotel_label": "Hotel Santiago Business",
        "prop_country_id": 44,  # Chile (dim_visitor_countries)
        "country_label": "Chile",
        "destination": "Santiago",  # srch_destination_id=168
        "city": "Santiago",
        "prop_starrating": 4,
        "prop_review_score": 4.3,
        "prop_location_score1": 4.2,
        "latitude": -33.4489,
        "longitude": -70.6693,
        "address": "Av. Libertador Bernardo O'Higgins 980, Santiago",
        "currency": "CLP",
        "description": (
            "Hotel ejecutivo en el centro de Santiago, próximo a La Moneda y al "
            "barrio Lastarria, con salas de reuniones y fácil acceso al aeropuerto."
        ),
    },
]


def _resolve_visitor_country(db, country_id: int) -> dict[str, Any]:
    doc = db.dim_visitor_countries.find_one({"visitor_location_country_id": country_id})
    if doc is None:
        raise ValueError(
            f"El país id={country_id} no existe en dim_visitor_countries. "
            "No se puede relacionar un hotel a un país inexistente."
        )
    return doc


def _resolve_destination(db, name: str | None) -> int | None:
    """Id canónico (menor) del destino en dim_destinations, o None si no existe."""
    if not name:
        return None
    doc = db.dim_destinations.find_one(
        {"destination_name": name},
        {"_id": 0, "srch_destination_id": 1},
        sort=[("srch_destination_id", 1)],
    )
    return int(doc["srch_destination_id"]) if doc and doc.get("srch_destination_id") is not None else None


def seed(db, *, dry_run: bool = False) -> dict[str, int]:
    """Completa/corrige los hoteles 1–5 (idempotente, valida antes de escribir)."""
    now = datetime.now(timezone.utc)

    # Validación PRE-escritura: países del dataset.
    for entry in FEATURED_GEO:
        _resolve_visitor_country(db, int(entry["prop_country_id"]))

    created = 0
    skipped = 0
    for entry in FEATURED_GEO:
        prop_id = int(entry["prop_id"])
        visitor = _resolve_visitor_country(db, int(entry["prop_country_id"]))
        dest_id = _resolve_destination(db, entry.get("destination"))
        city_text = entry.get("city") or entry.get("destination") or ""

        doc: dict[str, Any] = {
            "prop_id": prop_id,
            "hotel_name": entry["hotel_name"],
            "display_name": entry["display_name"],
            "hotel_label": entry["hotel_label"],
            "description": entry["description"],
            "address": entry["address"],
            "city": city_text,
            "display_country_label": visitor.get("country_name")
            or visitor.get("country_display_name")
            or visitor.get("visitor_country_label")
            or entry["country_label"],
            "prop_country_id": int(entry["prop_country_id"]),
            "prop_starrating": entry["prop_starrating"],
            "prop_review_score": entry["prop_review_score"],
            "prop_location_score1": entry["prop_location_score1"],
            "latitude": entry["latitude"],
            "longitude": entry["longitude"],
            "currency": entry["currency"],
            "accepted_currencies": [entry["currency"], *[c for c in ("USD",) if c != entry["currency"]]],
            "active": True,
            "manual_override": True,
            "name_source": "manual",
            "original_generated_name": entry["display_name"],
            "updated_by": "seed_featured_hotels_geo",
            "updated_at": now,
            "verified_at": now,
        }
        if dest_id is not None:
            doc["srch_destination_id"] = dest_id

        if dry_run:
            print(f"[dry-run] actualizaría prop_id={prop_id} ({entry['display_name']})")
            created += 1
            continue

        result = db.dim_hotels.update_one(
            {"prop_id": prop_id},
            {"$set": doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        if result.matched_count == 0:
            created += 1
        else:
            skipped += 1

        # Espejo la descripción a hotel_content_pages (fuente canónica).
        db.hotel_content_pages.update_one(
            {"prop_id": prop_id},
            {
                "$set": {
                    "prop_id": prop_id,
                    "description": entry["description"],
                    "highlights": "",
                    "amenities_text": "",
                    "active_amenities": [],
                    "amenities_catalog": [],
                    "source": "seed_featured_hotels_geo",
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    return {"created": created, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description="Completa/corrige los hoteles destacados 1–5.")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar qué se actualizaría sin escribir.")
    args = parser.parse_args()

    from src.database.connection import get_database

    db = get_database()
    print(f"Completando {len(FEATURED_GEO)} hoteles destacados ({'dry-run' if args.dry_run else 'write'})...")
    stats = seed(db, dry_run=args.dry_run)
    print(f"Listo: created={stats['created']}, skipped={stats['skipped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
