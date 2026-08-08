"""Unit tests for the navigation-preview permission filter.

``_filter_preview_codes`` decides which selected codes survive into the
navigation preview payload of ``POST /api/admin/permissions/preview``. It
must drop CRUD codes whose ``<resource>.read`` sibling does not exist in the
catalog (a grant that would produce a dead navigation item), while KEEPING
compound codes like ``hotel.manage_roles`` that are complete permissions on
their own (they are the only code behind the "Equipo y permisos" nav item).
"""

from src.app.modules.admin.routes import _filter_preview_codes


def test_keeps_compound_permission_without_read_sibling() -> None:
    """``hotel.manage_roles`` must survive even though ``hotel.read`` is not
    a catalog code (regression: the preview hid "Equipo y permisos" after any
    edit because the old filter dropped it)."""
    available = {"hotel.manage_roles", "users.read", "users.update", "etl.read", "etl.execute"}
    codes = {"hotel.manage_roles", "users.update", "etl.execute"}
    result = _filter_preview_codes(codes, available)
    assert "hotel.manage_roles" in result
    assert "users.update" in result
    assert "etl.execute" in result


def test_keeps_read_and_wildcard() -> None:
    available = {"users.read", "users.update"}
    result = _filter_preview_codes({"*.*", "users.read"}, available)
    assert result == {"*.*", "users.read"}


def test_drops_crud_action_without_read_sibling() -> None:
    """A CRUD action whose resource has no ``.read`` in the catalog is not
    grantable and must be filtered out of the preview."""
    available = {"users.read", "users.update"}
    result = _filter_preview_codes({"users.update", "foo.update", "foo.manage"}, available)
    assert "users.update" in result
    assert "foo.update" not in result
    assert "foo.manage" not in result


def test_keeps_crud_action_when_read_sibling_exists() -> None:
    available = {"users.read", "users.update"}
    result = _filter_preview_codes({"users.update"}, available)
    assert "users.update" in result


def test_keeps_unknown_actions_that_are_standalone_codes() -> None:
    """Compound codes such as ``inventory.products.cost.read`` (a dotted
    read) pass through unchanged; only the top-level resource matters."""
    available = {"inventory.products.cost.read", "inventory.products.cost.manage"}
    result = _filter_preview_codes({"inventory.products.cost.manage"}, available)
    assert "inventory.products.cost.manage" in result
