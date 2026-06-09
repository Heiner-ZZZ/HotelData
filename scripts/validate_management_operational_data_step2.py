from __future__ import annotations

import json
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
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "validate_management_operational_data_step2.json"
CONTRACT_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "validate_frontend_backend_contract.py"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(port: int) -> subprocess.Popen[str]:
    stdout_path = PROJECT_ROOT / "data" / "reports" / "validate_management_operational_data_step2.stdout.log"
    stderr_path = PROJECT_ROOT / "data" / "reports" / "validate_management_operational_data_step2.stderr.log"
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
            response = urllib.request.urlopen(f"{base_url}/auth/login", timeout=2)
            if response.status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def build_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor())


def json_request(
    opener: urllib.request.OpenerDirector,
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with opener.open(request, timeout=40) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def login_api(opener: urllib.request.OpenerDirector, base_url: str) -> dict[str, Any]:
    status, payload = json_request(
        opener,
        f"{base_url}/api/auth/login",
        method="POST",
        payload={"identifier": "superadmin", "password": "Admin12345*"},
    )
    return {"status": status, "payload": payload, "ok": status == 200 and payload.get("authenticated") is True}


def seeded_prop_id(db) -> int:
    prop_ids = db.room_types.distinct("prop_id")
    if prop_ids:
        return int(sorted(int(item) for item in prop_ids)[0])
    fallback = db.dim_hotels.find_one({}, {"_id": 0, "prop_id": 1})
    if not fallback:
        raise RuntimeError("No se encontró un prop_id demo para validar management.")
    return int(fallback["prop_id"])


def run_contract_validation(base_url: str, prop_id: int) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(CONTRACT_SCRIPT_PATH), "--base-url", base_url, "--prop-id", str(prop_id)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    parsed = {}
    if result.stdout.strip():
        parsed = json.loads(result.stdout)
    return {
        "ok": result.returncode == 0 and int(parsed.get("error_count", 1)) == 0,
        "returncode": result.returncode,
        "summary": parsed,
        "stderr": result.stderr.strip(),
    }


def check(name: str, ok: bool, details: dict[str, Any], checks: list[dict[str, Any]], errors: list[str], message: str) -> None:
    checks.append({"name": name, "ok": ok, "details": details})
    if not ok:
        errors.append(message)


def main() -> int:
    db = get_database()
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    fact_count_before = int(db.fact_hotel_reservations.count_documents({}))
    prop_id = seeded_prop_id(db)

    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = start_server(port)
    try:
        if not wait_for_server(base_url):
            raise RuntimeError("No fue posible iniciar FastAPI para la validación del Step 2.")

        opener = build_opener()
        login_result = login_api(opener, base_url)
        check("api_auth_login", login_result["ok"], login_result, checks, errors, "No fue posible autenticar como superadmin.")
        if not login_result["ok"]:
            raise RuntimeError("Login falló.")

        status, overview = json_request(opener, f"{base_url}/api/dashboard/overview")
        headline = overview.get("overview", {}).get("headline", {})
        check(
            "dashboard_overview_operational_metrics",
            status == 200
            and int(headline.get("configured_room_types", 0)) > 0
            and int(headline.get("physical_rooms", 0)) > 0
            and int(headline.get("inventory_days", 0)) > 0
            and int(headline.get("rate_plans", 0)) > 0,
            {"status": status, "headline": headline},
            checks,
            errors,
            "Dashboard overview no expone las métricas operativas esperadas.",
        )

        status, properties = json_request(opener, f"{base_url}/api/management/properties")
        property_items = properties.get("items", [])
        property_match = next((item for item in property_items if int(item.get("prop_id") or 0) == prop_id), None)
        check(
            "management_properties_operational_indicators",
            status == 200 and property_match is not None and isinstance(property_match.get("operational"), dict),
            {"status": status, "prop_id": prop_id, "property": property_match},
            checks,
            errors,
            "El listado de propiedades no devolvió indicadores operativos.",
        )

        status, rooms_payload = json_request(opener, f"{base_url}/api/management/rooms?prop_id={prop_id}")
        room_types = rooms_payload.get("room_types", [])
        hotel_rooms = rooms_payload.get("hotel_rooms", [])
        check(
            "management_rooms_connected",
            status == 200 and (len(room_types) >= 2 or len(hotel_rooms) >= 2),
            {"status": status, "room_types": len(room_types), "hotel_rooms": len(hotel_rooms)},
            checks,
            errors,
            "Rooms no devolvió datos de room_types/hotel_rooms.",
        )

        status, availability_payload = json_request(opener, f"{base_url}/api/management/availability?prop_id={prop_id}")
        inventory_items = availability_payload.get("inventory_items", [])
        availability_blocks = availability_payload.get("availability_blocks", [])
        blackout_items = availability_payload.get("blackout_items", [])
        check(
            "management_availability_connected",
            status == 200 and len(inventory_items) >= 14,
            {
                "status": status,
                "inventory_items": len(inventory_items),
                "availability_blocks": len(availability_blocks),
                "blackout_items": len(blackout_items),
            },
            checks,
            errors,
            "Availability no devolvió inventario operativo suficiente.",
        )

        status, rates_payload = json_request(opener, f"{base_url}/api/management/rates?prop_id={prop_id}")
        rate_plans = rates_payload.get("rate_plans", [])
        rate_calendar = rates_payload.get("calendar", [])
        check(
            "management_rates_connected",
            status == 200 and len(rate_plans) >= 2 and len(rate_calendar) >= 14,
            {"status": status, "rate_plans": len(rate_plans), "rate_calendar": len(rate_calendar)},
            checks,
            errors,
            "Rates no devolvió planes y calendario demo.",
        )

        status, policies_payload = json_request(opener, f"{base_url}/api/management/policies?prop_id={prop_id}")
        policies_count = int(db.hotel_policies.count_documents({}))
        check(
            "management_policies_connected",
            status == 200 and bool(policies_payload.get("policies")) and policies_count >= 5,
            {"status": status, "policies_count": policies_count},
            checks,
            errors,
            "Policies no devolvió una política válida o la colección no quedó poblada.",
        )

        status, amenities_payload = json_request(opener, f"{base_url}/api/management/amenities?prop_id={prop_id}")
        images = amenities_payload.get("images", [])
        content_page = amenities_payload.get("content_page", {})
        check(
            "management_amenities_connected",
            status == 200 and bool(content_page.get("description")) and len(images) >= 2,
            {"status": status, "images": len(images), "content_page": content_page},
            checks,
            errors,
            "Amenities no devolvió contenido e imágenes conectadas.",
        )

        status, reports_payload = json_request(opener, f"{base_url}/api/management/reports")
        check(
            "management_reports_connected",
            status == 200 and len(reports_payload.get("top_hotels_by_revenue", [])) > 0,
            {"status": status, "top_hotels": len(reports_payload.get("top_hotels_by_revenue", []))},
            checks,
            errors,
            "Reports no devolvió top hoteles por revenue.",
        )

        manual_doc = db.dim_hotels.find_one({"manual_override": True}, {"_id": 0, "prop_id": 1, "display_name": 1})
        if manual_doc:
            manual_prop_id = int(manual_doc["prop_id"])
            status, manual_detail = json_request(opener, f"{base_url}/api/management/properties/{manual_prop_id}")
            hotel_payload = manual_detail.get("hotel", {})
            check(
                "manual_override_display_name_respected",
                status == 200
                and bool(hotel_payload.get("manual_override"))
                and str(hotel_payload.get("display_name") or "") == str(manual_doc.get("display_name") or ""),
                {"status": status, "prop_id": manual_prop_id, "hotel": hotel_payload},
                checks,
                errors,
                "El endpoint de propiedad no respetó el display_name manual.",
            )

        fact_count_after = int(db.fact_hotel_reservations.count_documents({}))
        check(
            "fact_hotel_reservations_unchanged",
            fact_count_before == fact_count_after == 300000,
            {"before": fact_count_before, "after": fact_count_after},
            checks,
            errors,
            "fact_hotel_reservations cambió durante la validación.",
        )

        contract_validation = run_contract_validation(base_url, prop_id)
        check(
            "frontend_backend_contract_zero_errors",
            contract_validation["ok"],
            contract_validation,
            checks,
            errors,
            "validate_frontend_backend_contract.py reportó errores.",
        )
    finally:
        stop_server(process)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": utc_now_iso(),
        "prop_id": prop_id,
        "fact_count_before": fact_count_before,
        "checks": checks,
        "errors": errors,
        "ok": not errors,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
