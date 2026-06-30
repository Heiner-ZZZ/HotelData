"""Seed hotel products (billable add-ons) for all properties.

Creates a catalog of products across categories: Minibar, Spa, Restaurante,
Lavandería, Parking, Mascotas, Room Service, Daños, Late Checkout.

Run: python /app/scripts/seed_hotel_products.py
"""

from __future__ import annotations

import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database


PRODUCT_CATEGORIES = {
    "Minibar": [
        ("Agua embotellada", 3.50),
        ("Refresco", 4.00),
        ("Cerveza nacional", 5.00),
        ("Jugo natural", 4.50),
        ("Snacks", 3.00),
        ("Vino tinto (botella)", 25.00),
    ],
    "Spa": [
        ("Masaje relajante 60min", 60.00),
        ("Masaje deportivo 60min", 70.00),
        ("Facial hidratante", 45.00),
        ("Acceso a sauna", 25.00),
        ("Acceso a jacuzzi", 20.00),
        ("Tratamiento corporal", 55.00),
    ],
    "Restaurante": [
        ("Desayuno bufé", 18.00),
        ("Cena menú ejecutivo", 35.00),
        ("Comida ligera", 15.00),
        ("Botella de vino", 30.00),
        ("Postre artesanal", 8.00),
    ],
    "Lavandería": [
        ("Lavado y planchado (prenda)", 5.00),
        ("Lavado en seco (traje)", 12.00),
        ("Planchado solo (prenda)", 3.50),
        ("Lavado urgente (24h)", 15.00),
    ],
    "Parking": [
        ("Estacionamiento por noche", 15.00),
        ("Valet parking por noche", 25.00),
        ("Estacionamiento vehículo grande", 20.00),
    ],
    "Mascotas": [
        ("Estadía mascota pequeña", 20.00),
        ("Estadía mascota grande", 35.00),
        ("Kit de mascota (cama, platos)", 10.00),
    ],
    "Room Service": [
        ("Desayuno en habitación", 22.00),
        ("Cena en habitación", 40.00),
        ("Bandeja de frutas", 12.00),
        ("Champagne (botella)", 45.00),
    ],
    "Daños": [
        ("Daño menor (mueble)", 50.00),
        ("Daño mayor (pared/ventana)", 150.00),
        ("Objeto faltante (toalla/bata)", 30.00),
        ("Limpieza especial (mancha)", 40.00),
    ],
    "Late Checkout": [
        ("Late checkout hasta 14:00", 25.00),
        ("Late checkout hasta 16:00", 45.00),
        ("Late checkout hasta 18:00", 65.00),
    ],
    "Extras": [
        ("Cama extra por noche", 30.00),
        ("Cuna para bebé por noche", 15.00),
        ("Adaptador de corriente", 5.00),
        ("Caja de seguridad", 8.00),
        ("Wifi premium", 10.00),
    ],
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def main() -> int:
    db = get_database()

    # Delete existing seed products (prop_id < 100 to avoid deleting real data)
    db.hotel_products.delete_many({"prop_id": {"$lte": 10}, "seed_source": "seed_hotel_products"})

    # Get all active properties that have hotel_rooms
    prop_ids = sorted(
        db.dim_hotels.distinct("prop_id", {"prop_id": {"$gte": 1, "$lte": 5}})
    )
    if not prop_ids:
        prop_ids = list(range(1, 6))

    total_created = 0
    for prop_id in prop_ids:
        for category, items in PRODUCT_CATEGORIES.items():
            for name, price in items:
                product_id = f"PROD-{secrets.token_hex(4).upper()}"
                doc = {
                    "prop_id": prop_id,
                    "product_id": product_id,
                    "name": name,
                    "description": f"{name} — categoría {category}",
                    "unit_price": round(price, 2),
                    "quantity_available": 50,
                    "category": category,
                    "is_active": True,
                    "seed_source": "seed_hotel_products",
                    "created_by": "system",
                    "created_at": utc_now(),
                    "updated_at": utc_now(),
                }
                db.hotel_products.insert_one(doc)
                total_created += 1

    summary = {
        "prop_ids": prop_ids,
        "products_per_prop": sum(len(v) for v in PRODUCT_CATEGORIES.values()),
        "total_created": total_created,
        "categories": list(PRODUCT_CATEGORIES.keys()),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    print(f"✅ {total_created} productos creados para {len(prop_ids)} propiedad(es)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
