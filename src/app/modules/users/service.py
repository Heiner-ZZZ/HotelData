from __future__ import annotations

from src.app.modules.users.schemas import ModuleStatus


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="users",
        status="planned",
        description="Preparado para usuarios, roles y perfiles futuros; sin control de acceso real en GA03.",
    )
