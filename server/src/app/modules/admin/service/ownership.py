from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from passlib.context import CryptContext
from pymongo import ASCENDING

from src.app.security.role_helpers import resolve_role_id, build_role_query
from src.database.connection import get_database

from ._helpers import utc_now

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

HOTEL_ROLES = ("hotel_partner", "gerente_hotel", "revenue_manager", "marketing_hotelero", "maintenance")


def _serialize(value: Any) -> Any:
    """Recursively convert MongoDB types to JSON-safe types."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    return value


def _clean_user(user: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(user)
    cleaned.pop("password_hash", None)
    if "_id" in cleaned:
        cleaned["user_id"] = str(cleaned.pop("_id"))
    if "assigned_hotels" not in cleaned or not cleaned["assigned_hotels"]:
        cleaned["assigned_hotels"] = []
    # Serialize remaining MongoDB types (ObjectId in role_ids, datetime, etc.)
    return _serialize(cleaned)  # type: ignore[return-value]


def _resolve_hotel_names(prop_ids: list[int]) -> list[dict[str, Any]]:
    if not prop_ids:
        return []
    db = get_database()
    hotels = list(
        db.dim_hotels.find(
            {"prop_id": {"$in": prop_ids}},
            {"_id": 0, "prop_id": 1, "display_name": 1, "hotel_name": 1, "prop_country_id": 1},
        )
    )
    lookup = {int(h["prop_id"]): h for h in hotels if h.get("prop_id") is not None}
    result = []
    for pid in prop_ids:
        h = lookup.get(pid)
        if h:
            label = h.get("display_name") or h.get("hotel_name") or f"Hotel {pid}"
            result.append({"prop_id": pid, "label": label, "country_id": h.get("prop_country_id")})
        else:
            result.append({"prop_id": pid, "label": f"Hotel {pid} (sin nombre)", "country_id": None})
    return result


def list_ownership_users() -> list[dict[str, Any]]:
    db = get_database()
    users = (
        db.users.find(
            build_role_query(list(HOTEL_ROLES)),
            {"password_hash": 0},
        )
        .sort("created_at", -1)
    )
    result = []
    for user in users:
        cleaned = _clean_user(user)
        assigned = cleaned.get("assigned_hotels", [])
        hotel_names = _resolve_hotel_names(assigned)
        cleaned["hotel_count"] = len(assigned)
        cleaned["hotel_preview"] = [h["label"] for h in hotel_names[:3]]
        cleaned["hotel_overflow"] = max(0, len(assigned) - 3)
        result.append(cleaned)
    return result


def get_ownership_user(user_id: str) -> dict[str, Any] | None:
    db = get_database()
    try:
        oid = ObjectId(user_id)
    except InvalidId:
        return None
    user = db.users.find_one({"_id": oid}, {"password_hash": 0})
    if not user:
        return None
    cleaned = _clean_user(user)
    assigned = cleaned.get("assigned_hotels", [])
    cleaned["hotels"] = _resolve_hotel_names(assigned)
    return cleaned


def create_ownership_user(
    username: str,
    email: str,
    password: str,
    primary_role: str,
    display_name: str = "",
    assigned_hotels: list[int] | None = None,
) -> dict[str, Any]:
    db = get_database()

    if primary_role not in HOTEL_ROLES:
        return {"ok": False, "message": f"Rol no válido. Debe ser uno de: {', '.join(HOTEL_ROLES)}"}

    existing = db.users.find_one({"$or": [{"username": username}, {"email": email}]})
    if existing:
        return {"ok": False, "message": "El username o email ya está registrado."}

    if len(password) < 6:
        return {"ok": False, "message": "La contraseña debe tener al menos 6 caracteres."}

    # Security: los roles de hotel SIEMPRE requieren assigned_hotels. Escribir
    # [] deja al usuario con alcance ilimitado (hotel_filter trata vacío como
    # sin restricción → vería todos los hoteles del sistema).
    try:
        hotels = [int(h) for h in (assigned_hotels or [])]
    except (TypeError, ValueError):
        hotels = []
    if not hotels:
        return {
            "ok": False,
            "message": "Debe asignar al menos un hotel al crear un usuario con rol de hotel.",
        }

    now = utc_now()
    user_doc: dict[str, Any] = {
        "username": username,
        "email": email,
        "password_hash": password_context.hash(password),
        "display_name": display_name or username,
        # Keep the transitional role fields synchronized: permission checks
        # prefer the FK, while legacy readers still consume primary_role.
        "primary_role": primary_role,
        "primary_role_id": resolve_role_id(primary_role),
        "is_active": True,
        "assigned_hotels": hotels,
        "failed_login_attempts": 0,
        "locked_until": None,
        "created_at": now,
        "updated_at": now,
    }

    try:
        result = db.users.insert_one(user_doc)
    except Exception as e:
        return {"ok": False, "message": f"Error al crear usuario: {str(e)}"}

    user_doc["_id"] = result.inserted_id
    cleaned = _clean_user(user_doc)
    cleaned["hotels"] = _resolve_hotel_names(user_doc.get("assigned_hotels", []))

    db.user_activity_logs.insert_one({
        "user_id": result.inserted_id,
        "username": username,
        "action": "admin.user_created",
        "module": "admin",
        "details": {"primary_role": primary_role, "assigned_hotels": assigned_hotels or []},
        "created_at": now,
    })

    return {"ok": True, "message": f"Usuario {username} creado correctamente.", "user": cleaned}


def update_assigned_hotels(user_id: str, assigned_hotels: list[int]) -> dict[str, Any]:
    db = get_database()
    try:
        oid = ObjectId(user_id)
    except InvalidId:
        return {"ok": False, "message": "ID de usuario inválido."}

    user = db.users.find_one({"_id": oid})
    if not user:
        return {"ok": False, "message": "Usuario no encontrado."}

    # Security: vaciar assigned_hotels en un rol con filtro NO revoca acceso —
    # hotel_filter trata la lista vacía como "sin restricción" (vería todos
    # los hoteles). Para revocar el acceso se desactiva/elimina el usuario.
    try:
        hotels = [int(h) for h in (assigned_hotels or [])]
    except (TypeError, ValueError):
        hotels = []
    if not hotels:
        return {
            "ok": False,
            "message": "No puede dejar a un usuario de hotel sin hoteles asignados. "
            "Para revocar su acceso, desactívelo o elimínelo.",
        }

    db.users.update_one(
        {"_id": oid},
        {"$set": {"assigned_hotels": hotels, "updated_at": utc_now()}},
    )

    hotel_names = _resolve_hotel_names(assigned_hotels)
    return {
        "ok": True,
        "message": f"Hoteles asignados actualizados ({len(assigned_hotels)} hoteles).",
        "hotels": hotel_names,
    }


def search_hotels(query: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
    db = get_database()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)
    query = query.strip()

    filters: dict[str, Any] = {}
    if query:
        query_as_int: int | None = None
        try:
            query_as_int = int(query)
        except (ValueError, TypeError):
            pass

        filters["$or"] = [
            {"display_name": {"$regex": query, "$options": "i"}},
            {"hotel_name": {"$regex": query, "$options": "i"}},
            {"display_country_label": {"$regex": query, "$options": "i"}},
        ]
        if query_as_int is not None:
            filters["$or"].append({"prop_id": query_as_int})

    total = db.dim_hotels.count_documents(filters)
    total_pages = (total + page_size - 1) // page_size if total else 0

    cursor = (
        db.dim_hotels.find(filters, {"_id": 0})
        .sort([("prop_id", ASCENDING)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    items = []
    for hotel in cursor:
        prop_id = hotel.get("prop_id")
        label = (
            hotel.get("display_name")
            or hotel.get("display_name")
            or hotel.get("hotel_name")
            or f"Hotel {prop_id}"
        )
        items.append({
            "prop_id": prop_id,
            "label": label,
            "hotel_name": hotel.get("hotel_name"),
            "display_name": hotel.get("display_name"),
            "star_rating": hotel.get("prop_starrating"),
            "country_id": hotel.get("prop_country_id"),
            "country_label": hotel.get("display_country_label"),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


def get_roles_list() -> list[dict[str, Any]]:
    db = get_database()
    roles = list(
        db.roles.find(
            {"role_name": {"$in": list(HOTEL_ROLES)}},
            {"_id": 0, "role_name": 1, "description": 1},
        ).sort("role_name", ASCENDING)
    )
    return roles
