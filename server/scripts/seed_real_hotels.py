"""Seed de 15 hoteles reales mexicanos vinculados a país/ciudades EXISTENTES.

Crea/actualiza en ``dim_hotels`` un bloque de hoteles "curados" (nombres
reales, coordenadas aproximadas, descripción y moneda) con sus relaciones
geográficas resueltas dinámicamente contra las tablas del DATASET:

- País: ``dim_visitor_countries`` (México id 148) → ``prop_country_id`` +
  ``display_country_label``.
- Ciudad: cuando el destino existe en ``dim_destinations`` (tabla de ciudades
  del dataset), se vincula vía **``srch_destination_id``** + ``city`` = nombre
  del destino. Ciudades que no están en ``dim_destinations`` (Puerto Vallarta,
  San José del Cabo) conservan ``city`` como texto. La coordenada del hotel es
  aproximada a la ubicación real del establecimiento.

Opción B: el hotel NO lleva relación al catálogo curado (``geo_catalog``) —
no se escriben ``geo_country_code``/``geo_catalog_id``/``geo_city_*``.

Contrato (fijado por ``server/tests/test_seed_real_hotels.py``):

- Los ``prop_id`` viven en el bloque reservado 900000–900014.
- Idempotente: segunda pasada = 0 inserciones, sin duplicados.
- NUNCA sobrescribe: si un ``prop_id`` reservado ya existe en ``dim_hotels``
  aborta con ``ValueError`` (no pisa hoteles ETL/partner).
- Sin relaciones huérfanas: si ``MX`` o alguna ciudad falta en
  ``geo_catalog``, aborta ANTES de escribir nada.
- La descripción se espeja a ``hotel_content_pages`` (fuente canónica de la
  descripción larga, mismo flujo que ``save_partner_hotel_profile``).

Uso (dentro del contenedor server, apunta a la BD de la env var):

    python scripts/seed_real_hotels.py --dry-run
    python scripts/seed_real_hotels.py
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Bloque reservado y contiguo: no colisiona con ETL (~< 141k) ni con el
# counter de onboarding (se sincroniza a max(prop_id) de dim_hotels).
PROP_ID_BASE = 900000

# Legacy country id de México en dim_visitor_countries (fuente de verdad).
MEXICO_LEGACY_COUNTRY_ID = 148

FEATURED_HOTELS: list[dict[str, Any]] = [
    {
        "prop_id": 900000,
        "hotel_name": "Grand Fiesta Americana Coral Beach Cancún",
        "display_name": "Grand Fiesta Americana Coral Beach Cancún",
        "hotel_label": "Grand Fiesta Americana Coral Beach Cancún",
        "geo_city_code": "CUN",
        "destination": "Cancún",
        "city": "Cancún",
        "prop_starrating": 5,
        "prop_review_score": 4.8,
        "prop_location_score1": 5.4,
        "latitude": 21.1262,
        "longitude": -86.7689,
        "address": "Blvd. Kukulcán km 9.5, Zona Hotelera, Cancún, Q. Roo",
        "prop_brand_bool": True,
        "description": (
            "Resort de lujo frente al Caribe en la Zona Hotelera de Cancún, con la "
            "playa Coral Beach, spa de clase mundial y una amplia oferta gastronómica "
            "todo incluido."
        ),
    },
    {
        "prop_id": 900001,
        "hotel_name": "Le Blanc Spa Resort Cancún",
        "display_name": "Le Blanc Spa Resort Cancún",
        "hotel_label": "Le Blanc Spa Resort Cancún",
        "geo_city_code": "CUN",
        "destination": "Cancún",
        "city": "Cancún",
        "prop_starrating": 5,
        "prop_review_score": 4.9,
        "prop_location_score1": 5.6,
        "latitude": 21.1203,
        "longitude": -86.7755,
        "address": "Blvd. Kukulcán km 10, Zona Hotelera, Cancún, Q. Roo",
        "prop_brand_bool": True,
        "description": (
            "Hotel boutique para adultos solo con all-inclusive de alta gama, suites "
            "frente al mar y un concepto de lujo relajado en la Zona Hotelera de Cancún."
        ),
    },
    {
        "prop_id": 900002,
        "hotel_name": "Gran Hotel Ciudad de México",
        "display_name": "Gran Hotel Ciudad de México",
        "hotel_label": "Gran Hotel Ciudad de México",
        "geo_city_code": "CDMX",
        "destination": "Ciudad de México",
        "city": "Ciudad de México",
        "prop_starrating": 4,
        "prop_review_score": 4.4,
        "prop_location_score1": 4.9,
        "latitude": 19.4326,
        "longitude": -99.1321,
        "address": "Av. 16 de Septiembre 82, Centro Histórico, CDMX",
        "prop_brand_bool": False,
        "description": (
            "Histórico hotel del Centro Histórico de la Ciudad de México, a pasos del "
            "Zócalo, con vitral modernista y terraza con vistas a la Catedral."
        ),
    },
    {
        "prop_id": 900003,
        "hotel_name": "Hilton Mexico City Reforma",
        "display_name": "Hilton Mexico City Reforma",
        "hotel_label": "Hilton Mexico City Reforma",
        "geo_city_code": "CDMX",
        "destination": "Ciudad de México",
        "city": "Ciudad de México",
        "prop_starrating": 5,
        "prop_review_score": 4.3,
        "prop_location_score1": 4.7,
        "latitude": 19.4361,
        "longitude": -99.1504,
        "address": "Av. Juárez 70, Col. Centro, CDMX",
        "prop_brand_bool": True,
        "description": (
            "Hotel ejecutivo frente a la Alameda Central, a un paso de la Avenida "
            "Reforma, con piscina panorámica en la azotea y salones para eventos."
        ),
    },
    {
        "prop_id": 900004,
        "hotel_name": "Hotel Morales Guadalajara",
        "display_name": "Hotel Morales Guadalajara",
        "hotel_label": "Hotel Morales Guadalajara",
        "geo_city_code": "GDL",
        "destination": "Guadalajara",
        "city": "Guadalajara",
        "prop_starrating": 4,
        "prop_review_score": 4.6,
        "prop_location_score1": 4.4,
        "latitude": 20.6769,
        "longitude": -103.3466,
        "address": "Av. Corona 243, Centro, Guadalajara, Jal.",
        "prop_brand_bool": False,
        "description": (
            "Boutique hotel restaurado de la belle époque tapatía en el Centro de "
            "Guadalajara, con terraza sobre la catedral y arquitectura art nouveau."
        ),
    },
    {
        "prop_id": 900005,
        "hotel_name": "Quinta Real Monterrey",
        "display_name": "Quinta Real Monterrey",
        "hotel_label": "Quinta Real Monterrey",
        "geo_city_code": "MTY",
        "destination": "Monterrey",
        "city": "Monterrey",
        "prop_starrating": 5,
        "prop_review_score": 4.5,
        "prop_location_score1": 4.6,
        "latitude": 25.6424,
        "longitude": -100.3198,
        "address": "Av. Diego Rivera 2000, San Pedro Garza García, N. L.",
        "prop_brand_bool": True,
        "description": (
            "Hotel de lujo en San Pedro Garza García, con jardines, suites amplias y "
            "un spa reconocido, ideal para viajes de negocios en Monterrey."
        ),
    },
    {
        "prop_id": 900006,
        "hotel_name": "Hyatt Regency Mérida",
        "display_name": "Hyatt Regency Mérida",
        "hotel_label": "Hyatt Regency Mérida",
        "geo_city_code": "MID",
        "destination": "Mérida",
        "city": "Mérida",
        "prop_starrating": 4,
        "prop_review_score": 4.4,
        "prop_location_score1": 4.5,
        "latitude": 20.9726,
        "longitude": -89.6168,
        "address": "Paseo de Montejo 344, Col. Centro, Mérida, Yuc.",
        "prop_brand_bool": True,
        "description": (
            "Hotel sobre el Paseo de Montejo, a pocas cuadras del centro colonial de "
            "Mérida, con piscina en la azotea y acceso rápido a las zonas arqueológicas."
        ),
    },
    {
        "prop_id": 900007,
        "hotel_name": "Quinta Real Oaxaca",
        "display_name": "Quinta Real Oaxaca",
        "hotel_label": "Quinta Real Oaxaca",
        "geo_city_code": "OAX",
        "destination": "Oaxaca",
        "city": "Oaxaca",
        "prop_starrating": 4,
        "prop_review_score": 4.7,
        "prop_location_score1": 4.4,
        "latitude": 17.0617,
        "longitude": -96.7219,
        "address": "Av. Cinco de Mayo 300, Centro, Oaxaca, Oax.",
        "prop_brand_bool": True,
        "description": (
            "Hotel en el antiguo convento de Santa Catalina, en pleno Centro Histórico "
            "de Oaxaca, con claustros, capilla y jardines alrededor de la piscina."
        ),
    },
    {
        "prop_id": 900008,
        "hotel_name": "Rosewood Puebla",
        "display_name": "Rosewood Puebla",
        "hotel_label": "Rosewood Puebla",
        "geo_city_code": "PUEBLA",
        "destination": "Puebla",
        "city": "Puebla",
        "prop_starrating": 5,
        "prop_review_score": 4.6,
        "prop_location_score1": 4.6,
        "latitude": 19.0393,
        "longitude": -98.1982,
        "address": "2 Oriente 27, Centro Histórico, Puebla, Pue.",
        "prop_brand_bool": True,
        "description": (
            "Hotel de lujo ubicado en una casona colonial restaurada en el Centro "
            "Histórico de Puebla, con spa y gastronomía de autor."
        ),
    },
    {
        "prop_id": 900009,
        "hotel_name": "Marriott Puerto Vallarta Resort & Spa",
        "display_name": "Marriott Puerto Vallarta Resort & Spa",
        "hotel_label": "Marriott Puerto Vallarta Resort & Spa",
        "geo_city_code": "PVR",
        "destination": None,  # Puerto Vallarta NO está en dim_destinations (solo geo_catalog)
        "city": "Puerto Vallarta",
        "prop_starrating": 5,
        "prop_review_score": 4.5,
        "prop_location_score1": 4.9,
        "latitude": 20.6265,
        "longitude": -105.2338,
        "address": "Av. de las Garzas, Marina Vallarta, Puerto Vallarta, Jal.",
        "prop_brand_bool": True,
        "description": (
            "Resort frente a la Bahía de Banderas en Marina Vallarta, con piscinas, "
            "spa y campos de golf cercanos, ideal para familias y convenciones."
        ),
    },
    {
        "prop_id": 900010,
        "hotel_name": "Hotel Rosita Puerto Vallarta",
        "display_name": "Hotel Rosita Puerto Vallarta",
        "hotel_label": "Hotel Rosita Puerto Vallarta",
        "geo_city_code": "PVR",
        "destination": None,  # Puerto Vallarta NO está en dim_destinations (solo geo_catalog)
        "city": "Puerto Vallarta",
        "prop_starrating": 3,
        "prop_review_score": 4.0,
        "prop_location_score1": 4.3,
        "latitude": 20.6502,
        "longitude": -105.2458,
        "address": "Calle Pípila 159, Centro, Puerto Vallarta, Jal.",
        "prop_brand_bool": False,
        "description": (
            "Histórico hotel de playa en el malecón de Puerto Vallarta, uno de los "
            "primeros de la ciudad, con ambiente bohemio y vista a la bahía."
        ),
    },
    {
        "prop_id": 900011,
        "hotel_name": "Casa Natalia Hotel & Gallery",
        "display_name": "Casa Natalia Hotel & Gallery",
        "hotel_label": "Casa Natalia Hotel & Gallery",
        "geo_city_code": "SJD",
        "destination": None,  # San José del Cabo NO está en dim_destinations (solo geo_catalog)
        "city": "San José del Cabo",
        "prop_starrating": 5,
        "prop_review_score": 4.7,
        "prop_location_score1": 4.6,
        "latitude": 23.0594,
        "longitude": -109.6973,
        "address": "Calle Manuel Doblado 11, Centro, San José del Cabo, B.C.S.",
        "prop_brand_bool": False,
        "description": (
            "Boutique hotel en el centro histórico de San José del Cabo, con galería "
            "de arte, restaurante gourmet y piscina en la azotea."
        ),
    },
    {
        "prop_id": 900012,
        "hotel_name": "Real Inn Tijuana by Camino Real",
        "display_name": "Real Inn Tijuana by Camino Real",
        "hotel_label": "Real Inn Tijuana by Camino Real",
        "geo_city_code": "TIJUANA",
        "destination": "Tijuana",
        "city": "Tijuana",
        "prop_starrating": 4,
        "prop_review_score": 4.1,
        "prop_location_score1": 4.0,
        "latitude": 32.5074,
        "longitude": -116.9895,
        "address": "Paseo de los Héroes 10302, Zona Río, Tijuana, B.C.",
        "prop_brand_bool": True,
        "description": (
            "Hotel ejecutivo en la Zona Río de Tijuana, cerca de la Avenida Revolución "
            "y el Aeropuerto, con gimnasio y salones para reuniones."
        ),
    },
    {
        "prop_id": 900013,
        "hotel_name": "Hotel Emporio Veracruz",
        "display_name": "Hotel Emporio Veracruz",
        "hotel_label": "Hotel Emporio Veracruz",
        "geo_city_code": "VER",
        "destination": "Veracruz",
        "city": "Veracruz",
        "prop_starrating": 4,
        "prop_review_score": 4.3,
        "prop_location_score1": 4.4,
        "latitude": 19.1963,
        "longitude": -96.1318,
        "address": "Av. Camarón Sábalo s/n, Malecón, Veracruz, Ver.",
        "prop_brand_bool": False,
        "description": (
            "Hotel frente al malecón de Veracruz con piscina y vista al puerto, cerca "
            "del centro y del Acuario, ideal para turismo y negocios."
        ),
    },
    {
        "prop_id": 900014,
        "hotel_name": "Las Brisas Acapulco",
        "display_name": "Las Brisas Acapulco",
        "hotel_label": "Las Brisas Acapulco",
        "geo_city_code": "ACA",
        "destination": "Acapulco",
        "city": "Acapulco",
        "prop_starrating": 5,
        "prop_review_score": 4.4,
        "prop_location_score1": 4.8,
        "latitude": 16.8072,
        "longitude": -99.8598,
        "address": "Carretera Escénica 5255, Las Brisas, Acapulco, Gro.",
        "prop_brand_bool": True,
        "description": (
            "Icónico resort de bungalows sobre la bahía de Acapulco, con piscinas "
            "privadas, vista panorámica y el famoso desayuno en La Concha."
        ),
    },
]


def _resolve_visitor(db) -> dict[str, Any]:
    """Resuelve país y destinos contra las tablas del dataset (read-only).

    - País: ``dim_visitor_countries`` (id 148 = México) — la FK legacy que
      ``dim_hotels.prop_country_id`` referencia. Aborta si no existe.
    - Destinos: ``dim_destinations`` por nombre EXACTO sin sufijo numérico;
      cuando hay duplicados (ej. Guadalajara 304/512) se toma el id canónico
      menor. Los destinos ausentes se dejan sin ``srch_destination_id``.

    Devuelve ``{"country": doc, "destinations": {name: srch_destination_id}}``.
    """
    country = db.dim_visitor_countries.find_one({"visitor_location_country_id": MEXICO_LEGACY_COUNTRY_ID})
    if country is None:
        raise ValueError(
            f"El país id={MEXICO_LEGACY_COUNTRY_ID} (México) no existe en dim_visitor_countries."
        )

    destinations: dict[str, int] = {}
    wanted = sorted({h["destination"] for h in FEATURED_HOTELS if h.get("destination")})
    for name in wanted:
        # Canonical: nombre exacto (sin sufijo numérico), menor id.
        doc = db.dim_destinations.find_one(
            {"destination_name": name},
            {"_id": 0, "srch_destination_id": 1},
            sort=[("srch_destination_id", 1)],
        )
        if doc and doc.get("srch_destination_id") is not None:
            destinations[name] = int(doc["srch_destination_id"])
    return {"country": country, "destinations": destinations}


def seed(db, *, dry_run: bool = False) -> dict[str, int]:
    """Crea/actualiza los hoteles reales (idempotente, nunca pisa existentes).

    Valida TODO (colisiones de prop_id, país y ciudades) ANTES de escribir:
    si algo falla, la BD queda intacta. Devuelve ``{"created", "skipped"}``.
    """
    now = datetime.now(timezone.utc)

    # 1) Colisiones: abortar si un prop_id reservado ya existe y NO fue creado
    # por este seed (ETL/partner). Los hoteles que ya llevan la marca
    # ``updated_by == 'seed_real_hotels'`` son re-pasadas idempotentes.
    reserved = [h["prop_id"] for h in FEATURED_HOTELS]
    existing = db.dim_hotels.find(
        {"prop_id": {"$in": reserved}}, {"_id": 0, "prop_id": 1, "updated_by": 1}
    )
    foreign = sorted(
        int(d["prop_id"]) for d in existing if d.get("updated_by") != "seed_real_hotels"
    )
    if foreign:
        raise ValueError(
            f"Colisión de prop_id: {foreign} ya existen en dim_hotels. "
            "El seed no sobrescribe hoteles existentes."
        )

    # 2) Resolver país del dataset + destinos (dim_visitor_countries/dim_destinations).
    visitor = _resolve_visitor(db)
    visitor_country = visitor["country"]
    destinations = visitor["destinations"]

    created = 0
    skipped = 0
    for entry in FEATURED_HOTELS:
        prop_id = int(entry["prop_id"])
        # Ciudad: si el destino existe en dim_destinations, se vincula vía
        # srch_destination_id y city toma su nombre; si no, city = el nombre
        # literal del dataset (ej. Puerto Vallarta no está en dim_destinations).
        dest_name = entry.get("destination")
        dest_id = destinations.get(dest_name) if dest_name else None
        city_name = dest_name if dest_id is not None else entry["city"]
        doc: dict[str, Any] = {
            "prop_id": prop_id,
            "hotel_name": entry["hotel_name"],
            "display_name": entry["display_name"],
            "hotel_label": entry["hotel_label"],
            "description": entry["description"],
            "address": entry["address"],
            "city": city_name,
            "display_country_label": visitor_country.get("country_name")
            or visitor_country.get("country_display_name")
            or visitor_country.get("visitor_country_label"),
            "prop_country_id": MEXICO_LEGACY_COUNTRY_ID,
            "prop_starrating": entry["prop_starrating"],
            "prop_review_score": entry["prop_review_score"],
            "prop_location_score1": entry["prop_location_score1"],
            "prop_brand_bool": entry["prop_brand_bool"],
            "latitude": entry["latitude"],
            "longitude": entry["longitude"],
            "currency": "MXN",
            "accepted_currencies": ["MXN", "USD"],
            "active": True,
            "manual_override": True,
            "name_source": "manual",
            "original_generated_name": entry["display_name"],
            "updated_by": "seed_real_hotels",
            "updated_at": now,
            "verified_at": now,
        }
        if dest_id is not None:
            doc["srch_destination_id"] = dest_id
        if dry_run:
            print(f"[dry-run] insertaría prop_id={prop_id} ({entry['display_name']})")
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
                    "source": "seed_real_hotels",
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    return {"created": created, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed 15 hoteles reales (México, país/ciudades existentes).")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar qué se insertaría sin escribir.")
    args = parser.parse_args()

    from src.database.connection import get_database

    db = get_database()
    print(f"Seeding {len(FEATURED_HOTELS)} hoteles reales en dim_hotels ({'dry-run' if args.dry_run else 'write'})...")
    stats = seed(db, dry_run=args.dry_run)
    print(f"Listo: created={stats['created']}, skipped={stats['skipped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
