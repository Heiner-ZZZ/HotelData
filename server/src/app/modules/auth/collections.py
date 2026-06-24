from __future__ import annotations

from pymongo import IndexModel, ASCENDING, DESCENDING

from src.database.collections import ensure_collection

# Retain user activity logs for 180 days (≈6 months) before auto-cleanup.
USER_ACTIVITY_TTL_SECONDS = 180 * 24 * 60 * 60


def ensure_auth_collections() -> None:
    ensure_collection("password_recovery_tokens", [
        IndexModel([("token_hash", ASCENDING)], name="idx_recovery_token", unique=True, sparse=True),
        IndexModel([("expires_at", ASCENDING)], name="idx_recovery_expires", expireAfterSeconds=0),
    ])
    ensure_collection("two_factor_codes", [
        IndexModel([("user_id", ASCENDING), ("code", ASCENDING)], name="idx_2fa_user_code"),
        IndexModel([("expires_at", ASCENDING)], name="idx_2fa_expires", expireAfterSeconds=0),
    ])
    ensure_collection("user_2fa", [
        IndexModel([("user_id", ASCENDING)], name="idx_2fa_user", unique=True),
    ])
    ensure_collection("email_verification_tokens", [
        IndexModel([("token_hash", ASCENDING)], name="idx_email_verify_token", unique=True, sparse=True),
        IndexModel([("expires_at", ASCENDING)], name="idx_email_verify_expires", expireAfterSeconds=0),
    ])
    ensure_collection("refresh_tokens", [
        IndexModel([("token_hash", ASCENDING)], name="idx_refresh_token", unique=True, sparse=True),
        IndexModel([("expires_at", ASCENDING)], name="idx_refresh_expires", expireAfterSeconds=0),
    ])
    ensure_collection("user_activity_logs", [
        IndexModel([("event_key", ASCENDING)], name="idx_activity_event", unique=True, sparse=True),
        IndexModel([("created_at", DESCENDING)], name="idx_activity_created"),
        IndexModel([("created_at", ASCENDING)], name="idx_activity_ttl", expireAfterSeconds=USER_ACTIVITY_TTL_SECONDS),
        IndexModel([("action", ASCENDING)], name="idx_activity_action"),
        IndexModel([("user_id", ASCENDING)], name="idx_activity_user"),
    ])
