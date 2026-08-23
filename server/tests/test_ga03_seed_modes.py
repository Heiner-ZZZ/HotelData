"""Modos incremental/full del seed GA03 (CSV → PocketBase).

El bug 2026-08: ``start_seed_source`` ignoraba el toggle incremental/full para
el seed y el script ``cargar_reservas_hoteleras_03.py`` tenía el camino de
reanudar (skiprows) muerto tras un ``if current > 0: raise``. Estos tests fijan
la decisión de carga y los args que el backend pasa al script.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from src.app.features.etl_status.services import runtime_service

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "cargar_reservas_hoteleras_03.py"


def _load_seed_script():
    spec = importlib.util.spec_from_file_location("cargar_reservas_hoteleras_03", _SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── Decisión pura de carga ──────────────────────────────────────────────────


def test_resolve_load_action_matrix():
    script = _load_seed_script()
    fn = script.resolve_load_action

    assert fn(current=0, expected=1600000, incremental=False) == "fresh"
    assert fn(current=0, expected=1600000, incremental=True) == "fresh"
    assert fn(current=1600000, expected=1600000, incremental=False) == "noop"
    assert fn(current=1600000, expected=1600000, incremental=True) == "noop"

    # 800000 cargados de 1600000: incremental reanuda; full exige reload.
    assert fn(current=800000, expected=1600000, incremental=True) == "resume"
    assert fn(current=800000, expected=1600000, incremental=False) == "reload_required"

    # Ya tiene más de lo esperado → siempre reload (nunca reanudar sobre extra).
    assert fn(current=1600001, expected=1600000, incremental=True) == "reload_required"
    assert fn(current=1600001, expected=1600000, incremental=False) == "reload_required"


def test_incremental_mode_env_parsing(monkeypatch):
    script = _load_seed_script()

    for raw in ("", "false", "0", "no"):
        monkeypatch.setenv("GA03_INCREMENTAL_MODE", raw)
        assert script.incremental_mode() is False

    for raw in ("true", "1", "yes", "TRUE"):
        monkeypatch.setenv("GA03_INCREMENTAL_MODE", raw)
        assert script.incremental_mode() is True


# ── Args que el backend pasa al script ─────────────────────────────────────


def _capture_start_script(monkeypatch):
    captured: dict = {}

    class _Settings:
        project_root = Path("/tmp/hoteldata_test")
        reports_dir = Path("/tmp/hoteldata_test/reports")

    monkeypatch.setattr(runtime_service, "get_settings", lambda: _Settings())
    monkeypatch.setattr(runtime_service, "preparation_progress", dict)
    monkeypatch.setattr(runtime_service, "_write_progress_seed", lambda *a, **k: None)

    def fake_start(script_name, args=None, log_name="", env=None):
        captured["script_name"] = script_name
        captured["args"] = list(args or [])
        captured["env"] = dict(env or {})
        return {"ok": True, "pid": 1, "command": "", "stdout": "", "stderr": "", "returncode": 0}

    monkeypatch.setattr(runtime_service, "_start_script", fake_start)
    return captured


def test_start_seed_source_full_passes_reload(monkeypatch):
    captured = _capture_start_script(monkeypatch)
    monkeypatch.setattr(runtime_service, "_ga03_collection_name", lambda: "hotel_reservation_events_03")

    result = runtime_service.start_seed_source(target_records=1600000, incremental=False)

    assert result["ok"] is True
    assert captured["script_name"] == "cargar_reservas_hoteleras_03.py"
    assert captured["args"] == ["--reload", "--confirm-reload", "hotel_reservation_events_03"]
    assert captured["env"]["GA03_INCREMENTAL_MODE"] == "false"


def test_start_seed_source_incremental_skips_reload(monkeypatch):
    captured = _capture_start_script(monkeypatch)

    runtime_service.start_seed_source(target_records=1600000, incremental=True)

    assert captured["script_name"] == "cargar_reservas_hoteleras_03.py"
    assert "--reload" not in captured["args"]
    assert "--confirm-reload" not in captured["args"]
    assert captured["env"]["GA03_INCREMENTAL_MODE"] == "true"
