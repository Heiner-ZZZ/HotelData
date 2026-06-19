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


def test_airflow_dag_respects_etl_boundaries():
    imports = _imports_from(Path("dags/hoteldata_taf01_etl_dag.py"))
    forbidden_prefixes = ("src.app", "templates", "static")
    assert not [module for module in imports if module.startswith(forbidden_prefixes)]


def test_airflow_dag_uses_required_pipeline_name():
    dag_text = Path("dags/hoteldata_taf01_etl_dag.py").read_text(encoding="utf-8")
    assert "hoteldata_taf01_etl_pipeline" in dag_text
    assert "BashOperator" not in dag_text


def test_airflow_dag_has_fact_pipeline_tasks():
    dag_text = Path("dags/hoteldata_taf01_etl_dag.py").read_text(encoding="utf-8")
    for task_id in [
        "validate_environment",
        "seed_master_collections_check",
        "extract_csv",
        "validate_schema",
        "transform_fact_events",
        "validate_master_keys",
        "load_fact_events",
        "load_rejected_records",
        "create_indexes",
        "save_execution_report",
    ]:
        assert task_id in dag_text
