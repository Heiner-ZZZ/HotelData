"""Shared Pydantic v2 type aliases for the application.

Centralizes the ObjectId → string serialization pattern so individual
routes don't need to manually call ``str(doc["_id"])`` in every
response. Without this, FastAPI's default serializer would emit
``{"$oid": "..."}`` for raw ObjectId fields, which the frontend cannot
parse as a plain string.

Usage::

    from src.app.core.types import ObjectIdStr

    class HotelProductResponse(BaseModel):
        id: ObjectIdStr  # ← ObjectId | str | None auto-coerced to str | None
        prop_id: int
        name: str


How it works
------------
``ObjectIdStr`` is annotated as ``str`` with a ``BeforeValidator`` that
runs **before** Pydantic's normal type validation. The validator:

1.  Returns ``None`` unchanged so optional fields work.
2.  Coerces ``bson.ObjectId`` instances to ``str``.
3.  Coerces any other value through ``str()`` (idempotent on strings).

This single alias handles the 34+ ``str(doc["_id"])`` call sites
scattered across the codebase. New endpoints can adopt it by declaring
``response_model=List[HotelProductResponse]`` and using ``ObjectIdStr``
in the Pydantic model — no service-layer changes required.
"""

from __future__ import annotations

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


# Type alias for response models. Use as:
#   class MyResponse(BaseModel):
#       id: ObjectIdStr
#       parent_id: ObjectIdStr | None = None
ObjectIdStr = Annotated[str, BeforeValidator(_serialize_object_id)]
