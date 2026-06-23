from __future__ import annotations

from pymongo import IndexModel, ASCENDING

from src.database.collections import ensure_collection


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
