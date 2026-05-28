from __future__ import annotations

import ast
from pathlib import Path


def _imports_for(dag_path: Path) -> list[str]:
    tree = ast.parse(dag_path.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_dags_do_not_import_web_layers():
    dag_paths = [
        Path("dags/hoteldata_taf01_etl_dag.py"),
        Path("dags/hoteldata_ta02_reservations_dag.py"),
        Path("dags/hoteldata_reservas_03_pipeline.py"),
    ]
    forbidden = ("src.app", "templates", "static")
    for dag_path in dag_paths:
        imports = _imports_for(dag_path)
        assert not [module for module in imports if module.startswith(forbidden)]


def test_dags_use_python_operator_only():
    dag_paths = [
        Path("dags/hoteldata_taf01_etl_dag.py"),
        Path("dags/hoteldata_ta02_reservations_dag.py"),
        Path("dags/hoteldata_reservas_03_pipeline.py"),
    ]
    for dag_path in dag_paths:
        dag_text = dag_path.read_text(encoding="utf-8")
        assert "PythonOperator" in dag_text
        assert "BashOperator" not in dag_text
