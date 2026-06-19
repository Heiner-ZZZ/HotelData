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
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "ga03_web_integrations_report.json"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_database
ROUTES_TO_VALIDATE = [
    "/auth/login",
    "/auth/me",
    "/admin/security",
    "/system/redis-status",
    "/hotels/search",
    "/partner/hotels",
    "/analytics/reservations",
    "/analytics/conversion",
    "/analytics/revenue",
    "/analytics/promotions",
]
SECURITY_COLLECTIONS = [
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "user_sessions",
    "user_activity_logs",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_result(name: str, ok: bool, details: dict[str, Any] | None = None, error: str | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "details": details or {},
        "error": error,
    }


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def import_app() -> tuple[Any | None, dict[str, Any], str | None]:
    try:
        from src.app.main import app

        return app, {"title": app.title, "route_count": len(app.routes)}, None
    except Exception as exc:  # pragma: no cover - hard failure path
        return None, {}, str(exc)


def validate_route_definitions(app: Any) -> tuple[bool, dict[str, Any], list[str]]:
    registered = {getattr(route, "path", "") for route in app.routes}
    missing = [route for route in ROUTES_TO_VALIDATE if route not in registered]
    return not missing, {"registered": sorted(registered & set(ROUTES_TO_VALIDATE)), "missing": missing}, missing


def validate_mongodb() -> tuple[bool, dict[str, Any], list[str]]:
    errors: list[str] = []
    try:
        db = get_database()
        db.command("ping")
        existing = set(db.list_collection_names())
        missing = [name for name in SECURITY_COLLECTIONS if name not in existing]
        if missing:
            errors.extend([f"Missing collection: {name}" for name in missing])
        return (
            not errors,
            {
                "database": db.name,
                "collections_present": sorted(existing.intersection(SECURITY_COLLECTIONS)),
                "collections_missing": missing,
            },
            errors,
        )
    except Exception as exc:  # pragma: no cover - depends on local service state
        return False, {}, [str(exc)]


def start_server(port: int) -> subprocess.Popen[str]:
    stderr_path = PROJECT_ROOT / "data" / "reports" / "ga03_web_integrations.stderr.log"
    stdout_path = PROJECT_ROOT / "data" / "reports" / "ga03_web_integrations.stdout.log"
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_handle = open(stdout_path, "w", encoding="utf-8")
    stderr_handle = open(stderr_path, "w", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
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


def wait_for_server(base_url: str, timeout_seconds: int = 20) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/system/redis-status", timeout=2)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


def validate_http_routes(base_url: str) -> tuple[list[dict[str, Any]], list[str]]:
    validations: list[dict[str, Any]] = []
    errors: list[str] = []
    expected = {
        "/auth/login": {200},
        "/auth/me": {200, 303},
        "/admin/security": {200, 303},
        "/system/redis-status": {200},
        "/hotels/search": {200},
        "/partner/hotels": {200},
        "/analytics/reservations": {200},
        "/analytics/conversion": {200},
        "/analytics/revenue": {200},
        "/analytics/promotions": {200},
    }
    session = requests.Session()
    for route in ROUTES_TO_VALIDATE:
        try:
            response = session.get(f"{base_url}{route}", timeout=30, allow_redirects=False)
            route_ok = response.status_code in expected[route]
            details: dict[str, Any] = {
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "location": response.headers.get("location"),
            }
            if route == "/system/redis-status":
                try:
                    details["json"] = response.json()
                except Exception as exc:
                    route_ok = False
                    errors.append(f"{route}: invalid json ({exc})")
            validations.append(make_result(route, route_ok, details, None if route_ok else f"Unexpected status {response.status_code}"))
            if not route_ok and route != "/system/redis-status":
                errors.append(f"{route}: unexpected status {response.status_code}")
        except Exception as exc:  # pragma: no cover - network/runtime path
            validations.append(make_result(route, False, {}, str(exc)))
            errors.append(f"{route}: {exc}")
    return validations, errors


def validate_query_rendering(base_url: str) -> tuple[list[dict[str, Any]], list[str]]:
    checks = [
        "/hotels/search?min_stars=3&promotion=yes&page=1",
        "/partner/hotels?q=1",
        "/analytics/visitor-markets",
    ]
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for route in checks:
        try:
            response = requests.get(f"{base_url}{route}", timeout=30)
            ok = response.status_code == 200 and "text/html" in (response.headers.get("content-type") or "")
            results.append(
                make_result(
                    route,
                    ok,
                    {"status_code": response.status_code, "content_type": response.headers.get("content-type"), "body_size": len(response.text)},
                    None if ok else "Expected HTML 200 response",
                )
            )
            if not ok:
                errors.append(f"{route}: expected HTML 200 response")
        except Exception as exc:
            results.append(make_result(route, False, {}, str(exc)))
            errors.append(f"{route}: {exc}")
    return results, errors


def run_validation() -> dict[str, Any]:
    report: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "summary": {"ok": False, "total_routes_validated": len(ROUTES_TO_VALIDATE), "errors": []},
        "checks": [],
    }
    all_errors: list[str] = []

    app, app_details, import_error = import_app()
    report["checks"].append(make_result("app_import", app is not None, app_details, import_error))
    if app is None:
        all_errors.append(f"app_import: {import_error}")
    else:
        ok, details, route_errors = validate_route_definitions(app)
        report["checks"].append(make_result("route_definitions", ok, details, None if ok else "Missing required routes"))
        all_errors.extend([f"route_definitions: {item}" for item in route_errors])

    mongo_ok, mongo_details, mongo_errors = validate_mongodb()
    report["checks"].append(make_result("mongodb_and_security_collections", mongo_ok, mongo_details, None if mongo_ok else "MongoDB/security validation failed"))
    all_errors.extend([f"mongodb: {item}" for item in mongo_errors])

    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = start_server(port)
    try:
        if not wait_for_server(base_url):
            report["checks"].append(make_result("web_server_boot", False, {"base_url": base_url}, "Timed out waiting for app server"))
            all_errors.append("web_server_boot: timed out waiting for app server")
        else:
            report["checks"].append(make_result("web_server_boot", True, {"base_url": base_url}))
            route_checks, route_errors = validate_http_routes(base_url)
            report["checks"].extend(route_checks)
            all_errors.extend(route_errors)

            query_checks, query_errors = validate_query_rendering(base_url)
            report["checks"].extend(query_checks)
            all_errors.extend(query_errors)
    finally:
        stop_server(process)

    report["summary"]["errors"] = all_errors
    report["summary"]["ok"] = not all_errors
    report["summary"]["fail"] = len(all_errors)
    report["summary"]["pass"] = len([item for item in report["checks"] if item["ok"]])
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    return report


def main() -> None:
    report = run_validation()
    print(json.dumps(report["summary"], indent=2, ensure_ascii=True))
    print(f"report_path={REPORT_PATH}")


if __name__ == "__main__":
    main()
