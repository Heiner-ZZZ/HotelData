from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "ga03_hotel_cards_data_report.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(port: int) -> subprocess.Popen[str]:
    stdout_path = PROJECT_ROOT / "data" / "reports" / "ga03_hotel_cards_data.stdout.log"
    stderr_path = PROJECT_ROOT / "data" / "reports" / "ga03_hotel_cards_data.stderr.log"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_handle = open(stdout_path, "w", encoding="utf-8")
    stderr_handle = open(stderr_path, "w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(PROJECT_ROOT),
        stdout=stdout_handle,
        stderr=stderr_handle,
        text=True,
    )
    process._stdout_handle = stdout_handle  # type: ignore[attr-defined]
    process._stderr_handle = stderr_handle  # type: ignore[attr-defined]
    return process


def stop_server(process: subprocess.Popen[str]) -> None:
    try:
        process.terminate()
        process.wait(timeout=10)
    except Exception:
        process.kill()
    finally:
        stdout_handle = getattr(process, "_stdout_handle", None)
        stderr_handle = getattr(process, "_stderr_handle", None)
        if stdout_handle:
            stdout_handle.close()
        if stderr_handle:
            stderr_handle.close()


def wait_for_server(base_url: str) -> bool:
    deadline = time.time() + 25
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/auth/login", timeout=2)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


def login_cliente(base_url: str) -> requests.Session:
    session = requests.Session()
    session.post(
        f"{base_url}/auth/login",
        data={"identifier": "cliente", "password": "Cliente123*"},
        allow_redirects=False,
        timeout=30,
    )
    return session


def run_validation() -> dict[str, Any]:
    report: dict[str, Any] = {"generated_at": utc_now_iso(), "result": False, "checks": [], "errors": []}
    errors: list[str] = []

    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = start_server(port)
    try:
        if not wait_for_server(base_url):
            errors.append("server did not start")
            return report

        session = login_cliente(base_url)
        search_response = session.get(f"{base_url}/hotels/search", timeout=30)
        search_html = search_response.text
        cards_ok = search_response.status_code == 200 and search_html.count("ID propiedad") >= 10
        report["checks"].append({"name": "search_cards_display_name", "ok": cards_ok, "details": {"status_code": search_response.status_code}})
        if not cards_ok:
            errors.append("search_cards_display_name: expected at least 10 enriched cards")

        country_ok = "País 219" not in search_html
        report["checks"].append({"name": "search_cards_country_label", "ok": country_ok, "details": {}})
        if not country_ok:
            errors.append("search_cards_country_label: raw country label still visible")

        destination_ok = "Destino " in search_html
        report["checks"].append({"name": "search_cards_destinations", "ok": destination_ok, "details": {}})
        if not destination_ok:
            errors.append("search_cards_destinations: no destination display labels found")

        metrics_ok = "precio promedio" in search_html and "reservas" in search_html and "clicks" in search_html and "conversión" in search_html
        report["checks"].append({"name": "search_cards_metrics", "ok": metrics_ok, "details": {}})
        if not metrics_ok:
            errors.append("search_cards_metrics: metrics block missing")

        detail_response = session.get(f"{base_url}/hotels/61529", timeout=30)
        detail_html = detail_response.text
        detail_ok = (
            detail_response.status_code == 200
            and "Países visitantes principales" in detail_html
            and "Canales principales" in detail_html
            and "Tarifas configuradas" in detail_html
            and "Habitaciones y políticas" in detail_html
            and "ID propiedad: 61529" in detail_html
        )
        report["checks"].append({"name": "hotel_detail_view", "ok": detail_ok, "details": {"status_code": detail_response.status_code}})
        if not detail_ok:
            errors.append("hotel_detail_view: missing enriched detail sections")
    finally:
        stop_server(process)

    report["errors"] = errors
    report["result"] = not errors
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    report = run_validation()
    print(json.dumps({"result": report["result"], "checks": len(report["checks"]), "errors": report["errors"]}, indent=2, ensure_ascii=False))
    print(f"report_path={REPORT_PATH}")


if __name__ == "__main__":
    main()
