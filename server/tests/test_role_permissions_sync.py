"""Guard: ``scripts/sync_role_permissions.py`` must never regress the canonical
role permissions defined by ``scripts/init_security_model_ga03.py``.

Why this exists: ``sync_role_permissions.py`` is the maintenance re-seed tool —
it ``$set``s each role's ``permissions`` array. If its ``ROLE_PERMISSIONS`` map
drifts *below* the canonical seed (e.g. a new permission added to
``init_security_model_ga03.py`` but not to the sync map), running the sync tool
would silently REMOVE that permission from live roles in the DB. These tests
fail the build on that drift instead of letting a re-seed regress permissions.

The invariant is one-directional on purpose: sync may grant *extra* permissions
(a deliberate override), but it must never grant *fewer* than the canonical
catalog grants. Extras are the exception, not the rule: ``maintenance`` used to
carry ``properties.read`` / ``reservations.read`` as a stale override that the
canonical map never had — aligned away in 2026-08 (see
``test_maintenance_sync_has_no_extras_beyond_canonical``) so a re-seed does not
re-introduce codes the DB role already lost.
"""

from scripts.init_security_model_ga03 import PERMISSION_CATALOG, ROLE_PERMISSION_CODES
from scripts.sync_role_permissions import ROLE_PERMISSIONS


def test_sync_grants_at_least_canonical_permissions() -> None:
    """For every role the sync tool manages, sync ⊆ canonical must NOT regress.

    A regression here means re-seeding with ``sync_role_permissions.py`` would
    strip canonical permissions from that role in the DB.
    """
    # Guard contra typos en las KEYS del sync map: una key mal escrita haría
    # que ``ROLE_PERMISSIONS.get(role)`` devuelva None y el loop la saltaría
    # silenciosamente como "rol no gestionado" — el drift quedaría invisible.
    unknown_roles = sorted(set(ROLE_PERMISSIONS) - set(ROLE_PERMISSION_CODES))
    assert not unknown_roles, (
        "sync_role_permissions.py gestiona roles inexistentes en el catálogo "
        f"canónico (¿typo en la key?): {unknown_roles}"
    )

    regressions: dict[str, list[str]] = {}
    for role, canonical_codes in sorted(ROLE_PERMISSION_CODES.items()):
        sync_codes = ROLE_PERMISSIONS.get(role)
        if sync_codes is None:
            # Rol no gestionado por el sync tool (recepcionista, housekeeping,
            # concierge) → el re-seed no lo toca, no puede regresionar.
            continue
        missing = sorted(set(canonical_codes) - set(sync_codes))
        if missing:
            regressions[role] = missing
    assert not regressions, (
        "sync_role_permissions.py regresaría permisos del catálogo canónico al "
        f"re-seedar (códigos faltantes por rol): {regressions}"
    )


def test_maintenance_sync_has_no_extras_beyond_canonical() -> None:
    """The ``maintenance`` role in the sync map must match the canonical map
    exactly (no stale extras).

    Historical drift: the sync map granted ``properties.read`` and
    ``reservations.read`` to ``maintenance`` while the canonical map never did.
    The DB role was re-aligned to canonical, but a sync re-seed would have
    re-introduced the codes ($set semantics). This test pins the alignment so
    the drift cannot silently return.
    """
    canonical_codes = set(ROLE_PERMISSION_CODES["maintenance"])
    sync_codes = set(ROLE_PERMISSIONS["maintenance"])
    extras = sorted(sync_codes - canonical_codes)
    assert not extras, (
        "sync_role_permissions.py otorga a maintenance códigos que el canónico "
        f"no tiene (drift): {extras} — alinear el mapa sync con ROLE_PERMISSION_CODES."
    )


def test_sync_permission_codes_exist_in_canonical_catalog() -> None:
    """Every code in the sync map must be a real catalog code.

    A typo'd code would seed a dead permission that no endpoint checks and that
    no UI could ever grant — a silent configuration bug.
    """
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    invalid = sorted(
        {
            code
            for codes in ROLE_PERMISSIONS.values()
            for code in codes
            if code not in catalog_codes
        }
    )
    assert not invalid, f"Códigos inexistentes en el catálogo canónico: {invalid}"
