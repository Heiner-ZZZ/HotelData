from __future__ import annotations

from pydantic import BaseModel


class ModuleStatus(BaseModel):
    module: str
    status: str
    description: str


class RecentActivity(BaseModel):
    etl_executions: list[dict]
    search_logs: list[dict]
