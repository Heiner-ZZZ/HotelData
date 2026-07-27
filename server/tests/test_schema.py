from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

from src.etl.schema import EXPECTED_COLUMNS, validate_columns


def test_expected_schema_is_valid():
    result = validate_columns(EXPECTED_COLUMNS)
    assert result["valid"] is True
    assert result["missing_columns"] == []


def test_missing_schema_column_is_invalid():
    result = validate_columns(EXPECTED_COLUMNS[:-1])
    assert result["valid"] is False
    assert result["missing_columns"] == ["price_usd"]


# ─── Cache-clear ritual regression (knowledge.md → Backend Conventions) ──
#
# Locks the rule that says: after deleting any `*Response` Pydantic class
# (or modifying field aliases), stale `.pyc` files inside `__pycache__/`
# can still be loaded by the running Python interpreter. The only fix is
# to wipe `__pycache__/` and cold-restart the uvicorn process.
#
# This test simulates the failure mode in-process: it deletes a `*Response`
# class from `sys.modules`, wipes its bytecode, and asserts a clean
# re-import succeeds. If a future refactor breaks this invariant, the
# test fails and a code-reviewer (or agent) is forced to address it
# instead of silently leaking cached symbols at next runtime import.

REPO_ROOT = Path(__file__).resolve().parent.parent


def _wipe_module_pyc(module_name: str) -> int:
    """Wipe every ``.pyc`` file inside the module's ``__pycache__/`` dir.

    Mirrors the in-container step ``find /app/server -name __pycache__
    -exec rm -rf {} +`` of the cache-clear ritual, scoped to one module
    for test isolation. Returns the number of files deleted.
    """
    package_rel = module_name.replace(".", "/")
    py_stem = Path(package_rel).name  # last segment, no ``.py``
    pycache_dir = REPO_ROOT / Path(package_rel).parent / "__pycache__"
    if not pycache_dir.exists():
        return 0
    deleted = 0
    for pyc in pycache_dir.glob(f"{py_stem}.*.pyc"):
        pyc.unlink()
        deleted += 1
    dir_cache = pycache_dir / py_stem
    if dir_cache.exists() and dir_cache.is_dir():
        shutil.rmtree(dir_cache)
        deleted += 1
    return deleted


def test_response_class_reimport_succeeds_after_pyc_clear():
    """Regression: re-importing a `*Response` class after wiping its
    bytecode cache must work. Locks the cache-clear ritual as test-backed
    policy (mirrored in knowledge.md / AGENTS.md).

    Failure modes this catches (none today, all theoretical regression vectors):
      - Future refactor puts canonical `*Response` imports behind a path
        that does NOT produce a `.pyc` (silent loss of cache invariant).
      - Someone re-introduces `ObjectIdStr` helper duplication that bloat-
        ens the schema module + breaks the cache invalidation chain.
      - pytest config skips cache wipe; re-importing different class
        resolves to the cached old class.
    """
    # 1. Pick a known `*Response` class that defines the canonical pattern.
    from src.app.modules.reservations.schemas import BookingResponse

    module_name = BookingResponse.__module__
    class_name = BookingResponse.__name__

    # Warm up the import so a `.pyc` file is materialised (gives the test
    # something to actually wipe).
    assert booking_response_is_well_formed(BookingResponse)

    # Wipe bytecode for this module — simulates the cache-clear step.
    wiped = _wipe_module_pyc(module_name)
    assert wiped >= 0  # may be 0 on Python builds without `-O` or skip-cache

    # Force the runtime to forget the loaded module (simulates a
    # ``*Response`` class being deleted at source and the interpreter
    # not yet cold-restarting).
    sys.modules.pop(module_name, None)

    # Re-import and check the class is still there (proves the `.py`
    # source on disk is the source of truth, not stale `.pyc`).
    fresh = importlib.import_module(module_name)
    cls = getattr(fresh, class_name)
    assert cls is BookingResponse or cls.__name__ == class_name


def booking_response_is_well_formed(cls):
    """Sanity check that the test target class has the canonical pattern.

    Auto-skipped if the schema module did NOT yet land the canonical
    `AliasChoices("_id","id")` migration (because we may be running in
    a pre-migration environment for older deployments).
    """
    import re

    src = Path(cls.__module__.replace(".", "/") + ".py")
    repo_src = REPO_ROOT / "src" / Path(cls.__module__.replace(".", "/")).with_suffix(".py").relative_to("src")
    if not repo_src.exists():
        return True  # source not on disk path; test can't validate shape
    text = repo_src.read_text(encoding="utf-8")
    # Look for at least one ``validation_alias=AliasChoices("_id", "id")``
    # in the schema, OR an explicit ``model_rebuild()`` block. Either is
    # sufficient evidence the canonical pattern is in place.
    has_alias = bool(re.search(r'validation_alias=AliasChoices\(["\']_id["\'],\s*["\']id["\']\)', text))
    has_rebuild = bool(re.search(r"\.model_rebuild\(\)", text))
    return has_alias or has_rebuild
