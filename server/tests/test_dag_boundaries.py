from __future__ import annotations

import ast
import os
from pathlib import Path


def _existing_path(candidates: list[Path], description: str) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise AssertionError(f"No se encontró {description}; rutas revisadas: {candidates}")


_TEST_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT_CANDIDATES = [
    Path(os.getenv("HOTELDATA_REPO_ROOT", "")),
    _TEST_ROOT,
    Path("/opt/hoteldata"),
    Path("/app"),
]
_ACTIVE_DAGS_ROOT_CANDIDATES = [
    root / "dags" for root in _REPO_ROOT_CANDIDATES if str(root) != "."
] + [Path("/opt/airflow/dags")]
_ACTIVE_DAGS_ROOT = _existing_path(
    _ACTIVE_DAGS_ROOT_CANDIDATES,
    "la carpeta activa de DAGs",
)
_ACTIVE_GA03_PATH = _ACTIVE_DAGS_ROOT / "hoteldata_ga03_etl.py"
_BACKUP_DAGS_ROOT_CANDIDATES = [
    root / "dags_backup" for root in _REPO_ROOT_CANDIDATES if str(root) != "."
]
_BACKUP_DAGS_ROOT = next(
    (path for path in _BACKUP_DAGS_ROOT_CANDIDATES if path.exists()),
    _BACKUP_DAGS_ROOT_CANDIDATES[0],
)


def _imports_from(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _dag_paths() -> list[Path]:
    candidates = [
        _ACTIVE_GA03_PATH,
        _ACTIVE_DAGS_ROOT / "hoteldata_mongo_to_clickhouse_etl.py",
        _BACKUP_DAGS_ROOT / "hoteldata_taf01_etl_dag.py",
        _BACKUP_DAGS_ROOT / "hoteldata_ta02_reservations_dag.py",
        _BACKUP_DAGS_ROOT / "hoteldata_reservas_03_pipeline.py",
    ]
    return [path for path in candidates if path.exists()]


def test_airflow_dag_respects_etl_boundaries():
    forbidden_prefixes = ("src.app", "templates", "static")
    for dag_path in _dag_paths():
        imports = _imports_from(dag_path)
        assert not [module for module in imports if module.startswith(forbidden_prefixes)]


def test_airflow_dag_uses_python_operator():
    for dag_path in _dag_paths():
        dag_text = dag_path.read_text(encoding="utf-8")
        assert "PythonOperator" in dag_text
        assert "BashOperator" not in dag_text


def test_airflow_dag_has_core_tasks():
    dag_path = _dag_paths()
    assert dag_path
    dag_text = dag_path[0].read_text(encoding="utf-8")
    for task_id in ["validate_environment", "create_indexes", "save_execution_report"]:
        assert task_id in dag_text
    assert ("load_mongodb" in dag_text) or ("to_mongodb" in dag_text)


def test_m2c_dag_has_own_pipeline_tasks():
    """The MongoDB→ClickHouse DAG defines its own task graph (not GA03's)."""
    m2c_path = _ACTIVE_DAGS_ROOT / "hoteldata_mongo_to_clickhouse_etl.py"
    if not m2c_path.exists():
        return
    dag_text = m2c_path.read_text(encoding="utf-8")
    assert 'dag_id="hoteldata_mongo_to_clickhouse_etl"' in dag_text
    for task_id in [
        "validate_config",
        "extract_mongo",
        "transform",
        "create_tables",
        "load_clickhouse",
        "quality_report",
        "execution_report",
    ]:
        assert task_id in dag_text
    assert "ClickHouse" in dag_text  # este DAG SÍ toca ClickHouse por diseño


def test_active_ga03_dag_preserves_end_to_end_source_preparation():
    dag_text = _ACTIVE_GA03_PATH.read_text(encoding="utf-8")
    assert "dag_id=\"hoteldata_ga03_etl\"" in dag_text
    assert "seed_source" in dag_text
    assert "validate_dataset" in dag_text
    assert "subprocess" in dag_text
    assert "POCKETBASE_COLLECTION_03" in dag_text
    assert "POCKETBASE_ADMIN_EMAIL" in dag_text
    assert "POCKETBASE_ADMIN_PASSWORD" in dag_text
    assert "Heiner2005*" not in dag_text
    assert "hzambranor@uteq.edu.ec" not in dag_text
    assert 'env.get("TARGET_RECORDS") or env.get("GA03_EXPECTED_RECORDS")' in dag_text
    assert 'env.get("TARGET_RECORDS", env.get("GA03_EXPECTED_RECORDS", "800000"))' not in dag_text
    assert dag_text.index('task_id="seed_source"') < dag_text.index('task_id="validate_dataset"')
    assert dag_text.index('task_id="validate_dataset"') < dag_text.index('task_id="validate_environment"')
    assert "ClickHouse" not in dag_text


def test_airflow_mount_boundary_keeps_backups_out_of_active_dags():
    """The Compose mount is ``server/dags``; backups are never in that tree.

    This intentionally does not require exactly one active DAG: the second
    MongoDB-to-ClickHouse ETL will be another legitimate file in this folder.
    """
    assert _ACTIVE_GA03_PATH.is_file()
    assert not list(_ACTIVE_DAGS_ROOT.glob("dags_backup/*.py"))
    if _BACKUP_DAGS_ROOT.exists():
        assert all(
            path.parent == _BACKUP_DAGS_ROOT
            for path in _BACKUP_DAGS_ROOT.glob("*.py")
        )


def test_active_ga03_declares_all_fourteen_pipeline_tasks():
    dag_text = _ACTIVE_GA03_PATH.read_text(encoding="utf-8")
    expected_task_ids = [
        "seed_source",
        "validate_dataset",
        "validate_environment",
        "extract_from_pocketbase",
        "save_extract_jsonl",
        "convert_to_parquet",
        "validate_parquet_schema",
        "transform_dimensions",
        "transform_fact_reservations",
        "load_dimensions_to_mongodb",
        "load_fact_to_mongodb",
        "create_indexes",
        "run_quality_checks",
        "save_execution_report",
    ]
    declared_task_ids = [
        line.split('task_id="', 1)[1].split('"', 1)[0]
        for line in dag_text.splitlines()
        if 'task_id="' in line
    ]
    assert declared_task_ids == expected_task_ids

