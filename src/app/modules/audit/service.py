from __future__ import annotations

from src.app.modules.audit.schemas import ModuleStatus, RecentActivity
from src.database.connection import get_database


def recent_activity(limit: int = 20) -> RecentActivity:
    """Read recent ETL executions and search logs from Mongo.

    Migrated from `src.app.features.audit.service` in Phase 2 (see
    ADR-0006). The legacy file in `features/audit/` stays in place
    but is no longer mounted in `src.app.main`.
    """
    db = get_database()
    return RecentActivity(
        etl_executions=list(
            db.etl_executions.find({}, {"_id": 0}).sort("executed_at", -1).limit(limit)
        ),
        search_logs=list(
            db.search_logs.find({}, {"_id": 0}).sort("searched_at", -1).limit(limit)
        ),
    )


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="audit",
        status="active",
        description="Auditoria ETL y busquedas migrada a modules/audit (ADR-0006).",
    )
