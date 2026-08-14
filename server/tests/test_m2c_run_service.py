"""Tests del disparo del pipeline M2C en subproceso separado.

El botón "Run pipeline" lanza el ETL con ``python -m
src.etl.mongo_to_clickhouse.runner`` en un proceso aislado (``Popen`` con
``start_new_session``), de modo que un reinicio del --reload de uvicorn no
mata la corrida en curso. El subproceso es dueño del lock y lo limpia en su
``finally``, también ante fallos.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from config.settings import get_settings


def test_start_pipeline_spawns_isolated_subprocess(monkeypatch: pytest.MonkeyPatch):
    """El run se lanza como subproceso aislado, no como thread del API."""
    from src.app.features.etl_status_m2c.services import run_service

    settings = get_settings()
    lock_path = settings.reports_dir / "pipeline_m2c.lock"
    lock_path.unlink(missing_ok=True)

    calls: list[dict] = []

    class _FakeProc:
        pid = 424242

    def _fake_popen(cmd, **kwargs):
        calls.append({"cmd": cmd, **kwargs})
        return _FakeProc()

    monkeypatch.setattr(run_service.subprocess, "Popen", _fake_popen)
    try:
        result = run_service.start_pipeline()
    finally:
        lock_path.unlink(missing_ok=True)

    assert result["ok"] is True
    assert result["pid"] == 424242
    assert calls, "start_pipeline debe lanzar un subproceso"
    call = calls[0]
    assert call["cmd"] == [sys.executable, "-m", "src.etl.mongo_to_clickhouse.runner"]
    assert call.get("start_new_session") is True
    assert call.get("cwd") == settings.project_root


def test_runner_returns_zero_when_pipeline_ok(monkeypatch: pytest.MonkeyPatch):
    """El subproceso termina 0 cuando el pipeline reporta ok."""
    from src.etl.mongo_to_clickhouse import runner

    def _ok(*args, **kwargs):
        return {"ok": True, "rows_by_table": {}}

    monkeypatch.setattr(runner, "_run_pipeline", _ok)
    assert runner.run_subprocess() == 0


def test_runner_cleans_lock_and_returns_one_on_failure(monkeypatch: pytest.MonkeyPatch):
    """Ante un fallo, el subproceso limpia el lock y termina 1 (no deja el run colgado)."""
    from src.etl.mongo_to_clickhouse import runner

    settings = get_settings()
    lock_path = settings.reports_dir / "pipeline_m2c.lock"
    lock_path.touch()

    def _boom(*args, **kwargs):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(runner, "_run_pipeline", _boom)
    try:
        assert runner.run_subprocess() == 1
    finally:
        lock_path.unlink(missing_ok=True)
    assert not lock_path.exists()
