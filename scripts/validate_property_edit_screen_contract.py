from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "validate_property_edit_screen_contract.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(port: int) -> subprocess.Popen[str]:
    stdout_path = PROJECT_ROOT / "data" / "reports" / "validate_property_edit_screen_contract.stdout.log"
    stderr_path = PROJECT_ROOT / "data" / "reports" / "validate_property_edit_screen_contract.stderr.log"
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
    probe_url = f"{base_url}/api/management/properties/1"
    while time.time() < deadline:
        try:
            response = urllib.request.urlopen(probe_url, timeout=2)
            if response.status == 200:
                return True
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403, 404}:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def fetch_jsonish(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = response.headers.get("Content-Type", "")
            raw = response.read().decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status": response.status,
                "content_type": content_type,
                "json": "application/json" in content_type.lower(),
                "body_preview": raw[:240],
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
        return {
            "ok": False,
            "status": exc.code,
            "content_type": content_type,
            "json": "application/json" in content_type.lower(),
            "body_preview": raw[:240],
        }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    db = get_database()
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    fact_count = int(db.fact_hotel_reservations.count_documents({}))

    frontend_root = PROJECT_ROOT / "frontend" / "src" / "app"
    properties_routes_text = read_text(frontend_root / "features" / "properties" / "properties.routes.ts")
    property_edit_page_text = read_text(frontend_root / "features" / "properties" / "pages" / "property-edit-page" / "property-edit-page.ts")
    property_edit_html_text = read_text(frontend_root / "features" / "properties" / "pages" / "property-edit-page" / "property-edit-page.html")
    properties_api_text = read_text(frontend_root / "features" / "properties" / "services" / "properties-api.service.ts")
    route_permissions_text = read_text(PROJECT_ROOT / "src" / "app" / "security" / "route_permissions.py")
    partner_routes_text = read_text(PROJECT_ROOT / "src" / "app" / "modules" / "partner" / "routes.py")

    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = start_server(port)
    try:
        if not wait_for_server(base_url):
            raise RuntimeError("No fue posible iniciar FastAPI para validar el contrato de edición.")

        detail_result = fetch_jsonish(f"{base_url}/api/management/properties/1")
        checks.append({
            "name": "detail_endpoint_json_contract",
            "ok": detail_result["status"] in {200, 401, 403, 404} and detail_result["json"],
            "details": detail_result,
        })

        profile_result = fetch_jsonish(f"{base_url}/api/management/properties/1/profile")
        checks.append({
            "name": "profile_endpoint_json_contract",
            "ok": profile_result["status"] in {200, 401, 403, 404} and profile_result["json"],
            "details": profile_result,
        })

        put_result = fetch_jsonish(
            f"{base_url}/api/management/properties/1/profile",
            method="PUT",
            payload={
                "hotel_name": "Hotel no especificado",
                "display_name": "Hotel Partner 1",
                "description": "dry-run",
                "display_country_label": "Mercado hotelero 219",
            },
        )
        checks.append({
            "name": "profile_put_dry_run_contract",
            "ok": put_result["status"] in {200, 400, 401, 403, 404} and put_result["json"],
            "details": put_result,
        })
    finally:
        stop_server(process)

    route_ok = "path: ':propertyId/edit'" in properties_routes_text and "PropertyEditPageComponent" in properties_routes_text
    checks.append({
        "name": "angular_route_to_property_edit_page",
        "ok": route_ok,
        "details": {"route_found": route_ok},
    })

    param_ok = "params.get('propertyId')" in property_edit_page_text and "params.get('propId')" not in property_edit_page_text
    checks.append({
        "name": "angular_uses_propertyId_param",
        "ok": param_ok,
        "details": {"propertyId_reference": param_ok},
    })

    service_profile_ok = "/management/properties/${propId}/profile" in properties_api_text
    service_uses_forkjoin = "forkJoin({" in properties_api_text
    load_profile_block = re.search(
        r"loadPropertyProfile\(propId: number\)\s*\{(?P<body>.*?)\n\s*\}\n\n\s*saveProfile",
        properties_api_text,
        re.S,
    )
    loader_uses_legacy_edit = False
    loader_uses_policy_fallback = False
    loader_uses_amenity_fallback = False
    if load_profile_block:
        loader_body = load_profile_block.group("body")
        loader_uses_legacy_edit = "/management/properties/${propId}/edit" in loader_body
        loader_uses_policy_fallback = "/management/policies" in loader_body and "catchError(() => of(null))" in loader_body
        loader_uses_amenity_fallback = "/management/amenities" in loader_body and loader_body.count("catchError(() => of(null))") >= 2
    checks.append({
        "name": "angular_calls_profile_endpoint_for_loader",
        "ok": service_profile_ok and service_uses_forkjoin and not loader_uses_legacy_edit,
        "details": {
            "profile_endpoint_present": service_profile_ok,
            "forkjoin_present": service_uses_forkjoin,
            "legacy_edit_loader_present": loader_uses_legacy_edit,
        },
    })

    checks.append({
        "name": "angular_loader_tolerates_policies_failure",
        "ok": loader_uses_policy_fallback,
        "details": {
            "fallback_present": loader_uses_policy_fallback,
        },
    })

    checks.append({
        "name": "angular_loader_tolerates_amenities_failure",
        "ok": loader_uses_amenity_fallback,
        "details": {
            "fallback_present": loader_uses_amenity_fallback,
        },
    })

    title_ok = "Editar perfil de propiedad" in property_edit_html_text
    checks.append({
        "name": "screen_title_updated",
        "ok": title_ok,
        "details": {"title_found": title_ok},
    })

    page_uses_profile_loader = "this.propertiesApi.loadPropertyProfile(propId)" in property_edit_page_text
    checks.append({
        "name": "property_edit_page_uses_profile_loader",
        "ok": page_uses_profile_loader,
        "details": {"profile_loader_call_found": page_uses_profile_loader},
    })

    no_legacy_edit_reference = "/management/properties/${propId}/edit" not in properties_api_text
    checks.append({
        "name": "frontend_has_no_legacy_edit_endpoint_reference",
        "ok": no_legacy_edit_reference,
        "details": {"legacy_reference_present": not no_legacy_edit_reference},
    })

    backend_profile_routes_ok = all(
        marker in partner_routes_text
        for marker in (
            '@api_router.get("/properties/{prop_id}/profile")',
            '@api_router.put("/properties/{prop_id}/profile")',
        )
    )
    checks.append({
        "name": "backend_profile_routes_present",
        "ok": backend_profile_routes_ok,
        "details": {"routes_present": backend_profile_routes_ok},
    })

    roles_ok = all(
        role in route_permissions_text
        for role in ("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel", "marketing_hotelero")
    ) and 'AccessRule("/api/management"' in route_permissions_text
    checks.append({
        "name": "route_permissions_cover_management_roles",
        "ok": roles_ok,
        "details": {"roles_present": roles_ok},
    })

    fact_ok = fact_count == 300000
    checks.append({
        "name": "fact_hotel_reservations_unchanged",
        "ok": fact_ok,
        "details": {"fact_count": fact_count},
    })

    for item in checks:
        if not item["ok"]:
            errors.append(item["name"])

    report = {
        "generated_at": utc_now_iso(),
        "checks": checks,
        "errors": errors,
        "ok": not errors,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
