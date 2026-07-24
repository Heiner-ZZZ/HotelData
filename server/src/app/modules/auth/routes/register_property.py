"""Property-owner onboarding: atomic user + property creation.

Two-phase flow that mirrors the regular registration pattern (send-code
→ confirm-code) so the email-verification, retry, and expiry semantics
already battle-tested in `register.py` carry over without divergence.

Phase 1 — `POST /api/auth/register-property/send-code`
    Validates the combined user + property payload, stores it under
    `pending_registrations.pending_property`, and sends a 6-digit
    verification code to the email.

Phase 2 — `POST /api/auth/register-property/confirm-code`
    Verifies the code, allocates the next prop_id via an atomic
    `system_counters` counter (with high-water-mark sync against
    `dim_hotels`), then creates the user (role `hotel_partner`) and
    the new property row. If the dim_hotels insert fails the user is
    rolled back so we never leak orphan accounts.
"""

from __future__ import annotations

import hashlib
import logging
import random
import re
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from src.app.modules.auth.routes._helpers import (
    PENDING_TTL_MINUTES,
    _is_email_available,
    _is_username_available,
    _now,
    _send_property_verification_code,
)
from src.app.security.role_helpers import resolve_role_id
from src.app.security.session import log_user_activity, password_context
from src.database.connection import get_database

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api/auth", tags=["auth-register-property"])

# E.164 allows up to 15 digits; allow optional leading +.
_PHONE_REGEX = re.compile(r"^\+?[1-9]\d{6,14}$")

_PROPERTY_TYPES: tuple[str, ...] = (
    "hotel",
    "hostal",
    "apartamento",
    "bed_breakfast",
    "resort",
    "cabaña",
    "boutique",
)


def _ensure_indexes() -> None:
    """Idempotently ensure `dim_hotels.prop_id` is unique.

    Without this index a duplicate-key error cannot fire on insertion
    and `confirm_property_registration_code` would silently overwrite
    rows. Safe to call at module import time.
    """
    try:
        db = get_database()
        db.dim_hotels.create_index("prop_id", unique=True)
    except Exception as exc:  # pragma: no cover — best-effort index ensure
        logger.debug("dim_hotels unique index check: %s", exc)


_ensure_indexes()


def _validate_property_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize + validate the combined user/property registration payload."""
    email = str(payload.get("email") or "").strip().lower()
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    user_display_name = str(payload.get("user_display_name") or "").strip()

    property_name = str(payload.get("property_name") or "").strip()
    property_type = str(payload.get("property_type") or "").strip().lower()
    phone = str(payload.get("contact_phone") or "").strip()
    country_id = payload.get("country_id")
    city = str(payload.get("city") or "").strip()
    currency = str(payload.get("currency") or "USD").strip().upper()
    total_rooms = payload.get("total_rooms")
    description = str(payload.get("description") or "").strip()

    # ── Account-level validation ──
    if "@" not in email or " " in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Correo electrónico inválido.")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="El usuario debe tener al menos 3 caracteres.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres.")
    if len(user_display_name) > 80:
        raise HTTPException(status_code=400, detail="El nombre visible debe tener máximo 80 caracteres.")

    # ── Property-level validation ──
    if len(property_name) < 2:
        raise HTTPException(status_code=400, detail="El nombre del alojamiento es requerido.")
    if len(property_name) > 120:
        raise HTTPException(status_code=400, detail="El nombre del alojamiento debe tener máximo 120 caracteres.")
    if property_type not in _PROPERTY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de alojamiento inválido. Valores permitidos: {', '.join(_PROPERTY_TYPES)}.",
        )
    if not _PHONE_REGEX.match(phone):
        raise HTTPException(
            status_code=400,
            detail="Número de teléfono inválido. Usa formato internacional (ej. +5215512345678).",
        )
    try:
        country_id_int = int(country_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Selecciona un país válido.")
    if country_id_int <= 0:
        raise HTTPException(status_code=400, detail="Selecciona un país válido.")
    if len(city) < 2:
        raise HTTPException(status_code=400, detail="La ciudad es requerida.")
    if len(currency) != 3 or not currency.isalpha():
        raise HTTPException(status_code=400, detail="Selecciona una moneda válida (código ISO 4217 de 3 letras).")
    try:
        total_rooms_int = int(total_rooms)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="La cantidad de habitaciones debe ser un número entero.")
    if total_rooms_int <= 0:
        raise HTTPException(status_code=400, detail="La cantidad de habitaciones debe ser mayor a 0.")
    if total_rooms_int > 10000:
        raise HTTPException(status_code=400, detail="La cantidad de habitaciones parece demasiado alta.")
    if len(description) > 500:
        raise HTTPException(status_code=400, detail="La descripción no puede superar los 500 caracteres.")

    return {
        "email": email,
        "username": username,
        "password_hash": password_context.hash(password),
        "user_display_name": user_display_name or username,
        "property": {
            "name": property_name,
            "type": property_type,
            "phone": phone,
            "country_id": country_id_int,
            "city": city,
            "currency": currency,
            "total_rooms": total_rooms_int,
            "description": description,
        },
    }


def _validate_country_and_currency(db, country_id: int, currency: str) -> tuple[dict, dict]:
    """Resolve both catalog rows; 400 if either is missing."""
    country = db.dim_visitor_countries.find_one(
        {"visitor_location_country_id": country_id},
        {
            "_id": 0,
            "country_name": 1,
        },
    )
    if not country:
        raise HTTPException(status_code=400, detail="El país seleccionado no existe en el catálogo.")
    cur = db.system_currencies.find_one({"code": currency}, {"_id": 0})
    if not cur or not cur.get("active", True):
        raise HTTPException(status_code=400, detail="La moneda seleccionada no está disponible.")
    return country, cur


def _country_label(country: dict, country_id: int) -> str:
    return (
        country.get("country_name")
        or f"País {country_id}"
    )


def _resolve_geo_country(db, country: dict, country_id: int) -> tuple[str | None, object | None]:
    """Resolve geo_country_code and geo_catalog_id from a dim_visitor_countries doc.

    Matches the country's display name against geo_catalog.type=country entries
    by name (case-insensitive). Returns (geo_country_code, geo_catalog_id) or
    (None, None) if no match found.
    """
    country_name = _country_label(country, country_id).strip().lower()
    if not country_name:
        return None, None
    geo_doc = db.geo_catalog.find_one(
        {"type": "country", "name": {"$regex": f"^{re.escape(country_name)}$", "$options": "i"}},
        {"code": 1},
    )
    if geo_doc:
        return geo_doc.get("code"), geo_doc["_id"]
    return None, None


def _next_prop_id(db) -> int:
    """Allocate the next prop_id atomically with high-water-mark sync.

    Race-safety:
      • `find_one_and_update` + `$inc` is the canonical MongoDB atomic
        increment; concurrent calls never return the same value.
      • After the increment we sync against the actual high-water-mark
        from `dim_hotels` so seeds / backfills / manual inserts can't
        cause collisions.
      • If two registrations both attempt the same prop_id (extremely
        narrow window between the increment and the dim_hotels insert),
        the duplicate-key fallback in the caller rolls the user back
        cleanly.
    """
    max_doc = db.dim_hotels.find_one(
        sort=[("prop_id", -1)],
        projection={"prop_id": 1, "_id": 0},
    )
    max_existing = max_doc["prop_id"] if max_doc else 0

    counter = db.system_counters.find_one_and_update(
        {"_id": "prop_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    proposed = counter["seq"]

    if proposed <= max_existing:
        bumped = db.system_counters.find_one_and_update(
            {"_id": "prop_id"},
            {"$set": {"seq": max_existing + 1}},
            return_document=ReturnDocument.AFTER,
        )
        return bumped["seq"] if bumped else max_existing + 1

    return proposed


@api_router.post("/register-property/send-code")
def send_property_registration_code(
    request: Request,
    payload: dict = Body(...),
):
    clean = _validate_property_payload(payload)
    db = get_database()

    if not _is_username_available(db, clean["username"]):
        raise HTTPException(status_code=400, detail="Este nombre de usuario ya está registrado.")
    if not _is_email_available(db, clean["email"]):
        raise HTTPException(status_code=400, detail="Este correo ya está asociado a una cuenta activa.")

    _validate_country_and_currency(db, clean["property"]["country_id"], clean["property"]["currency"])

    code = f"{random.randint(0, 999999):06d}"
    now = _now()

    pending = {
        "email": clean["email"],
        "username": clean["username"],
        "password_hash": clean["password_hash"],
        "display_name": clean["user_display_name"],
        "code_hash": hashlib.sha256(code.encode("utf-8")).hexdigest(),
        "attempts": 0,
        "created_at": now,
        "expires_at": now + timedelta(minutes=PENDING_TTL_MINUTES),
        "pending_property": clean["property"],
    }
    db.pending_registrations.replace_one(
        {"email": clean["email"]},
        pending,
        upsert=True,
    )

    _send_property_verification_code(clean["email"], clean["user_display_name"], code)

    log_user_activity(
        db,
        action="auth.register_property.send_code",
        request=request,
        details={
            "email": clean["email"],
            "property_name": clean["property"]["name"],
            "property_type": clean["property"]["type"],
        },
    )

    return {
        "ok": True,
        "email": clean["email"],
        "message": (
            f"Te enviamos un código de verificación a {clean['email']}. "
            "Revisa tu bandeja de entrada."
        ),
    }


@api_router.post("/register-property/confirm-code")
def confirm_property_registration_code(
    request: Request,
    payload: dict = Body(...),
):
    email = str(payload.get("email") or "").strip().lower()
    code = str(payload.get("code") or "").strip()

    if not email or not code:
        raise HTTPException(status_code=400, detail="email y code son requeridos.")
    if len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=400, detail="El código debe tener 6 dígitos.")

    db = get_database()
    pending = db.pending_registrations.find_one({"email": email})
    if not pending or not pending.get("pending_property"):
        raise HTTPException(
            status_code=404,
            detail=(
                "No hay un registro de alojamiento pendiente para este correo. "
                "Solicita un nuevo código desde el formulario."
            ),
        )

    from src.app.security.session import ensure_utc

    expires_at = ensure_utc(pending.get("expires_at"))
    if expires_at and expires_at < _now():
        db.pending_registrations.delete_one({"email": email})
        raise HTTPException(status_code=400, detail="El código expiró. Solicita un nuevo registro.")

    if pending["attempts"] >= 5:
        db.pending_registrations.delete_one({"email": email})
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos fallidos. Solicita un nuevo código.",
        )

    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    if code_hash != pending["code_hash"]:
        db.pending_registrations.update_one(
            {"email": email},
            {"$inc": {"attempts": 1}},
        )
        remaining = 4 - pending["attempts"]
        raise HTTPException(
            status_code=400,
            detail=f"Código incorrecto. Te quedan {remaining} intento(s).",
        )

    pending_property = pending["pending_property"]

    # ── Atomic creation: country/currency → user → dim_hotels → audit ──
    country, _currency = _validate_country_and_currency(
        db, pending_property["country_id"], pending_property["currency"]
    )
    country_label = _country_label(country, pending_property["country_id"])
    geo_country_code, geo_catalog_id = _resolve_geo_country(db, country, pending_property["country_id"])
    now = _now()
    prop_id = _next_prop_id(db)

    user_doc = {
        "username": pending["username"],
        "email": pending["email"],
        "password_hash": pending["password_hash"],
        "display_name": pending["display_name"] or pending["username"],
        "primary_role_id": resolve_role_id("hotel_partner"),
        "is_active": True,
        "email_verified": True,
        "failed_login_attempts": 0,
        "locked_until": None,
        "assigned_prop_id": prop_id,
        "created_at": now,
        "updated_at": now,
    }
    try:
        user_result = db.users.insert_one(user_doc)
    except DuplicateKeyError:
        db.pending_registrations.delete_one({"email": email})
        raise HTTPException(
            status_code=400,
            detail="El usuario o correo ya está registrado.",
        )
    user_id = user_result.inserted_id

    hotel_doc = {
        "prop_id": prop_id,
        "hotel_name": pending_property["name"],
        "name_source": "onboarding_register",
        "display_name": pending_property["name"],
        "description": pending_property.get("description", ""),
        "display_country_label": country_label,
        "prop_country_id": pending_property["country_id"],
        "geo_country_code": geo_country_code,
        "geo_catalog_id": geo_catalog_id,
        "currency": pending_property["currency"],
        "accepted_currencies": [pending_property["currency"]],
        "manual_override": True,
        "verified_at": now,
        "contact_phone": pending_property["phone"],
        "property_type": pending_property["type"],
        "city": pending_property["city"],
        "total_rooms_declared": pending_property["total_rooms"],
        "owner_user_id": user_id,
        "owner_username": pending["username"],
        "created_at": now,
        "updated_at": now,
    }
    try:
        db.dim_hotels.insert_one(hotel_doc)
    except DuplicateKeyError:
        db.users.delete_one({"_id": user_id})
        db.pending_registrations.delete_one({"email": email})
        logger.warning(
            "Duplicate prop_id collision during onboarding for email=%s prop_id=%s",
            email,
            prop_id,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "El sistema generó un identificador duplicado. "
                "Intenta el registro nuevamente."
            ),
        )
    except Exception as exc:
        db.users.delete_one({"_id": user_id})
        db.pending_registrations.delete_one({"email": email})
        logger.exception("Failed to create dim_hotels row during onboarding: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="No se pudo crear el alojamiento. Intenta nuevamente.",
        )

    db.hotel_profile_changes.insert_one({
        "prop_id": prop_id,
        "field": "onboarding.register",
        "old_value": None,
        "new_value": pending_property["name"],
        "changed_by": pending["username"],
        "changed_at": now,
        "reason": "Registro inicial de alojamiento vía onboarding público",
        "source": "register_property_wizard",
    })

    db.pending_registrations.delete_one({"email": email})

    log_user_activity(
        db,
        action="auth.register_property.confirmed",
        request=request,
        user=user_doc,
        details={
            "email": email,
            "prop_id": prop_id,
            "property_name": pending_property["name"],
            "property_type": pending_property["type"],
        },
    )

    return {
        "ok": True,
        "requires_login": True,
        "prop_id": prop_id,
        "email": email,
        "message": (
            f"Tu alojamiento «{pending_property['name']}» fue registrado correctamente. "
            "Inicia sesión para acceder a tu panel de gestión."
        ),
    }
