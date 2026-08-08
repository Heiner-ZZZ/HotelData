"""Approval gate for hotel-owner onboarding (UX-1, docs/EXPERIENCIA_DUENO_PENDIENTE.md).

The owner's account is born with ``approval_status != "approved"`` (pending,
changes_requested or rejected). While not approved, the session is RESTRICTED:
the middleware only lets through the paths below (the owner can see their
registration status and edit their submitted data) and returns 403 with
``code: approval_pending`` / ``approval_rejected`` for everything else.

Also implements the LAZY rejection grace: when a registration is rejected the
account stays active (``is_active: true``) so the owner can see the reason
once in the app. After ``REJECTION_GRACE_DAYS`` the first interaction
(login or any middleware request) deactivates the account and invalidates its
sessions — no background job needed.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo.database import Database

from src.app.security.session import invalidate_user_sessions, utc_now

# Paths a non-approved owner may reach. Everything else → 403.
APPROVAL_ALLOWLIST = (
    "/api/auth/me",
    "/api/auth/status",
    "/api/auth/registration-status",
    "/api/auth/register-property/me",  # PATCH: edit + resubmit (pending/changes_requested)
    "/auth/me",
    "/api/auth/logout",
    "/auth/logout",
)

# Nota: /api/auth/me, /api/auth/status y /auth/logout ya están en
# PUBLIC_PATHS/PUBLIC_PREFIXES (short-circuit antes del gate) — se mantienen
# aquí por fidelidad a la spec y como red de seguridad si algún día dejan de
# ser públicas.

# Rejection grace window before the account is hard-deactivated.
# Configurable via env so ops can shorten/extend without code changes.
DEFAULT_REJECTION_GRACE_DAYS = 7


def rejection_grace_days() -> int:
    raw = os.getenv("REJECTION_GRACE_DAYS", str(DEFAULT_REJECTION_GRACE_DAYS))
    try:
        return max(int(raw), 1)
    except (TypeError, ValueError):
        return DEFAULT_REJECTION_GRACE_DAYS


def is_approval_allowlisted(path: str) -> bool:
    """True when a non-approved owner may reach *path*."""
    return path in APPROVAL_ALLOWLIST


def approval_gate_code(approval_status: str | None) -> str:
    """Distinct 403 codes so the UI can differentiate pending vs rejected."""
    return "approval_rejected" if approval_status == "rejected" else "approval_pending"


def maybe_apply_rejection_grace(db: Database, user: dict) -> bool:
    """Lazily enforce the rejection grace window.

    When ``user.approval_status == "rejected"`` and ``rejected_at`` is older
    than ``REJECTION_GRACE_DAYS``, deactivate the account and invalidate all
    its sessions. Returns True when the deactivation happened (the caller
    should treat the request as unauthenticated / fail the login).

    Idempotent: once ``is_active`` is False the user won't even be resolved
    by ``get_current_user``, so this only ever runs once per account.
    """
    if not user or user.get("approval_status") != "rejected":
        return False
    rejected_at = user.get("rejected_at")
    if not rejected_at:
        return False
    if isinstance(rejected_at, str):
        try:
            rejected_at = datetime.fromisoformat(rejected_at.replace("Z", "+00:00"))
        except ValueError:
            return False
    if rejected_at.tzinfo is None:
        rejected_at = rejected_at.replace(tzinfo=timezone.utc)

    if rejected_at + timedelta(days=rejection_grace_days()) > utc_now():
        return False

    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"is_active": False, "updated_at": utc_now()}},
    )
    user_id = user["_id"]
    if isinstance(user_id, str):
        try:
            user_id = ObjectId(user_id)
        except Exception:  # pragma: no cover — defensive
            pass
    invalidate_user_sessions(db, user_id, reason="hotel_rejected")
    return True
