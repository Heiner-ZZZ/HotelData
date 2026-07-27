"""Shared Pydantic v2 type aliases for the application.

Centralizes the ObjectId → string serialization pattern so individual
routes don't need to manually call ``str(doc["_id"])`` in every
response. Without this, FastAPI's default serializer would emit
``{"$oid": "..."}`` for raw ObjectId fields, which the frontend cannot
parse as a plain string.

Usage::

    from src.app.core.types import ObjectIdStr, ListToCommaStr

    class HotelProductResponse(BaseModel):
        id: ObjectIdStr           # ← ObjectId | str | None auto-coerced to str | None
        special_requests: ListToCommaStr | None = None  # ← list[str] | str | None → str


How it works
------------
``ObjectIdStr`` is annotated as ``str`` with a ``BeforeValidator`` that
runs **before** Pydantic's normal type validation. The validator:

1.  Returns ``None`` unchanged so optional fields work.
2.  Coerces ``bson.ObjectId`` instances to ``str``.
3.  Coerces any other value through ``str()`` (idempotent on strings).

``ListToCommaStr`` runs the symmetric pattern for fields that historically
were stored as Mongo arrays but are exposed to the frontend as a flat
string. It auto-joins ``list[str]`` into a comma-separated string so
consumers can safely call ``str.lower()`` / ``str.split()`` without
having to first detect the array shape.

This pair handles the 34+ ``str(doc["_id"])`` call sites scattered
across the codebase + the recent FK-by-ObjectId migration (where
``prop_id`` may be ObjectId OR int) + the special_requests array→str
canonicalization. New endpoints can adopt them by using the typed
aliases — no service-layer migration needed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from bson import ObjectId
from pydantic import BeforeValidator


def _serialize_object_id(v: Any) -> str | None:
    """Coerce MongoDB ObjectId (or its string form) to a plain string.

    Strict mode — rejects unknown types with ``ValueError`` instead of
    silently coercing via ``str()``. This catches bugs at the source
    (e.g. accidentally passing a dict like ``{"$oid": "..."}`` or a
    datetime that would otherwise appear as ``"{'$oid': '...'}"`` or
    ``"2024-01-01 ..."`` on the wire).

    Returns ``None`` unchanged so it can be used for optional FK fields
    when the annotation is ``ObjectIdStr | None``.

    Allowed inputs:
        - ``None``        → passes through (for optional fields)
        - ``bson.ObjectId`` → coerced via ``str()``
        - ``str``         → passed through unchanged (no double-encoding)
    """
    if v is None:
        return None
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str):
        return v
    raise ValueError(
        f"ObjectIdStr expected ObjectId or str, got {type(v).__name__}"
    )


def _join_list_to_str(v: Any) -> Any:
    """Coerce ``list[str]`` (or ``list[Any]``) to a single comma-separated string.

    Used by ``ListToCommaStr`` for Mongo-native fields that historically
    came in as arrays (e.g. ``special_requests`` post-FK-migration) but
    were historically exposed as a flat string to the frontend. Keeps
    callers using ``str.lower()`` / ``str.split()`` safe without forcing
    every consumer to learn about the array shape.

    Allowed inputs:
        - ``None``            → passes through (for optional fields)
        - ``list``            → ``", ".join(str(i) for i in v if i)``
        - ``str`` (or other)  → passes through unchanged
    """
    if v is None:
        return None
    if isinstance(v, list):
        return ", ".join(str(i) for i in v if i)
    return v


# Type alias for response models. Use as:
#   class MyResponse(BaseModel):
#       id: ObjectIdStr
#       parent_id: ObjectIdStr | None = None
ObjectIdStr = Annotated[str, BeforeValidator(_serialize_object_id)]


# Type alias for fields whose Mongo shape is a ``list[str]`` but whose
# wire shape is a flat comma-separated string. Pydantic runs this
# BeforeValidator BEFORE its own type-coercion so the result
# (``str | None``) passes the ``Annotated[str, ...]`` slot it stands in
# for. Use as:
#   class BookingResponse(BaseModel):
#       special_requests: ListToCommaStr | None = None
ListToCommaStr = Annotated[str, BeforeValidator(_join_list_to_str)]


def to_json_safe(value: Any) -> Any:
    """Recursively serialize MongoDB-native types into JSON-safe primitives.

    Public helper for routes/payloads that need belt-and-suspenders
    defenses BEFORE calling ``SomeResponse.model_validate(...)``. The
    canonical use is at API boundaries where it is safer to pre-clean
    the input than to depend solely on a service-layer wrap that may
    not have propagated (e.g. after WatchFiles reloads, stale .pyc,
    or a service function imported from outside its own module).

    Handles:
    - ``None`` -> passthrough
    - ``bson.ObjectId`` -> ``str``
    - ``datetime.datetime`` -> ``isoformat()``
    - ``bson.DatetimeMS`` (some pymongo builds) -> ``isoformat()`` via ``str``
    - ``dict`` -> walk values
    - ``list``/``tuple``/``set`` -> walk items
    - other types (int / float / bool / plain str) -> passthrough

    The function is INTENTIONALLY TOLERANT (extra Mongo-like types
    are ``str()``-coerced silently) to avoid surprise 500s on edge
    cases like ``bson.DatetimeMS``, ``bson.regex.Regex``, ``bson.binary.Binary``.
    """
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    # bson.DatetimeMS (some pymongo versions) is NOT an isinstance subclass
    # of datetime.datetime — fall back to str() which formats to ISO via its
    # __str__ method. Likewise guard against future mongo-like wrapper types.
    type_name = type(value).__name__
    if type_name in ("DatetimeMS", "Int64", "Binary"):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return {k: to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_json_safe(v) for v in value]
    return value  # int / float / bool / etc. — already JSON-safe


# Backwards-compat alias for callers that may already import ``json_safe``.
json_safe = to_json_safe  # noqa: E305 — intentional public re-export
