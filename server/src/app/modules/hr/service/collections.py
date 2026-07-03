from __future__ import annotations

from pymongo import ASCENDING, IndexModel

from src.database.collections import ensure_collection

EMPLOYEES_COLLECTION = "employees"
DEPARTMENTS_COLLECTION = "employee_departments"
DOCUMENTS_COLLECTION = "employee_documents"
SHIFTS_COLLECTION = "employee_shifts"

EMPLOYEES_INDEXES = [
    IndexModel([("full_name", ASCENDING)], name="idx_emp_name"),
    IndexModel([("department", ASCENDING)], name="idx_emp_dept"),
    IndexModel([("position", ASCENDING)], name="idx_emp_position"),
    IndexModel([("is_active", ASCENDING)], name="idx_emp_active"),
    IndexModel([("id_document", ASCENDING)], name="idx_emp_doc", unique=True),
]

DEPARTMENTS_INDEXES = [
    IndexModel([("name", ASCENDING)], name="idx_dept_name", unique=True),
]

DOCUMENTS_INDEXES = [
    IndexModel([("employee_id", ASCENDING)], name="idx_doc_employee"),
    IndexModel([("doc_type", ASCENDING)], name="idx_doc_type"),
]

SHIFTS_INDEXES = [
    IndexModel([("employee_id", ASCENDING)], name="idx_shift_employee"),
    IndexModel([("date", ASCENDING)], name="idx_shift_date"),
]


def ensure_hr_collections() -> None:
    ensure_collection(EMPLOYEES_COLLECTION, EMPLOYEES_INDEXES)
    ensure_collection(DEPARTMENTS_COLLECTION, DEPARTMENTS_INDEXES)
    ensure_collection(DOCUMENTS_COLLECTION, DOCUMENTS_INDEXES)
    ensure_collection(SHIFTS_COLLECTION, SHIFTS_INDEXES)


def module_status() -> ModuleStatus:
    from src.app.modules.hr.schemas import ModuleStatus
    return ModuleStatus(
        module="hr",
        status="active",
        description="Gestión de empleados (RRHH): altas, documentos, turnos y departamentos.",
    )
