from __future__ import annotations

from src.app.modules.audit.schemas import ModuleStatus


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="audit",
        status="preparation",
        description="Preparado para auditoria ampliada; la auditoria ETL actual sigue en features/audit.",
    )
