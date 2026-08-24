"""Invariante: ``seed_roles_users.py`` ya NO es una fuente divergente de
roles/permisos.

Antes (legacy) definía listas propias diminutas (``ROLES``/``PERMISSIONS``/
``ROLE_PERMISSIONS``) y las escribía con ``$set`` sobre
``roles.permissions``, pisando el catálogo canónico cada vez que se
re-ejecutaba después de ``init_security_model_ga03.py``. Desde la migración
importa ``BASE_ROLES``/``PERMISSION_CATALOG``/``ROLE_PERMISSION_CODES`` y las
funciones ``upsert_roles``/``upsert_permissions``/``embed_role_permissions``
del canónico (fuente única). Su único aporte propio son los usuarios demo.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, SERVER_ROOT / rel)
    assert spec and spec.loader, f"no se pudo cargar {rel}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _modules():
    seed = _load("seed_roles_users_audit", "scripts/seed_roles_users.py")
    canon = _load("init_security_model_ga03_audit", "scripts/init_security_model_ga03.py")
    return seed, canon


def test_seed_roles_users_reuses_canonical_role_permission_codes() -> None:
    seed, canon = _modules()
    assert seed.ROLE_PERMISSION_CODES == canon.ROLE_PERMISSION_CODES


def test_seed_roles_users_reuses_canonical_base_roles() -> None:
    seed, canon = _modules()
    assert seed.BASE_ROLES == canon.BASE_ROLES


def test_seed_roles_users_reuses_canonical_permission_catalog() -> None:
    seed, canon = _modules()
    assert seed.PERMISSION_CATALOG == canon.PERMISSION_CATALOG


def test_seed_roles_users_has_no_legacy_divergent_lists() -> None:
    seed, _ = _modules()
    # Las listas legacy (ROLE_PERMISSIONS diminutas con $set) no deben existir.
    # Si alguien las reintroduce, este test revienta en el primer chequeo.
    assert not hasattr(seed, "ROLE_PERMISSIONS")
    assert not hasattr(seed, "PERMISSIONS")


def test_seed_roles_users_keeps_demo_users() -> None:
    seed, _ = _modules()
    usernames = {u["username"] for u in seed.USERS}
    assert {"admin", "gerente", "operador", "cliente1", "marketing", "revenue"} <= usernames
    canonical_roles = {r[0] for r in seed.BASE_ROLES}
    for u in seed.USERS:
        assert u["primary_role"] in canonical_roles, f"rol {u['primary_role']} no canónico"


def test_seed_roles_users_seeds_convergent_permissions_on_test_db() -> None:
    """Smoke end-to-end: ``seed()`` sobre la BD de test deja cada
    ``roles.permissions`` EXACTAMENTE como el catálogo canónico (convergente,
    nunca pisado con listas divergentes)."""
    from pymongo import MongoClient

    seed, canon = _modules()
    uri = os.environ.get("MONGO_URI", "mongodb://mongo:27018")
    db_name = os.environ.get("MONGO_DATABASE", "hoteldata_hub_test")

    seed.seed(uri=uri, db_name=db_name)
    # Segunda corrida: si re-ejecutar pisara permisos con ``$set`` divergentes
    # (el bug legacy), la invariante salta aquí. La convergencia se demuestra
    # por re-ejecución, no por un único run.
    seed.seed(uri=uri, db_name=db_name)

    db = MongoClient(uri)[db_name]
    try:
        for role_name, codes in canon.ROLE_PERMISSION_CODES.items():
            doc = db.roles.find_one({"role_name": role_name})
            assert doc is not None, f"rol {role_name} no sembrado por seed()"
            assert sorted(doc.get("permissions", [])) == sorted(codes), (
                f"rol {role_name}: permisos divergentes {doc.get('permissions')}"
            )
        demo = db.users.count_documents({"username": {"$in": ["admin", "gerente", "operador"]}})
        assert demo == 3, f"usuarios demo no sembrados (encontrados {demo})"
    finally:
        db.client.close()


def test_operador_datos_is_platform_role_monitoring_only() -> None:
    """operador_datos es un rol de PLATAFORMA (por encima del hotel) y tras la
    corrección de 2026-08 solo porta monitoreo: sin etl.execute/etl.read ni
    audit.read ni dashboard.read. El ETL lo ejecuta solo la administración.
    """
    _, canon = _modules()
    assert "operador_datos" in canon.PLATFORM_ROLES
    assert canon.ROLE_PERMISSION_CODES["operador_datos"] == ["monitoring.read"]
