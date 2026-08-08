"""Bootstrap de colecciones e índices del módulo hotels (dimensión ``dim_hotels``).

El gate operativo (Fase A — `docs/APROBACION_HOTELES_Y_PRICING.md` §4) ejecuta
``published_prop_ids()`` en CADA búsqueda pública:

    db.dim_hotels.find({"published": {"$ne": False}}, {"_id": 0, "prop_id": 1})

Sin índice eso es un COLLSCAN de toda la dimensión por búsqueda. Este bootstrap
garantiza, de forma idempotente en el lifespan (`src/app/main.py`), que:

- ``published_1_prop_id_1`` — índice compuesto cuyas claves cubren exactamente
  la query (``published``) y la proyección (``prop_id``) del gate. El prefijo
  izquierdo sirve también cualquier filtro puro por ``published``.
- ``is_operational_1`` — el flag hermano que approve/onboarding escriben junto
  a ``published``; útil para auditorías y consultas operativas por estado.

Estilo del proyecto: bootstrap descentralizado — cada módulo posee su
``ensure_*_collections`` (mismo patrón que partner/revenue/billing/…), llamado
una vez en el lifespan y en el conftest de tests (aislamiento por test).
"""
from __future__ import annotations

from pymongo import ASCENDING, IndexModel

from src.database.collections import ensure_collection

# Índices de la dimensión de hoteles para el gate operativo (published).
# El compuesto (published, prop_id) hace de ``published_prop_ids`` un scan
# acotado por el índice (IXSCAN) en vez de un barrido completo de la colección.
HOTELS_DIM_HOTELS_INDEXES: list[IndexModel] = [
    IndexModel(
        [("published", ASCENDING), ("prop_id", ASCENDING)],
        name="published_1_prop_id_1",
    ),
    IndexModel([("is_operational", ASCENDING)], name="is_operational_1"),
]


def ensure_hotels_collections() -> dict[str, list[str]]:
    """Crea (si faltan) la colección ``dim_hotels`` y sus índices operativos.

    Additiva respecto al bootstrap del partner (``DIM_HOTELS_INDEXES`` en
    ``partner/services/bootstrap.py``): no dropea ni redefine índices ajenos.
    """
    created = ensure_collection("dim_hotels", HOTELS_DIM_HOTELS_INDEXES)
    return {
        "collections": [c for c in created if c.startswith("collection:")],
        "indexes": [c for c in created if c.startswith("index:")],
    }
