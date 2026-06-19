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
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "ga03_role_access_report.json"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.security.navigation import get_default_redirect_for_role


USERS = {
    "super_admin": {"username": "superadmin", "password": "Admin12345*"},
    "operador_datos": {"username": "operador", "password": "Operador123*"},
    "auditor_datos": {"username": "auditor", "password": "Auditor123*"},
    "hotel_partner": {"username": "partner", "password": "Partner123*"},
    "gerente_hotel": {"username": "gerente", "password": "Gerente123*"},
    "revenue_manager": {"username": "revenue", "password": "Revenue123*"},
    "marketing_hotelero": {"username": "marketing", "password": "Marketing123*"},
    "cliente": {"username": "cliente", "password": "Cliente123*"},
}


ROLE_CHECKS = {
    "cliente": {
        "allowed": ["/hotels/search", "/reservations", "/auth/me"],
        "forbidden": ["/admin/security", "/admin/users", "/etl-status", "/ta02/crud", "/revenue/rate-plans", "/partner/hotels"],
    },
    "hotel_partner": {
        "allowed": ["/partner/hotels", "/partner/manual-reservations/new", "/auth/me"],
        "forbidden": ["/admin/security", "/admin/users", "/etl-status"],
    },
    "gerente_hotel": {
        "allowed": ["/partner/hotels", "/partner/manual-reservations/new", "/partner/hotels/1/inventory", "/auth/me"],
        "forbidden": ["/admin/security", "/admin/users", "/etl-status"],
    },
    "revenue_manager": {
        "allowed": ["/analytics/reservations", "/analytics/revenue", "/revenue/rate-plans", "/revenue/promotions"],
        "forbidden": ["/admin/security", "/admin/users", "/etl-status"],
    },
    "marketing_hotelero": {
        "allowed": ["/partner/hotels", "/revenue/promotions", "/analytics/promotions", "/auth/me"],
        "forbidden": ["/admin/security", "/admin/users", "/etl-status", "/revenue/rate-plans/new"],
    },
    "operador_datos": {
        "allowed": ["/etl-status", "/system/redis-status"],
        "forbidden": ["/admin/security"],
    },
    "auditor_datos": {
        "allowed": ["/analytics/reservations", "/analytics/conversion", "/analytics/revenue"],
        "forbidden": ["/admin/security", "/admin/users", "/revenue/rate-plans"],
    },
    "super_admin": {
        "allowed": ["/admin/security", "/admin/users", "/etl-status", "/ta02/crud", "/revenue/rate-plans", "/partner/hotels", "/analytics/reservations", "/hotels/search"],
        "forbidden": [],
    },
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(port: int) -> subprocess.Popen[str]:
    stdout_path = PROJECT_ROOT / "data" / "reports" / "ga03_role_access.stdout.log"
    stderr_path = PROJECT_ROOT / "data" / "reports" / "ga03_role_access.stderr.log"
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
    subprocess.run([sys.executable, "scripts/create_demo_users_ga03.py"], cwd=str(PROJECT_ROOT), check=True, capture_output=True, text=True)


def login(base_url: str, role_name: str) -> tuple[requests.Session, dict[str, Any]]:
    user = USERS[role_name]
    session = requests.Session()
    response = session.post(
        f"{base_url}/auth/login",
        data={"identifier": user["username"], "password": user["password"]},
        timeout=30,
        allow_redirects=False,
    )
    return session, {"status_code": response.status_code, "location": response.headers.get("location")}


def run_validation() -> dict[str, Any]:
    ensure_demo_users()
    report: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "result": False,
        "total_users_tested": 0,
        "allowed_checks_ok": 0,
        "forbidden_checks_ok": 0,
        "errors": [],
        "checks": [],
    }
    errors: list[str] = []
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = start_server(port)
    try:
        if not wait_for_server(base_url):
            errors.append("server did not start")
            return report

        anonymous_root = requests.get(f"{base_url}/", timeout=30, allow_redirects=False)
        anonymous_ok = anonymous_root.status_code == 303 and anonymous_root.headers.get("location") == "/auth/login"
        report["checks"].append({"role": "anonymous", "route": "/", "expected": "/auth/login", "actual": anonymous_root.headers.get("location"), "ok": anonymous_ok})
        if not anonymous_ok:
            errors.append(f"anonymous / expected redirect to /auth/login, got {anonymous_root.status_code} {anonymous_root.headers.get('location')}")

        for role_name, route_sets in ROLE_CHECKS.items():
            session, login_result = login(base_url, role_name)
            report["total_users_tested"] += 1
            expected_default = get_default_redirect_for_role(role_name)
            login_ok = login_result["status_code"] == 303 and login_result["location"] == expected_default
            report["checks"].append({"role": role_name, "route": "/auth/login[POST]", "expected": expected_default, "actual": login_result, "ok": login_ok})
            if not login_ok:
                errors.append(f"{role_name}: login redirect expected {expected_default}, got {login_result}")

            root_response = session.get(f"{base_url}/", timeout=30, allow_redirects=False)
            root_ok = root_response.status_code == 303 and root_response.headers.get("location") == expected_default
            report["checks"].append({"role": role_name, "route": "/", "expected": expected_default, "actual": root_response.headers.get("location"), "ok": root_ok})
            if not root_ok:
                errors.append(f"{role_name}: root redirect expected {expected_default}, got {root_response.status_code} {root_response.headers.get('location')}")

            for route in route_sets["allowed"]:
                response = session.get(f"{base_url}{route}", timeout=30, allow_redirects=False)
                ok = response.status_code == 200
                report["checks"].append({"role": role_name, "route": route, "expected": 200, "actual": response.status_code, "ok": ok})
                if ok:
                    report["allowed_checks_ok"] += 1
                else:
                    errors.append(f"{role_name}: allowed route {route} returned {response.status_code}")

            for route in route_sets["forbidden"]:
                response = session.get(f"{base_url}{route}", timeout=30, allow_redirects=False)
                ok = response.status_code == 403
                report["checks"].append({"role": role_name, "route": route, "expected": 403, "actual": response.status_code, "ok": ok})
                if ok:
                    report["forbidden_checks_ok"] += 1
                else:
                    errors.append(f"{role_name}: forbidden route {route} returned {response.status_code}")
    finally:
        stop_server(process)

    report["errors"] = errors
    report["result"] = not errors
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return report


def main() -> None:
    report = run_validation()
    print(
        json.dumps(
            {
                "result": report["result"],
                "total_users_tested": report["total_users_tested"],
                "allowed_checks_ok": report["allowed_checks_ok"],
                "forbidden_checks_ok": report["forbidden_checks_ok"],
                "errors": report["errors"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"report_path={REPORT_PATH}")


if __name__ == "__main__":
    main()
