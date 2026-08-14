"""Matriz rol → informes: códigos granulares (táctico/estratégico + por informe)
asignados a los roles de forma coherente.

Reglas de coherencia (top-down pruning del árbol de navegación):
1. Todo rol con un código fino ``reports.<dominio>.<informe>.read`` debe tener
   también el código de ÁREA ``reports.tactical.read`` (el container "Informes"
   lo exige) y el código de LECTURA del dominio ancestro
   (``reservations.read`` para reports.rates.*/requests, ``billing.read`` para
   reports.billing.*, ``housekeeping.read`` para reports.housekeeping.*).
2. ``reports.download`` es GLOBAL (exportar lo que ya puedes leer), no
   por-informe: se asigna a los niveles administrativos/estratégicos, no a los
   operativos de solo-lectura.
3. ``super_admin`` cubre automáticamente todo el catálogo (incluye download).
"""

from __future__ import annotations

from scripts.init_security_model_ga03 import PERMISSION_CATALOG, ROLE_PERMISSION_CODES
from src.app.security.permissions import expand_permissions

TACTICAL_FINE_CODES = (
    "reports.rates.adr.read",
    "reports.rates.calendar.read",
    "reports.requests.read",
    "reports.billing.invoices.read",
    "reports.billing.payments.read",
    "reports.housekeeping.dashboard.read",
    "reports.housekeeping.operations.read",
    "reports.housekeeping.matrix.read",
)

DOMAIN_READ_ANCESTOR = {
    "reports.rates.adr.read": "reservations.read",
    "reports.rates.calendar.read": "reservations.read",
    "reports.requests.read": "reservations.read",
    "reports.billing.invoices.read": "billing.read",
    "reports.billing.payments.read": "billing.read",
    "reports.housekeeping.dashboard.read": "housekeeping.read",
    "reports.housekeeping.operations.read": "housekeeping.read",
    "reports.housekeeping.matrix.read": "housekeeping.read",
}


def test_reports_download_exists_in_catalog() -> None:
    catalog = {code for code, _ in PERMISSION_CATALOG}
    assert "reports.download" in catalog, "falta reports.download en PERMISSION_CATALOG"


def test_super_admin_covers_reports_and_download() -> None:
    """super_admin auto-incluye el catálogo completo (menos guest)."""
    perms = set(ROLE_PERMISSION_CODES["super_admin"])
    for code in TACTICAL_FINE_CODES:
        assert code in perms, f"super_admin sin {code}"
    assert "reports.tactical.read" in perms
    assert "reports.strategic.read" in perms
    assert "reports.download" in perms


def test_gerente_hotel_has_full_tactical_strategic_and_download() -> None:
    perms = set(ROLE_PERMISSION_CODES["gerente_hotel"])
    assert "reports.tactical.read" in perms
    assert "reports.strategic.read" in perms
    assert "reports.download" in perms
    for code in TACTICAL_FINE_CODES:
        assert code in perms, f"gerente_hotel sin {code}"
    # Ancestros de dominio para ver los informes anidados
    assert "billing.read" in perms, "gerente_hotel necesita billing.read para billing Informes"
    assert "housekeeping.read" in perms, "gerente_hotel necesita housekeeping.read para housekeeping Informes"


def test_revenue_manager_has_revenue_and_billing_reports() -> None:
    perms = set(ROLE_PERMISSION_CODES["revenue_manager"])
    for code in (
        "reports.tactical.read",
        "reports.download",
        "reports.rates.adr.read",
        "reports.rates.calendar.read",
        "reports.billing.invoices.read",
        "reports.billing.payments.read",
        "billing.read",
    ):
        assert code in perms, f"revenue_manager sin {code}"


def test_housekeeping_role_has_housekeeping_reports_view_only() -> None:
    perms = set(ROLE_PERMISSION_CODES["housekeeping"])
    for code in (
        "reports.tactical.read",
        "reports.housekeeping.dashboard.read",
        "reports.housekeeping.operations.read",
        "reports.housekeeping.matrix.read",
    ):
        assert code in perms, f"housekeeping sin {code}"
    assert "reports.download" not in perms, "housekeeping es solo-lectura: no debe exportar"


def test_recepcionista_has_requests_report_without_download() -> None:
    perms = set(ROLE_PERMISSION_CODES["recepcionista"])
    assert "reports.tactical.read" in perms
    assert "reports.requests.read" in perms
    assert "reports.download" not in perms, "recepcionista ve su informe pero no exporta"


def test_admin_sistema_has_strategic_and_download() -> None:
    perms = set(ROLE_PERMISSION_CODES["admin_sistema"])
    assert "reports.strategic.read" in perms
    assert "reports.download" in perms


def test_roles_with_fine_reports_have_area_and_domain_ancestors() -> None:
    """Coherencia top-down: ningún rol recibe un código fino sin su área ni su
    ancestro de dominio (si no, el árbol lo podaría y el permiso sería inútil)."""
    for role, codes in ROLE_PERMISSION_CODES.items():
        if role in ("super_admin", "cliente"):
            continue
        expanded = expand_permissions(set(codes))
        for code in codes:
            if code not in DOMAIN_READ_ANCESTOR:
                continue
            assert "reports.tactical.read" in expanded, f"{role}: {code} sin reports.tactical.read"
            domain = DOMAIN_READ_ANCESTOR[code]
            assert domain in expanded, f"{role}: {code} sin ancestro de dominio {domain}"
