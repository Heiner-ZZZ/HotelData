"""Seed the employees collection with demo data for HR module testing."""
from __future__ import annotations

from datetime import datetime, timezone

from src.database.connection import get_database
from src.app.modules.hr.service.collections import ensure_hr_collections

EMPLOYEES = [
    {
        "full_name": "María Gómez",
        "id_document": "EMP-001",
        "phone": "+52 55 1234 5678",
        "email": "maria.gomez@hoteldata.local",
        "address": "Av. Reforma 123, CDMX",
        "position": "Recepcionista",
        "department": "Recepción",
        "hire_date": "2023-06-15",
        "salary": 15000.0,
        "emergency_contact": "Juan Gómez",
        "emergency_phone": "+52 55 8765 4321",
        "notes": "Turno matutino, bilingüe inglés-español",
        "prop_id": 1,
        "is_active": True,
    },
    {
        "full_name": "Carlos Mendoza",
        "id_document": "EMP-002",
        "phone": "+52 55 2345 6789",
        "email": "carlos.mendoza@hoteldata.local",
        "address": "Calle 5 de Mayo 456, CDMX",
        "position": "Supervisor de Recepción",
        "department": "Recepción",
        "hire_date": "2022-03-01",
        "salary": 22000.0,
        "emergency_contact": "Ana Mendoza",
        "emergency_phone": "+52 55 9876 5432",
        "notes": "10 años de experiencia en hotelería",
        "prop_id": 1,
        "is_active": True,
    },
    {
        "full_name": "Laura Castillo",
        "id_document": "EMP-003",
        "phone": "+52 55 3456 7890",
        "email": "laura.castillo@hoteldata.local",
        "address": "Blvd. Insurgentes 789, CDMX",
        "position": "Housekeeping Manager",
        "department": "Limpieza",
        "hire_date": "2023-01-10",
        "salary": 18000.0,
        "emergency_contact": "Pedro Castillo",
        "emergency_phone": "+52 55 6543 2109",
        "notes": "Certificada en estándares de limpieza AAA",
        "prop_id": 1,
        "is_active": True,
    },
    {
        "full_name": "Roberto Álvarez",
        "id_document": "EMP-004",
        "phone": "+52 55 4567 8901",
        "email": "roberto.alvarez@hoteldata.local",
        "address": "Calle Juárez 234, CDMX",
        "position": "Revenue Manager",
        "department": "Revenue",
        "hire_date": "2021-08-20",
        "salary": 28000.0,
        "emergency_contact": "Sofía Álvarez",
        "emergency_phone": "+52 55 3210 9876",
        "notes": "Experto en pricing dinámico y yield management",
        "prop_id": 1,
        "is_active": True,
    },
    {
        "full_name": "Patricia Núñez",
        "id_document": "EMP-005",
        "phone": "+52 55 5678 9012",
        "email": "patricia.nunez@hoteldata.local",
        "address": "Av. Universidad 567, CDMX",
        "position": "Gerente General",
        "department": "Administración",
        "hire_date": "2020-01-05",
        "salary": 35000.0,
        "emergency_contact": "Miguel Núñez",
        "emergency_phone": "+52 55 1098 7654",
        "notes": "MBA en Hospitalidad, 15 años de experiencia",
        "prop_id": 1,
        "is_active": True,
    },
]


def seed_employees() -> None:
    db = get_database()
    ensure_hr_collections()
    now = datetime.now(timezone.utc)

    existing = db.employees.count_documents({})
    if existing > 0:
        print(f"⚠ {existing} empleados ya existen. Saltando seed.")
        return

    for emp in EMPLOYEES:
        emp["created_at"] = now
        emp["updated_at"] = now
        db.employees.insert_one(emp)

    print(f"✅ {len(EMPLOYEES)} empleados insertados exitosamente.")


if __name__ == "__main__":
    seed_employees()
