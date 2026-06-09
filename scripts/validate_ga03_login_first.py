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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "ga03_login_first_report.json"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.security.navigation import get_default_redirect_for_role


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(port: int) -> subprocess.Popen[str]:
    stdout_path = PROJECT_ROOT / "data" / "reports" / "ga03_login_first.stdout.log"
    stderr_path = PROJECT_ROOT / "data" / "reports" / "ga03_login_first.stderr.log"
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


def ensure_demo_users() -> None:
    subprocess.run(
        [sys.executable, "scripts/create_demo_users_ga03.py"],
        cwd=str(PROJECT_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )


def login(base_url: str, identifier: str, password: str) -> tuple[requests.Session, requests.Response]:
    session = requests.Session()
    response = session.post(
        f"{base_url}/auth/login",
        data={"identifier": identifier, "password": password},
        timeout=30,
        allow_redirects=False,
    )
    return session, response


def run_validation() -> dict[str, Any]:
    ensure_demo_users()
    report: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "result": False,
        "checks": [],
        "errors": [],
    }
    errors: list[str] = []
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = start_server(port)
    try:
        if not wait_for_server(base_url):
            errors.append("server did not start")
            return report

        root_response = requests.get(f"{base_url}/", timeout=30, allow_redirects=False)
        root_ok = root_response.status_code in {303, 307} and root_response.headers.get("location") == "/auth/login"
        report["checks"].append(
            {
                "name": "anonymous_root_redirect",
                "ok": root_ok,
                "expected": "/auth/login",
                "status_code": root_response.status_code,
                "location": root_response.headers.get("location"),
            }
        )
        if not root_ok:
            errors.append(f"GET / without session returned {root_response.status_code} {root_response.headers.get('location')}")

        login_page_response = requests.get(f"{base_url}/auth/login", timeout=30, allow_redirects=False)
        login_page_ok = login_page_response.status_code == 200
        report["checks"].append(
            {
                "name": "login_page",
                "ok": login_page_ok,
                "status_code": login_page_response.status_code,
            }
        )
        if not login_page_ok:
            errors.append(f"GET /auth/login returned {login_page_response.status_code}")

        ta02_anon = requests.get(f"{base_url}/ta02", timeout=30, allow_redirects=False)
        ta02_anon_ok = ta02_anon.status_code in {303, 307} and str(ta02_anon.headers.get("location", "")).startswith("/auth/login?next=")
        report["checks"].append(
            {
                "name": "ta02_requires_login",
                "ok": ta02_anon_ok,
                "status_code": ta02_anon.status_code,
                "location": ta02_anon.headers.get("location"),
            }
        )
        if not ta02_anon_ok:
            errors.append(f"GET /ta02 without session returned {ta02_anon.status_code} {ta02_anon.headers.get('location')}")

        client_session, client_login = login(base_url, "cliente", "Cliente123*")
        expected_client = get_default_redirect_for_role("cliente")
        client_login_ok = client_login.status_code == 303 and client_login.headers.get("location") == expected_client
        report["checks"].append(
            {
                "name": "cliente_login_redirect",
                "ok": client_login_ok,
                "status_code": client_login.status_code,
                "location": client_login.headers.get("location"),
                "expected": expected_client,
            }
        )
        if not client_login_ok:
            errors.append(f"cliente login redirect returned {client_login.status_code} {client_login.headers.get('location')}")

        client_forbidden = client_session.get(f"{base_url}/admin/security", timeout=30, allow_redirects=False)
        client_forbidden_ok = client_forbidden.status_code == 403
        report["checks"].append(
            {
                "name": "cliente_forbidden_admin_security",
                "ok": client_forbidden_ok,
                "status_code": client_forbidden.status_code,
            }
        )
        if not client_forbidden_ok:
            errors.append(f"cliente access to /admin/security returned {client_forbidden.status_code}")

        admin_session, admin_login = login(base_url, "superadmin", "Admin12345*")
        expected_admin = get_default_redirect_for_role("super_admin")
        admin_login_ok = admin_login.status_code == 303 and admin_login.headers.get("location") == expected_admin
        report["checks"].append(
            {
                "name": "superadmin_login_redirect",
                "ok": admin_login_ok,
                "status_code": admin_login.status_code,
                "location": admin_login.headers.get("location"),
                "expected": expected_admin,
            }
        )
        if not admin_login_ok:
            errors.append(f"superadmin login redirect returned {admin_login.status_code} {admin_login.headers.get('location')}")

        ta02_admin = admin_session.get(f"{base_url}/ta02", timeout=30, allow_redirects=False)
        ta02_admin_ok = ta02_admin.status_code == 200
        report["checks"].append(
            {
                "name": "ta02_superadmin_access",
                "ok": ta02_admin_ok,
                "status_code": ta02_admin.status_code,
            }
        )
        if not ta02_admin_ok:
            errors.append(f"GET /ta02 with superadmin returned {ta02_admin.status_code}")

    finally:
        stop_server(process)

    report["errors"] = errors
    report["result"] = not errors
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    report = run_validation()
    print(
        json.dumps(
            {
                "result": report["result"],
                "checks": len(report["checks"]),
                "errors": report["errors"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"report_path={REPORT_PATH}")


if __name__ == "__main__":
    main()
