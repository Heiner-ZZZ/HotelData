"""One-shot migration: populate daily_duties for existing employees that don't have it.
Run via: docker compose -f infra/docker-compose.yml exec server python scripts/migrate_employee_daily_duties.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import MongoClient
from config.settings import get_settings

DEPT_DEFAULTS: dict[str, list[dict]] = {
    "limpieza": [
        {"label": "Revisar carrito de limpieza", "icon": "shopping_cart"},
        {"label": "Cambiar sábanas y toallas", "icon": "bed"},
        {"label": "Limpiar baño y reponer amenities", "icon": "shower"},
        {"label": "Aspirar y trapear piso", "icon": "mop"},
        {"label": "Sacar basura de habitaciones", "icon": "delete"},
        {"label": "Reportar daños encontrados", "icon": "report"},
    ],
    "housekeeping": [
        {"label": "Revisar carrito de limpieza", "icon": "shopping_cart"},
        {"label": "Cambiar sábanas y toallas", "icon": "bed"},
        {"label": "Limpiar baño y reponer amenities", "icon": "shower"},
        {"label": "Aspirar y trapear piso", "icon": "mop"},
        {"label": "Sacar basura de habitaciones", "icon": "delete"},
        {"label": "Reportar daños encontrados", "icon": "report"},
    ],
    "mantenimiento": [
        {"label": "Revisar reportes de averías", "icon": "plumbing"},
        {"label": "Inspeccionar A/C y calefacción", "icon": "ac_unit"},
        {"label": "Verificar sistemas eléctricos", "icon": "bolt"},
        {"label": "Revisar cerraduras y puertas", "icon": "door_front"},
        {"label": "Documentar reparaciones", "icon": "description"},
    ],
    "maintenance": [
        {"label": "Revisar reportes de averías", "icon": "plumbing"},
        {"label": "Inspeccionar A/C y calefacción", "icon": "ac_unit"},
        {"label": "Verificar sistemas eléctricos", "icon": "bolt"},
        {"label": "Revisar cerraduras y puertas", "icon": "door_front"},
        {"label": "Documentar reparaciones", "icon": "description"},
    ],
    "recepción": [
        {"label": "Revisar llegadas y salidas del día", "icon": "event"},
        {"label": "Confirmar reservas pendientes", "icon": "confirmation_number"},
        {"label": "Atender check-ins programados", "icon": "login"},
        {"label": "Gestionar solicitudes de huéspedes", "icon": "support_agent"},
        {"label": "Cierre de caja y reporte diario", "icon": "receipt_long"},
    ],
    "reception": [
        {"label": "Revisar llegadas y salidas del día", "icon": "event"},
        {"label": "Confirmar reservas pendientes", "icon": "confirmation_number"},
        {"label": "Atender check-ins programados", "icon": "login"},
        {"label": "Gestionar solicitudes de huéspedes", "icon": "support_agent"},
        {"label": "Cierre de caja y reporte diario", "icon": "receipt_long"},
    ],
}

GENERIC_DUTIES = [
    {"label": "Revisar asignaciones del día", "icon": "task_alt"},
    {"label": "Completar check-in de turno", "icon": "how_to_reg"},
    {"label": "Atender solicitudes pendientes", "icon": "pending_actions"},
    {"label": "Reportar novedades al supervisor", "icon": "report"},
]


def main() -> int:
    s = get_settings()
    c = MongoClient(s.mongo_uri)
    db = c[s.mongo_database]

    # Find employees missing daily_duties
    query = {"$or": [
        {"daily_duties": {"$exists": False}},
        {"daily_duties": None},
        {"daily_duties": []},
    ]}
    employees = list(db.employees.find(query, {"_id": 1, "full_name": 1, "department": 1}))
    print(f"Found {len(employees)} employee(s) without daily_duties")

    updated = 0
    for emp in employees:
        dept = (emp.get("department") or "").strip().lower()
        duties = DEPT_DEFAULTS.get(dept, GENERIC_DUTIES)
        db.employees.update_one(
            {"_id": emp["_id"]},
            {"$set": {"daily_duties": duties}},
        )
        print(f"  {emp.get('full_name', str(emp['_id']))} ({dept or 'sin depto'}) → {len(duties)} duties")
        updated += 1

    print(f"\nMigrated {updated} employee(s).")
    # Verify
    remaining = db.employees.count_documents(query)
    print(f"Remaining without duties: {remaining}")
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
