"""Enforcement de descarga de informes: los endpoints de export server-side
(``POST /api/reports/pdf`` y ``POST /api/reports/xlsx``) exigen el permiso
global ``reports.download``.

El CSV es client-side (``exportCsv``): su botón se oculta por el mismo permiso
en la UI, pero la frontera real de seguridad son estos endpoints, que hoy
estaban abiertos a cualquier usuario autenticado (sin ``require_permission``).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from passlib.context import CryptContext

# (endpoint, payload mínimo válido)
EXPORT_ENDPOINTS = [
    ("/api/reports/pdf", {"html": "<p>test</p>", "filename": "reporte"}),
    (
        "/api/reports/xlsx",
        {
            "filename": "reporte",
            "sheets": [{"name": "Hoja1", "headers": [{"label": "Col"}], "rows": [["a"]]}],
        },
    ),
]

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _make_user(db, username: str, role: str) -> None:
    db.users.insert_one(
        {
            "username": username,
            "email": f"{username}@example.com",
            "display_name": username.replace("_", " ").title(),
            "password_hash": _pwd.hash("TestPass123!"),
            "primary_role": role,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
    )


async def _login(client, username: str) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": username, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("path,payload", EXPORT_ENDPOINTS)
async def test_export_requires_reports_download(client, db, path, payload):
    """Un rol que puede VER reportes (reports.read) pero NO tiene
    reports.download recibe 403 al intentar exportar."""
    role = "rol_solo_lectura"
    username = "user_solo_lectura"
    db.roles.insert_one(
        {"role_name": role, "display_name": role, "permissions": ["reports.read"], "is_system": True}
    )
    _make_user(db, username, role)
    await _login(client, username)

    resp = await client.post(path, json=payload)
    assert resp.status_code == 403, (
        f"{path} debe exigir reports.download; respondió {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_download_permission_allows_xlsx_export(client, db):
    """Con reports.download, el export XLSX server-side responde 200."""
    role = "rol_con_descarga"
    username = "user_con_descarga"
    db.roles.insert_one(
        {"role_name": role, "display_name": role, "permissions": ["reports.download"], "is_system": True}
    )
    _make_user(db, username, role)
    await _login(client, username)

    resp = await client.post(
        "/api/reports/xlsx",
        json={
            "filename": "reporte",
            "sheets": [{"name": "Hoja1", "headers": [{"label": "Col"}], "rows": [["a"]]}],
        },
    )
    assert resp.status_code == 200, resp.text
