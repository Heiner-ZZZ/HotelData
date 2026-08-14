"""Pydantic models for the Admin module.

Fase #9 (canonical Pydantic v2 *Response convention, line with Fase #5/6/7/8).

The Admin module surfaces two large composite responses — users overview
(for the ``/admin/users`` page) and permissions overview (for the
``/admin/security`` page). Both are produced by helpers ``_serialize_users_overview``
and ``_serialize_permissions_overview`` in ``admin/routes.py`` that build the
dict by composing several Mongo lookups (counts + lists + access buttons).

These helpers are kept as-is. The new ``*Response`` models below wrap the
final dict and pin the wire-shape via Pydantic. Routes call
``UsersOverviewResponse.model_validate(raw_dict)`` or
``PermissionsOverviewResponse.model_validate(raw_dict)`` before returning.

Nested shapes (e.g. ``users[].role_names``, ``roles[].access_buttons``)
remain ``list[dict[str, Any]]`` / ``list[str]`` to keep the helpers'
output un-restricted — the helpers already enforce invariants in code.
Tightening these to typed sub-models is deferred to a follow-up sweep
because it would force a coordinated change across ``admin/service/``.

RULES (canonical from Fase #5/6/7):
- ``model_config = ConfigDict(extra=\"allow\", populate_by_name=True)``
- Primary key ``id`` (when present) uses ``AliasChoices(\"_id\",\"id\")`` + ``serialization_alias=\"id\"``.
- FK fields use a SINGLE alias matching the field name (NOT ``AliasChoices``).
- ``.model_rebuild()`` called on every class.
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from src.app.core.types import ObjectIdStr


# ── Sub-models (typed only at top-level — keep permit-list of optional fields) ──


class UserOverviewItem(BaseModel):
    """One row in the ``users`` array of ``UsersOverviewResponse``.

    The helper flattens many fields from the underlying ``users`` doc plus
    RBAC-computed ones (``is_current_user``, ``can_toggle``,
    ``toggle_label``, ``action_hint``). They are all ``str | bool`` so
    Pydantic coercion is straightforward.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    user_id: str = ""
    username: str = ""
    email: str = ""
    primary_role: str = ""
    role_names: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: str | None = None
    display_name: str = ""
    is_current_user: bool = False
    is_protected: bool = False
    can_toggle: bool = True
    toggle_label: str = "Desactivar"
    action_hint: str = ""


class CurrentUserMini(BaseModel):
    """Embedded ``current_user`` mini-record inside UsersOverviewResponse."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    username: str = ""
    primary_role: str = ""


class AccessButton(BaseModel):
    """One clickable action surfaced in the permissions overview for a role.

    Shape comes from ``_serialize_permissions_overview`` in admin/routes.py:
    each role entry includes a list of access buttons with ``label``, ``href``,
    and ``icon``. Locking the wire-shape prevents regressions when a future
    sweep adds a new field without updating the schema.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    label: str = ""
    href: str = ""
    icon: str = ""


class RolePermissionCodes(BaseModel):
    """Light-typed summary of one role plus its permission codes."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    role_name: str = ""
    description: str = ""
    permission_codes: list[str] = Field(default_factory=list)
    access_buttons: list[AccessButton] = Field(default_factory=list)


class PermissionEntry(BaseModel):
    """One row in the ``permissions`` list of PermissionsOverviewResponse."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    permission_code: str = ""
    description: str = ""


# ── Top-level envelopes ────────────────────────────────────────────────


class UsersOverviewCounters(BaseModel):
    """Aggregate counts surfaced by ``users_overview()`` in admin/service/users.py."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    total: int | None = None
    active: int | None = None
    inactive: int | None = None
    by_role: dict[str, int] | None = None


class UsersOverviewResponse(BaseModel):
    """Composite response for ``GET /api/admin/users`` (and ``/admin/users``)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    counts: UsersOverviewCounters = Field(
        default_factory=UsersOverviewCounters,
    )
    users: list[UserOverviewItem] = Field(default_factory=list)
    current_user: CurrentUserMini = Field(
        default_factory=CurrentUserMini,
    )


class PermissionsOverviewCounters(BaseModel):
    """Aggregate counts surfaced by ``security_overview()`` in admin/service/security.py."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    total_roles: int | None = None
    total_permissions: int | None = None
    nav_items: int | None = None


class PermissionsOverviewResponse(BaseModel):
    """Composite response for ``GET /api/admin/permissions`` (and ``/admin/security``)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    counts: PermissionsOverviewCounters = Field(
        default_factory=PermissionsOverviewCounters,
    )
    roles: list[RolePermissionCodes] = Field(default_factory=list)
    permissions: list[PermissionEntry] = Field(default_factory=list)


class NavigationNodeResponse(BaseModel):
    """One flat node of the sidebar navigation tree (parent refs, no nesting).

    ``get_all_navigation_items()`` returns nodes with camelCase keys; the model
    pins that wire shape and keeps the ObjectId FK as a plain string (already
    stringified by the navigation service)."""

    model_config = ConfigDict(populate_by_name=True)

    slug: str = ""
    parent_slug: str | None = Field(
        default=None, validation_alias="parentSlug", serialization_alias="parentSlug"
    )
    position: int | float = 0
    node_type: str | None = Field(
        default=None, validation_alias="nodeType", serialization_alias="nodeType"
    )
    label: str = ""
    href: str | None = None
    icon: str = ""
    visible: bool = True
    permission_id: str | None = Field(
        default=None, validation_alias="permissionId", serialization_alias="permissionId"
    )
    permission_code: str | None = Field(
        default=None, validation_alias="permissionCode", serialization_alias="permissionCode"
    )
    horizontal_menu: bool = Field(
        default=False, validation_alias="horizontalMenu", serialization_alias="horizontalMenu"
    )


class NavigationResponse(BaseModel):
    """Response for ``GET /api/admin/navigation`` (sidebar tree as flat nodes)."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[NavigationNodeResponse] = Field(default_factory=list)


# ── Explicit rebuilds — ``from __future__ import annotations`` requires
#    eager resolution before the first TypeAdapter binds. Force it.

UserOverviewItem.model_rebuild()
CurrentUserMini.model_rebuild()
UsersOverviewCounters.model_rebuild()
UsersOverviewResponse.model_rebuild()
AccessButton.model_rebuild()
RolePermissionCodes.model_rebuild()
PermissionEntry.model_rebuild()
PermissionsOverviewCounters.model_rebuild()
PermissionsOverviewResponse.model_rebuild()
NavigationNodeResponse.model_rebuild()
NavigationResponse.model_rebuild()
