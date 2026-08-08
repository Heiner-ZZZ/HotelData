"""Hotel-scoped read-only financial reconciliation API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field

from src.app.modules.financial_reconciliation.service import build_reconciliation_report
from src.app.security.dependencies import require_prop_permission
from src.database.connection import get_database

api_router = APIRouter(
    prefix="/api/hotels/{prop_id}/reconciliation",
    tags=["financial-reconciliation"],
)


class ReconciliationLedgerResponse(BaseModel):
    debit: float = 0.0
    credit: float = 0.0
    difference: float = 0.0
    is_balanced: bool = True
    transaction_count: int = 0


class ReconciliationSummaryResponse(BaseModel):
    total_findings: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_domain: dict[str, int] = Field(default_factory=dict)
    ledger: ReconciliationLedgerResponse


class ReconciliationFindingResponse(BaseModel):
    finding_id: str
    domain: str
    severity: str
    source_ids: list[str] = Field(default_factory=list)
    expected: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    resolution: str
    repair_policy: str
    message: str


class ReconciliationReportResponse(BaseModel):
    """KEEP IN SYNC with the reconciliation DTO consumed by future hotel UI."""

    model_config = ConfigDict(populate_by_name=True)
    prop_id: int
    as_of: datetime
    summary: ReconciliationSummaryResponse
    findings: list[ReconciliationFindingResponse] = Field(default_factory=list)


ReconciliationLedgerResponse.model_rebuild()
ReconciliationSummaryResponse.model_rebuild()
ReconciliationFindingResponse.model_rebuild()
ReconciliationReportResponse.model_rebuild()


_require_reconciliation_permission = require_prop_permission("audit.read")


@api_router.get("/summary", response_model=ReconciliationReportResponse)
def reconciliation_summary(
    prop_id: int = Path(..., ge=1),
    current_user: dict = Depends(_require_reconciliation_permission),  # noqa: B008
) -> ReconciliationReportResponse:
    """Return findings for exactly ``prop_id``; never repairs or writes data."""
    if not get_database().dim_hotels.find_one({"prop_id": prop_id}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Hotel no encontrado")
    return ReconciliationReportResponse.model_validate(build_reconciliation_report(prop_id))
