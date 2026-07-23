"""Link existing employees to employee_departments via department_id FK.

Idempotent: only updates employees without a department_id.
Handles the legacy inconsistency: ``"Limpieza"`` → ``"Housekeeping"``.
Other departments match by exact name.

Also adds ``department_name`` (denormalized label) for queries that
need the display name without a join.
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from src.database.connection import get_database  # noqa: E402

# Legacy name overrides: employee.department → catalog name
_DEPARTMENT_RENAMES = {
    "Limpieza": "Housekeeping",
}


def migrate() -> None:
    db = get_database()

    # Build name → _id lookup from catalog
    print("Building department name → _id lookup...")
    name_to_id: dict[str, object] = {}
    for dept in db.employee_departments.find({}, {"name": 1}):
        name = dept.get("name", "").strip()
        if name:
            name_to_id[name] = dept["_id"]
    print(f"  → {len(name_to_id)} departments mapped.")

    # Find employees needing migration
    query = {
        "$or": [
            {"department_id": {"$exists": False}},
            {"department_id": None},
            {"department_id": ""},
        ]
    }

    employees = list(db.employees.find(query, {"_id": 1, "department": 1, "full_name": 1}))
    print(f"\nEmployees needing migration: {len(employees)}")

    updated = 0
    skipped: list[str] = []

    for emp in employees:
        eid = emp["_id"]
        dept = (emp.get("department") or "").strip()

        if not dept:
            skipped.append(f"{emp.get('full_name', '?')}: department vacío")
            continue

        # Apply legacy rename if applicable
        canonical = _DEPARTMENT_RENAMES.get(dept, dept)
        dept_id = name_to_id.get(canonical)

        if dept_id:
            db.employees.update_one(
                {"_id": eid},
                {"$set": {
                    "department_id": dept_id,
                    "department_name": canonical,
                }},
            )
            updated += 1
        else:
            skipped.append(f"{emp.get('full_name', '?')}: department={dept!r} → canonical={canonical!r} not in catalog")

    print(f"\nDone: {updated}/{len(employees)} migrated.")
    if skipped:
        print(f"Skipped {len(skipped)}:")
        for s in skipped:
            print(f"  - {s}")


if __name__ == "__main__":
    migrate()
