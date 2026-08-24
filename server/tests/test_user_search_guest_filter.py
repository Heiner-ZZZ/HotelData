"""Prefill de huéspedes — la búsqueda solo devuelve usuarios rol cliente/huésped,
y trae la cédula (id_document_number) si está guardada.

Comportamiento deseado (2026-08): al crear una reserva en recepción y filtrar
por caracteres para autocompletar, NO deben aparecer usuarios staff/plataforma
(gerente, operador, housekeeping, super_admin...), solo huéspedes registrados.
"""
from __future__ import annotations

from src.app.modules.reservations.routes.management_impl._users import search_users


def _guest(name: str, email: str, **extra):
    doc = {"display_name": name, "email": email, "primary_role": "cliente"}
    doc.update(extra)
    return doc


def test_search_users_returns_only_guest_role(db) -> None:
    """Devuelve huéspedes (cliente) y NUNCA usuarios staff/plataforma."""
    db.users.insert_many(
        [
            _guest("Ana Huesped", "ana@test.com"),
            {"display_name": "Ana Staff", "email": "anastaff@hotel.local", "primary_role": "housekeeping"},
            {"display_name": "Gerente Ana", "email": "gerente@hotel.local", "primary_role": "gerente_hotel"},
            {"display_name": "Operador", "email": "op@hotel.local", "primary_role": "operador_datos"},
            {"display_name": "Sin Rol", "email": "sinrol@hotel.local"},
        ]
    )
    res = search_users("ana", limit=10, db=db)
    names = [r["name"] for r in res]
    assert "Ana Huesped" in names, names
    assert "Ana Staff" not in names, names
    assert "Gerente Ana" not in names, names


def test_search_users_never_returns_platform_or_staff(db) -> None:
    """Aunque el texto coincida, staff/plataforma quedan fuera del prefill."""
    db.users.insert_many(
        [
            _guest("Ana Huesped", "guest1@test.com"),
            {"display_name": "Ana Admin", "email": "admin@hotel.local", "primary_role": "super_admin"},
            {"display_name": "Ana Marketing", "email": "mkt@hotel.local", "primary_role": "marketing_hotelero"},
            {"display_name": "Ana Revenue", "email": "rev@hotel.local", "primary_role": "revenue_manager"},
        ]
    )
    res = search_users("ana", limit=50, db=db)
    names = [r["name"] for r in res]
    assert "Ana Huesped" in names
    assert "Ana Admin" not in names
    assert "Ana Marketing" not in names
    assert "Ana Revenue" not in names


def test_search_users_includes_cedula_from_id_document_number(db) -> None:
    """La cédula viaja como ``cedula`` tomada de ``id_document_number`` (el
    campo real de la cuenta; ``cedula`` legacy suele estar vacío)."""
    db.users.insert_many(
        [
            _guest("Horuz", "horuz@test.com", id_document_number="1303695842", id_document_type="dni"),
            {"display_name": "Carlos", "email": "carlos@hotel.local", "primary_role": "housekeeping",
             "id_document_number": "999"},
        ]
    )
    res = search_users("horuz", limit=10, db=db)
    assert len(res) == 1, res
    assert res[0]["cedula"] == "1303695842"
    assert res[0]["name"] == "Horuz"
