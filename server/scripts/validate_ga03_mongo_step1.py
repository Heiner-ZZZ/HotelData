from __future__ import annotations

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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "mongodb_model_audit.json"
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "validate_ga03_mongo_step1.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(port: int) -> subprocess.Popen[str]:
    stdout_path = PROJECT_ROOT / "data" / "reports" / "validate_ga03_mongo_step1.stdout.log"
    stderr_path = PROJECT_ROOT / "data" / "reports" / "validate_ga03_mongo_step1.stderr.log"
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


def login(opener: urllib.request.OpenerDirector, base_url: str, identifier: str, password: str) -> tuple[bool, dict[str, Any]]:
    body = urllib.parse.urlencode({"identifier": identifier, "password": password}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/auth/login",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        response = opener.open(request, timeout=20)
        return response.status in {200, 303}, {"status": response.status, "final_url": response.geturl()}
    except urllib.error.HTTPError as exc:
        return False, {"status": exc.code, "error": exc.reason}
    except Exception as exc:
        return False, {"status": None, "error": str(exc)}


def fetch_json(opener: urllib.request.OpenerDirector, url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with opener.open(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    db = get_database()
    fact_count_current = int(db.fact_hotel_reservations.count_documents({}))
    fact_count_expected = fact_count_current
    if AUDIT_REPORT_PATH.exists():
        audit = json.loads(AUDIT_REPORT_PATH.read_text(encoding="utf-8"))
        fact_count_expected = int(audit.get("fact_metrics", {}).get("total_rows", fact_count_current))

    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    site_name_count = int(db.dim_sites.count_documents({"site_name": {"$exists": True, "$nin": [None, ""]}}))
    checks.append({"name": "dim_sites.site_name", "ok": site_name_count == 32, "details": {"count": site_name_count}})
    if site_name_count != 32:
        errors.append(f"dim_sites.site_name esperado 32 y actual {site_name_count}")

    collection_expectations = {
        "room_types": int(db.room_types.count_documents({})),
        "room_inventory_calendar": int(db.room_inventory_calendar.count_documents({})),
        "rate_plans": int(db.rate_plans.count_documents({})),
        "hotel_rate_calendar": int(db.hotel_rate_calendar.count_documents({})),
        "hotel_policies": int(db.hotel_policies.count_documents({})),
        "hotel_content_pages": int(db.hotel_content_pages.count_documents({})),
        "hotel_images": int(db.hotel_images.count_documents({})),
        "promotion_campaigns": int(db.promotion_campaigns.count_documents({})),
    }
    for name, count in collection_expectations.items():
        ok = count > 0
        checks.append({"name": name, "ok": ok, "details": {"count": count}})
        if not ok:
            errors.append(f"{name} no tiene datos después del seed demo")

    coupon_count = int(db.coupon_codes.count_documents({}))
    checks.append({"name": "coupon_codes", "ok": coupon_count > 0, "details": {"count": coupon_count}})
    if coupon_count <= 0:
        errors.append("coupon_codes no tiene datos después del seed demo")

    fact_unchanged = fact_count_current == fact_count_expected
    checks.append(
        {
            "name": "fact_hotel_reservations_count",
            "ok": fact_unchanged,
            "details": {"expected": fact_count_expected, "current": fact_count_current},
        }
    )
    if not fact_unchanged:
        errors.append(
            f"fact_hotel_reservations cambió: esperado {fact_count_expected} y actual {fact_count_current}"
        )

    total_reservations_expected = int(db.fact_hotel_reservations.count_documents({"reserva_bool": True}))
    total_clicks_expected = int(db.fact_hotel_reservations.count_documents({"click_bool": True}))
    total_events_expected = fact_count_current
    promotions_expected = int(db.fact_hotel_reservations.count_documents({"promotion_flag": True}))
    gross_revenue_expected = round(
        float(
            next(
                db.fact_hotel_reservations.aggregate(
                    [{"$group": {"_id": None, "gross_revenue": {"$sum": "$reservas_brutas_usd"}, "avg_price": {"$avg": "$price_usd"}}}]
                ),
                {},
            ).get("gross_revenue", 0.0)
        ),
        2,
    )
    avg_price_expected = round(
        float(
            next(
                db.fact_hotel_reservations.aggregate(
                    [{"$group": {"_id": None, "gross_revenue": {"$sum": "$reservas_brutas_usd"}, "avg_price": {"$avg": "$price_usd"}}}]
                ),
                {},
            ).get("avg_price", 0.0)
        ),
        2,
    )

    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = start_server(port)
    dashboard_payload: dict[str, Any] = {}
    try:
        if not wait_for_server(base_url):
            raise RuntimeError("No fue posible iniciar el servidor FastAPI para validación.")
        opener = build_opener()
        login_ok, login_details = login(opener, base_url, "superadmin", "Admin12345*")
        login_optional_ok = login_ok or login_details.get("status") == 404
        checks.append({"name": "dashboard_login_superadmin_optional", "ok": login_optional_ok, "details": login_details})
        dashboard_payload = fetch_json(opener, f"{base_url}/api/dashboard/overview")
    finally:
        stop_server(process)

    headline = dashboard_payload.get("overview", {}).get("headline", {})
    dashboard_checks = {
        "dashboard.total_events": int(headline.get("total_events", 0)) == total_events_expected,
        "dashboard.total_reservations": int(headline.get("total_reservations", headline.get("bookings", 0)) or 0)
        == total_reservations_expected,
        "dashboard.total_clicks": int(headline.get("total_clicks", 0) or 0) == total_clicks_expected,
        "dashboard.promotions": int(headline.get("promotions", 0) or 0) == promotions_expected,
        "dashboard.rejected_records": int(headline.get("rejected_records", 0) or 0)
        == int(db.rejected_records.count_documents({})),
        "dashboard.gross_revenue": round(float(headline.get("gross_revenue", 0) or 0), 2) == gross_revenue_expected,
        "dashboard.avg_price": round(float(headline.get("avg_price", 0) or 0), 2) == avg_price_expected,
        "dashboard.total_reservations_gt_zero": int(
            headline.get("total_reservations", headline.get("bookings", 0)) or 0
        )
        > 0,
    }
    for name, ok in dashboard_checks.items():
        checks.append({"name": name, "ok": ok, "details": {"headline": headline}})
        if not ok:
            errors.append(f"Fallo validación {name}")

    report = {
        "generated_at": utc_now_iso(),
        "result": not errors,
        "checks": checks,
        "errors": errors,
        "expected_metrics": {
            "total_events": total_events_expected,
            "total_reservations": total_reservations_expected,
            "total_clicks": total_clicks_expected,
            "promotions": promotions_expected,
            "gross_revenue": gross_revenue_expected,
            "avg_price": avg_price_expected,
        },
        "dashboard_headline": headline,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"report_path={REPORT_PATH}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
