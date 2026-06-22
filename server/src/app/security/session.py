from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from passlib.context import CryptContext
from pymongo.database import Database
from starlette.requests import Request


SESSION_COOKIE_NAME = "hoteldata_session"
SESSION_TTL_HOURS = 8

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, password_hash: str) -> bool:
    if not plain_password or not password_hash:
        return False
    return password_context.verify(plain_password, password_hash)


def find_user_by_identifier(db: Database, identifier: str) -> dict[str, Any] | None:
    normalized = identifier.strip()
    if not normalized:
        return None
    return db.users.find_one(
        {
            "$or": [
                {"email": normalized},
                {"email": normalized.lower()},
                {"username": normalized},
            ]
        }
    )


def create_user_session(db: Database, user: dict[str, Any], request: Request) -> str:
    token = secrets.token_urlsafe(48)
    token_hash = hash_session_token(token)
    now = utc_now()
    expires_at = now + timedelta(hours=SESSION_TTL_HOURS)
    db.user_sessions.insert_one(
        {
            "session_token_hash": token_hash,
            "user_id": user["_id"],
            "username": user.get("username"),
            "email": user.get("email"),
            "is_active": True,
            "created_at": now,
            "expires_at": expires_at,
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
    )
    return token


def ensure_user_sessions_indexes(db: Database) -> None:
    """Create the indexes required by the session store. Idempotent.

    Called from the FastAPI `lifespan` so we don't pay the cost of
    `create_index` on every login (was previously inside
    `create_user_session`).

    Indexes:
    - `session_token_hash`: unique lookup for session resolution.
    - `expires_at`: TTL index so MongoDB automatically removes expired
      session documents (RNF-002 / CA-007).
    """
    db.user_sessions.create_index("session_token_hash", unique=True, sparse=True)
    db.user_sessions.create_index("expires_at", expireAfterSeconds=0)


def ensure_users_indexes(db: Database) -> None:
    """Create unique indexes on users collection to prevent duplicates."""
    db.users.create_index("email", unique=True)
    db.users.create_index("username", unique=True)


def get_session(db: Database, token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    session = db.user_sessions.find_one({"session_token_hash": hash_session_token(token), "is_active": True})
    if not session:
        return None
    expires_at = session.get("expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < utc_now():
        db.user_sessions.update_one(
            {"_id": session["_id"]},
            {"$set": {"is_active": False, "ended_at": utc_now(), "end_reason": "expired"}},
        )
        return None
    return session


def get_current_user(db: Database, token: str | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    session = get_session(db, token)
    if not session:
        return None, None
    user_id = session.get("user_id")
    if isinstance(user_id, str):
        try:
            user_id = ObjectId(user_id)
        except Exception:
            return None, session
    user = db.users.find_one({"_id": user_id, "is_active": True})
    return user, session


def invalidate_session(db: Database, token: str | None, reason: str = "logout") -> dict[str, Any] | None:
    session = get_session(db, token)
    if not session:
        return None
    db.user_sessions.update_one(
        {"_id": session["_id"]},
        {"$set": {"is_active": False, "ended_at": utc_now(), "end_reason": reason}},
    )
    return session


def invalidate_user_sessions(db: Database, user_id: ObjectId | str, reason: str = "new_login") -> int:
    """Mark all active sessions for a user as inactive.

    Called before creating a new session on login so that each user
    has at most one active session at any time (RN-004).

    Args:
        reason: Reason for invalidation ("new_login", "password_changed", etc.)
    """
    uid = user_id
    if isinstance(uid, str):
        try:
            uid = ObjectId(uid)
        except Exception:
            return 0
    result = db.user_sessions.update_many(
        {"user_id": uid, "is_active": True},
        {"$set": {"is_active": False, "ended_at": utc_now(), "end_reason": reason}},
    )
    return result.modified_count


def log_user_activity(
    db: Database,
    *,
    action: str,
    request: Request,
    user: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    db.user_activity_logs.insert_one(
        {
            "user_id": user.get("_id") if user else None,
            "username": user.get("username") if user else None,
            "email": user.get("email") if user else None,
            "action": action,
            "module": "auth",
            "details": details or {},
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "created_at": utc_now(),
        }
    )
