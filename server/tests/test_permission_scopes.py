"""Scope del catálogo (C 2026-08): sistema/hotel/guest + sync script↔runtime.

El runtime resuelve el scope con ``permission_scope()`` de
``src.app.security.permissions``; el seed canónico
(``scripts/init_security_model_ga03.py``) duplica el mapa con KEEP IN SYNC y
lo escribe en la colección ``permissions``. Estos tests pinchan:
  1. Que ambos mapas (script y runtime) sean idénticos — si divergen, el
     editor del hotel (runtime) y el seed (BD) desincronizan.
  2. Que todo código del catálogo tenga un scope y que system/guest sean
     disjuntos.
  3. La clasificación de los códigos sensibles (ETL, usuarios, aprobación de
     hoteles, cartera estratégica → system; cuenta/búsqueda del huésped →
     guest; operaciones del hotel → hotel).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from src.app.security.permissions import (
    GUEST_PERMISSION_CODES,
    GUEST_ROLES,
    PLATFORM_ROLES,
    SYSTEM_SCOPE_CODES,
    permission_scope,
)

SERVER_ROOT = Path(__file__).resolve().parents[1]


def _load_canonical():
    spec = importlib.util.spec_from_file_location(
        "init_security_model_ga03_scope_audit",
        SERVER_ROOT / "scripts/init_security_model_ga03.py",
    )
    assert spec and spec.loader, "no se pudo cargar scripts/init_security_model_ga03.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_and_runtime_scopes_in_sync() -> None:
    canon = _load_canonical()
    assert set(canon.SYSTEM_SCOPE_CODES) == set(SYSTEM_SCOPE_CODES), (
        "SYSTEM_SCOPE_CODES divergió entre scripts/init_security_model_ga03.py "
        "y src/app/security/permissions.py (KEEP IN SYNC)"
    )
    assert set(canon.GUEST_PERMISSION_CODES) == set(GUEST_PERMISSION_CODES), (
        "GUEST_PERMISSION_CODES divergió entre el seed y el runtime (KEEP IN SYNC)"
    )


def test_system_and_guest_scopes_are_disjoint() -> None:
    assert SYSTEM_SCOPE_CODES.isdisjoint(GUEST_PERMISSION_CODES), (
        "un código no puede ser system y guest a la vez"
    )


def test_every_catalog_code_has_a_scope() -> None:
    canon = _load_canonical()
    codes = {code for code, _ in canon.PERMISSION_CATALOG}
    unclassified = [c for c in codes if permission_scope(c) not in ("system", "hotel", "guest")]
    assert not unclassified, f"códigos sin scope válido: {unclassified}"


def test_platform_codes_are_system_scope() -> None:
    for code in (
        "etl.manage", "etl.read", "etl.execute",
        "users.manage", "users.create", "users.read", "users.update", "users.delete",
        "roles.manage", "roles.read",
        "audit.manage", "audit.read",
        "monitoring.manage", "monitoring.read",
        "settings.manage", "settings.read",
        "properties.approve",
        "reports.strategic.portfolio.read",
    ):
        assert permission_scope(code) == "system", f"{code} debe ser system"


def test_guest_codes_are_guest_scope() -> None:
    for code in ("account.manage", "account.read", "account.update", "account.bookings.read", "search.manage", "search.read"):
        assert permission_scope(code) == "guest", f"{code} debe ser guest"


def test_hotel_operational_codes_are_hotel_scope() -> None:
    for code in (
        "reservations.manage", "billing.read", "billing.write_off.approve",
        "hr.portal.read", "hr.directory.read", "hr.onboarding.create",
        "housekeeping.manage", "check-ins.early_approve",
        "hotel.manage_roles", "dashboard.read", "reports.download",
        "reports.strategic.read", "reports.tactical.read",
    ):
        assert permission_scope(code) == "hotel", f"{code} debe ser hotel"


def test_runtime_and_script_platform_guest_roles_in_sync() -> None:
    """PLATFORM_ROLES / GUEST_ROLES (allow-lists de quién puede portar códigos
    system/guest) deben coincidir entre el seed y el runtime (KEEP IN SYNC)."""
    canon = _load_canonical()
    assert set(canon.PLATFORM_ROLES) == set(PLATFORM_ROLES)
    assert set(canon.GUEST_ROLES) == set(GUEST_ROLES)


def test_hotel_roles_never_carry_platform_or_guest_codes() -> None:
    """Lógica dura (C 2026-08): ningún rol fuera de la plataforma porta códigos
    system; ningún rol que no sea el huésped porta códigos guest.

    Regresión que impide reintroducir ``properties.approve`` en gerente_hotel
    (aprobación de hoteles = plataforma; conflicto competitivo) o ``users.read``
    en recepcionista (lista global de usuarios = plataforma).
    """
    canon = _load_canonical()
    for role, codes in canon.ROLE_PERMISSION_CODES.items():
        if role == "super_admin" or role in canon.PLATFORM_ROLES:
            continue  # plataforma: puede portar códigos system
        platform_bad = sorted(set(codes) & SYSTEM_SCOPE_CODES)
        assert not platform_bad, f"{role} porta códigos de plataforma: {platform_bad}"
        if role not in canon.GUEST_ROLES:
            guest_bad = sorted(set(codes) & GUEST_PERMISSION_CODES)
            assert not guest_bad, f"{role} porta códigos de huésped: {guest_bad}"
