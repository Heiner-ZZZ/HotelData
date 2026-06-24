from __future__ import annotations

import ast
from pathlib import Path


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
        Path("dags/hoteldata_ga03_etl.py"),
        Path("dags_backup/hoteldata_taf01_etl_dag.py"),
        Path("dags_backup/hoteldata_ta02_reservations_dag.py"),
        Path("dags_backup/hoteldata_reservas_03_pipeline.py"),
    ]
    return [p for p in candidates if p.exists()]


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

