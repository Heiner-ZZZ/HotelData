"""Public API contract for ``src.app.modules.reception.shifts``.

Background
----------
``resolve_expected_shift_type`` used to be ``_resolve_expected_shift_type``
(private by convention). Sibling modules imported it via an ``as`` alias
to avoid pulling a leading-underscore name across the module boundary::

    from .shifts import _resolve_expected_shift_type as resolve_expected_shift_type

We renamed the function (drop the underscore) so the alias workaround
isn't needed, the function is genuinely part of the module's public
surface, and code review can flag accidental re-prefixing at import time
instead of in code review memory.

This test pins the resulting contract so any future drift is caught by
CI immediately, not by a human reviewer.

If a test here fails, you likely:

* re-prefixed ``resolve_expected_shift_type`` back to
  ``_resolve_expected_shift_type`` — undo the rename
* reintroduced the ``as`` alias in a module that imports from
  ``shifts`` — remove the alias (just import the public name)
* moved the function or module — update this test's import path
"""
from __future__ import annotations

from datetime import datetime, timezone

import src.app.modules.reception.shifts as shifts
from src.app.modules.reception.shifts import resolve_expected_shift_type


# ─── Contract 1: importable WITHOUT an `as` alias ─────────────────────────


def test_resolve_expected_shift_type_is_importable_without_alias():
    """The function must be reachable via a clean public import.

    The import statement at the top of this module already exercises
    this; this assertion exists so a regression that adds an ``as``
    alias is caught here, not during code review.
    """
    assert callable(resolve_expected_shift_type), (
        "resolve_expected_shift_type must be a callable reachable via "
        "`from src.app.modules.reception.shifts import resolve_expected_shift_type` "
        "without an `as` alias."
    )


# ─── Contract 2: old private name removed from the module ─────────────────


def test_underscored_name_removed_from_module():
    """The old private name must NOT be reachable as a module attribute.

    Catches accidental git-revert / merge-conflict resolution that
    restored the underscore.
    """
    assert not hasattr(shifts, "_resolve_expected_shift_type"), (
        "`_resolve_expected_shift_type` was found on the shifts module; "
        "expected it to be removed when the rename landed. Restore the "
        "rename — see git log for the conversion commit."
    )


# ─── Contract 3: function returns the documented shape ────────────────────


def test_resolve_expected_shift_type_returns_valid_tuple():
    """Smoke test — the function must return ``(shift_type, source)``.

    The test DB has no seeded users, so the lookup falls through to the
    clock-hour heuristic. We pick 10:00 UTC, which the heuristic maps
    deterministically to the ``morning`` bucket (08:00–15:59).

    Validates ONLY the shape and provenance string — NOT an exhaustive
    hour-to-bucket map (that's covered elsewhere by the existing shift
    tests).
    """
    # An opener username deliberately absent from the test DB; the lookup
    # will fall through to the time-of-day heuristic. The signature is
    # `(opened_by: str, at_dt: datetime) -> tuple[str, str]`.
    at_dt = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
    result = resolve_expected_shift_type("__nonexistent_opener_for_test__", at_dt)

    assert isinstance(result, tuple), f"expected tuple, got {type(result).__name__}"
    assert len(result) == 2, f"expected 2-tuple, got {len(result)}-tuple"

    shift_type, source = result
    assert shift_type in ("morning", "afternoon", "evening"), (
        f"unexpected shift_type={shift_type!r}; must be one of morning/afternoon/evening"
    )
    assert source in ("schedule", "time_of_day"), (
        f"unexpected source={source!r}; must be 'schedule' or 'time_of_day'"
    )

    # 10:00 UTC falls into the 08:00–15:59 morning bucket; no HR fixture
    # means source == 'time_of_day'.
    assert shift_type == "morning"
    assert source == "time_of_day"
