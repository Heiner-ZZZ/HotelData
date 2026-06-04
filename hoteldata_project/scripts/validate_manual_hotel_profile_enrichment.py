from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "validate_manual_hotel_profile_enrichment.json"
ENRICH_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "enrich_ga03_display_dimensions.py"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(port: int) -> subprocess.Popen[str]:
    stdout_path = PROJECT_ROOT / "data" / "reports" / "validate_manual_hotel_profile_enrichment.stdout.log"
    stderr_path = PROJECT_ROOT / "data" / "reports" / "validate_manual_hotel_profile_enrichment.stderr.log"
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
    with opener.open(request, timeout=30) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def login_api(opener: urllib.request.OpenerDirector, base_url: str) -> tuple[bool, dict[str, Any]]:
    try:
        status, payload = json_request(
            opener,
            f"{base_url}/api/auth/login",
            method="POST",
            payload={"identifier": "superadmin", "password": "Admin12345*"},
        )
        return status == 200 and payload.get("authenticated") is True, payload
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return False, {"status": exc.code, "body": body}


def run_enrichment_script() -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(ENRICH_SCRIPT_PATH)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    parsed_stdout: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            parsed_stdout = json.loads(result.stdout)
        except json.JSONDecodeError:
            parsed_stdout = None
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": parsed_stdout if parsed_stdout is not None else result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def choose_demo_prop_id(db, opener: urllib.request.OpenerDirector, base_url: str) -> tuple[int, dict[str, Any]]:
    status, search_payload = json_request(opener, f"{base_url}/api/hotels/search")
    items = search_payload.get("items", [])
    if items:
        return int(items[0]["prop_id"]), {"status": status, "source": "api_search_top_item"}
    hotel = db.dim_hotels.find_one({}, {"_id": 0, "prop_id": 1})
    if not hotel:
        raise RuntimeError("No se encontró un prop_id demo en dim_hotels.")
    return int(hotel["prop_id"]), {"status": 200, "source": "dim_hotels_fallback"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate manual hotel profile enrichment.")
    parser.add_argument("--is-test", action="store_true", help="Keep the demo manual change instead of restoring the previous values.")
    args = parser.parse_args()

    db = get_database()
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    fact_count_before = int(db.fact_hotel_reservations.count_documents({}))

    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = start_server(port)
    try:
        if not wait_for_server(base_url):
            raise RuntimeError("No fue posible iniciar FastAPI para la validación.")

        opener = build_opener()
        login_ok, login_payload = login_api(opener, base_url)
        checks.append({"name": "api_auth_login", "ok": login_ok, "details": login_payload})
        if not login_ok:
            raise RuntimeError("No fue posible autenticar como superadmin.")

        prop_id, selection = choose_demo_prop_id(db, opener, base_url)
        checks.append({"name": "demo_prop_selection", "ok": True, "details": {"prop_id": prop_id, **selection}})

        status, original_profile_payload = json_request(opener, f"{base_url}/api/management/properties/{prop_id}/profile")
        checks.append({"name": "profile_get_before", "ok": status == 200, "details": {"status": status}})
        if status != 200:
            raise RuntimeError("No fue posible obtener el perfil inicial.")
        original_profile = original_profile_payload.get("profile", {})

        original_doc = db.dim_hotels.find_one({"prop_id": prop_id}, {"_id": 0})
        if not original_doc:
            raise RuntimeError("No se encontró el documento dim_hotels para el prop_id seleccionado.")

        suffix = " [Demo Manual]"
        new_display_name = f"{original_profile.get('display_name') or original_doc.get('display_name') or f'Hotel Partner {prop_id}'}{suffix}"
        payload = {
            "hotel_name": original_profile.get("hotel_name") or original_doc.get("hotel_name") or new_display_name,
            "display_name": new_display_name,
            "description": original_profile.get("description") or original_doc.get("description") or "",
            "display_country_label": original_profile.get("display_country_label") or original_doc.get("display_country_label") or "",
            "reason": "Validación automática manual profile enrichment",
            "changed_by": "validation_script",
        }

        restore_payload = {
            "hotel_name": original_profile.get("hotel_name") or original_doc.get("hotel_name") or "",
            "display_name": original_profile.get("display_name") or original_doc.get("display_name") or "",
            "description": original_profile.get("description") or original_doc.get("description") or "",
            "display_country_label": original_profile.get("display_country_label") or original_doc.get("display_country_label") or "",
            "reason": "Restauración posterior a validación automática",
            "changed_by": "validation_script",
        }

        status, updated_profile_payload = json_request(
            opener,
            f"{base_url}/api/management/properties/{prop_id}/profile",
            method="PUT",
            payload=payload,
        )
        checks.append({"name": "profile_put_manual_update", "ok": status == 200, "details": {"status": status}})
        if status != 200:
            raise RuntimeError("No fue posible guardar el nombre manual por API.")

        updated_doc = db.dim_hotels.find_one({"prop_id": prop_id}, {"_id": 0})
        checks.append(
            {
                "name": "dim_hotels_prop_id_stable",
                "ok": updated_doc is not None and int(updated_doc.get("prop_id") or 0) == prop_id,
                "details": {"prop_id": updated_doc.get("prop_id") if updated_doc else None},
            }
        )
        if not updated_doc or int(updated_doc.get("prop_id") or 0) != prop_id:
            errors.append("prop_id cambió o no se encontró después de la actualización manual.")

        checks.append(
            {
                "name": "dim_hotels_manual_override_true",
                "ok": bool(updated_doc.get("manual_override")) is True if updated_doc else False,
                "details": {"manual_override": updated_doc.get("manual_override") if updated_doc else None},
            }
        )
        if not updated_doc or bool(updated_doc.get("manual_override")) is not True:
            errors.append("manual_override no quedó en true.")

        change_doc = db.hotel_profile_changes.find_one(
            {"prop_id": prop_id, "field": "display_name", "new_value": new_display_name},
            sort=[("changed_at", -1)],
        )
        checks.append(
            {
                "name": "hotel_profile_changes_logged",
                "ok": change_doc is not None
                and str(change_doc.get("old_value") or "") == str(original_profile.get("display_name") or original_doc.get("display_name") or "")
                and str(change_doc.get("new_value") or "") == new_display_name,
                "details": {
                    "old_value": change_doc.get("old_value") if change_doc else None,
                    "new_value": change_doc.get("new_value") if change_doc else None,
                },
            }
        )
        if change_doc is None:
            errors.append("hotel_profile_changes no registró el cambio esperado.")

        original_generated_name_before_enrich = str(updated_doc.get("original_generated_name") or "") if updated_doc else ""
        checks.append(
            {
                "name": "original_generated_name_preserved_before_enrich",
                "ok": bool(original_generated_name_before_enrich),
                "details": {"original_generated_name": original_generated_name_before_enrich},
            }
        )
        if not original_generated_name_before_enrich:
            errors.append("original_generated_name no quedó preservado antes de ejecutar el enrich automático.")

        enrich_result = run_enrichment_script()
        checks.append({"name": "run_enrich_ga03_display_dimensions", "ok": enrich_result["ok"], "details": enrich_result})
        if not enrich_result["ok"]:
            raise RuntimeError("Falló enrich_ga03_display_dimensions.py durante la validación de preservación manual.")

        after_enrich_doc = db.dim_hotels.find_one({"prop_id": prop_id}, {"_id": 0})
        checks.append(
            {
                "name": "dim_hotels_prop_id_stable_after_enrich",
                "ok": after_enrich_doc is not None and int(after_enrich_doc.get("prop_id") or 0) == prop_id,
                "details": {"prop_id": after_enrich_doc.get("prop_id") if after_enrich_doc else None},
            }
        )
        if not after_enrich_doc or int(after_enrich_doc.get("prop_id") or 0) != prop_id:
            errors.append("prop_id cambió después de ejecutar enrich_ga03_display_dimensions.py.")

        checks.append(
            {
                "name": "display_name_manual_preserved_after_enrich",
                "ok": after_enrich_doc is not None and str(after_enrich_doc.get("display_name") or "") == new_display_name,
                "details": {"display_name": after_enrich_doc.get("display_name") if after_enrich_doc else None},
            }
        )
        if not after_enrich_doc or str(after_enrich_doc.get("display_name") or "") != new_display_name:
            errors.append("display_name manual fue sobrescrito por enrich_ga03_display_dimensions.py.")

        checks.append(
            {
                "name": "manual_override_protected_after_enrich",
                "ok": after_enrich_doc is not None and bool(after_enrich_doc.get("manual_override")) is True,
                "details": {"manual_override": after_enrich_doc.get("manual_override") if after_enrich_doc else None},
            }
        )
        if not after_enrich_doc or bool(after_enrich_doc.get("manual_override")) is not True:
            errors.append("manual_override dejó de estar protegido tras el enrich automático.")

        checks.append(
            {
                "name": "original_generated_name_preserved_after_enrich",
                "ok": after_enrich_doc is not None
                and str(after_enrich_doc.get("original_generated_name") or "") == original_generated_name_before_enrich,
                "details": {
                    "before": original_generated_name_before_enrich,
                    "after": after_enrich_doc.get("original_generated_name") if after_enrich_doc else None,
                },
            }
        )
        if not after_enrich_doc or str(after_enrich_doc.get("original_generated_name") or "") != original_generated_name_before_enrich:
            errors.append("original_generated_name no se preservó después del enrich automático.")

        status, search_after = json_request(opener, f"{base_url}/api/hotels/search")
        visible_in_search = any(
            int(item.get("prop_id") or 0) == prop_id and str(item.get("hotel_label") or "") == new_display_name
            for item in search_after.get("items", [])
        )
        checks.append(
            {
                "name": "api_hotels_search_uses_manual_name",
                "ok": status == 200 and visible_in_search,
                "details": {"status": status, "prop_id": prop_id, "display_name": new_display_name},
            }
        )
        if not visible_in_search:
            errors.append("La búsqueda pública no reflejó el nuevo nombre manual.")

        if not args.is_test:
            restore_status, _ = json_request(
                opener,
                f"{base_url}/api/management/properties/{prop_id}/profile",
                method="PUT",
                payload=restore_payload,
            )
            checks.append({"name": "profile_restore_previous_values", "ok": restore_status == 200, "details": {"status": restore_status}})
            if restore_status != 200:
                errors.append("No fue posible restaurar el perfil original tras la validación.")
    finally:
        stop_server(process)

    fact_count_after = int(db.fact_hotel_reservations.count_documents({}))
    checks.append(
        {
            "name": "fact_hotel_reservations_not_modified",
            "ok": fact_count_before == fact_count_after,
            "details": {"before": fact_count_before, "after": fact_count_after},
        }
    )
    if fact_count_before != fact_count_after:
        errors.append("fact_hotel_reservations fue modificado durante la validación y no debía ocurrir.")

    report = {
        "generated_at": utc_now_iso(),
        "result": not errors,
        "is_test": args.is_test,
        "checks": checks,
        "errors": errors,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print(f"report_path={REPORT_PATH}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
