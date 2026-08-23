"""Helpers compartidos para los tests funcionales de Migración E (prop-gate).

Seeds de catálogo, usuarios, roles de hotel y hoteles. Archivo helper (no
coleccionado por pytest: empieza con ``_``).
"""
from __future__ import annotations

from datetime import UTC, datetime

from bson import ObjectId
from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def now() -> datetime:
    return datetime.now(UTC)


def seed_catalog(db, codes: list[str]) -> None:
    for code in codes:
        db.permissions.insert_one(
            {"permission_code": code, "description": code, "is_system": True,
             "created_at": now(), "updated_at": now()}
        )


def seed_hotel(db, prop_id: int) -> None:
    db.dim_hotels.insert_one(
        {
            "prop_id": prop_id,
            "hotel_name": f"Hotel {prop_id}",
            "display_name": f"Hotel {prop_id}",
            "prop_starrating": 4.0,
            "prop_review_score": 8.0,
        }
    )


def seed_user(db, *, username: str, role: str, permissions: list[str],
              assigned_hotels: list[int] | None = None) -> dict[str, str]:
    db.roles.insert_one(
        {
            "role_name": role,
            "display_name": role.replace("_", " ").title(),
            "permissions": permissions,
            "is_system": True,
            "created_at": now(),
        }
    )
    user_id = db.users.insert_one(
        {
            "username": username,
            "email": f"{username}@hotel.local",
            "display_name": username.replace("_", " ").title(),
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": role,
            "role_ids": [],
            "assigned_hotels": assigned_hotels if assigned_hotels is not None else [],
            "is_active": True,
            "created_at": now(),
        }
    ).inserted_id
    return {"user_id": str(user_id), "username": username, "password": "Pass123!"}


def seed_hotel_role(db, *, prop_id: int = 1, name: str = "rol_hotel_prop",
                    permissions: list[str]) -> ObjectId:
    return db.hotel_roles.insert_one(
        {
            "prop_id": prop_id,
            "name": name,
            "display_name": name.replace("_", " ").title(),
            "permissions": permissions,
            "is_active": True,
            "created_at": now(),
            "updated_at": now(),
        }
    ).inserted_id


async def login(client, creds: dict[str, str]) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": creds["username"], "password": creds["password"]},
    )
    assert resp.status_code == 200, resp.text
