"""The canonical recepcionista role must cover every front-desk area.

Check-in, check-out, reservations, payments and the money side of the front
desk (billing/charges) all require specific permissions. This test guards the
canonical definition in ``scripts/sync_role_permissions.py`` so a fresh seed
(or a ``sync_role_permissions`` run) always ships a complete front-desk role.

Note: ``resource.manage`` expands to create/read/update/delete, so checking
the ``.manage`` codes covers the read-only variants too.
"""

from __future__ import annotations

from scripts.sync_role_permissions import ROLE_PERMISSIONS


def test_recepcionista_has_full_front_desk_permissions():
    perms = set(ROLE_PERMISSIONS["recepcionista"])

    # Check-in / check-out (manage ⇒ CRUD).
    assert "check-ins.manage" in perms
    assert "check-outs.manage" in perms
    # Reservas + cargos POS durante la estancia activa.
    assert "reservations.manage" in perms
    assert "charges.manage" in perms
    # Pagos: registrar/reembolsar/vincular, y el lado monetario de la
    # facturación (pagar factura, postings de folio, liquidar folio).
    assert "payments.manage" in perms
    assert "billing.manage" in perms
    # Búsqueda de huéspedes para prefill rápido en recepción.
    assert "users.read" in perms
