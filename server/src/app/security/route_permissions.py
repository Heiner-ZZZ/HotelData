from __future__ import annotations


PUBLIC_PREFIXES = (
    "/static",
    "/uploads",
    "/api/hotels",
    "/api/stay/guest",
    "/api/public",
    "/api/amenities/photos",
    "/api/tracking",
)
PUBLIC_PATHS = (
    "/login", "/auth/login", "/api/auth/login",
    "/api/auth/register", "/api/auth/send-code", "/api/auth/confirm-code",
    "/api/auth/register-property/send-code", "/api/auth/register-property/confirm-code",
    "/api/auth/refresh", "/api/auth/me", "/api/auth/status",
    "/api/auth/recover", "/api/auth/reset", "/api/auth/recover/reset",
    "/auth/logout",
)


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


def is_safe_internal_next(next_url: str | None) -> bool:
    if not next_url:
        return False
    return next_url.startswith("/") and not next_url.startswith("//") and "://" not in next_url

