from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "ga03_full_integrations_report.json"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_database
from src.app.security.navigation import get_default_redirect_for_role


SECURITY_COLLECTIONS = [
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "user_sessions",
    "user_activity_logs",
]
RESERVATION_COLLECTIONS = [
    "booking_orders",
    "booking_guests",
    "booking_status_history",
    "manual_reservations",
]
PARTNER_COLLECTIONS = [
    "hotel_images",
    "hotel_policies",
    "hotel_content_pages",
    "hotel_content_changes",
    "room_types",
    "hotel_rooms",
    "room_inventory_calendar",
    "room_availability_blocks",
    "blackout_dates",
]
REVENUE_COLLECTIONS = [
    "rate_plans",
    "hotel_rate_calendar",
    "rate_rules",
    "promotion_campaigns",
    "coupon_codes",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_check(name: str, ok: bool, details: dict[str, Any] | None = None, error: str | None = None) -> dict[str, Any]:
    return {"name": name, "ok": ok, "details": details or {}, "error": error}


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def import_app() -> tuple[Any | None, str | None]:
    try:
        from src.app.main import app

        return app, None
    except Exception as exc:
        return None, str(exc)


def start_server(port: int) -> subprocess.Popen[str]:
    stdout_path = PROJECT_ROOT / "data" / "reports" / "ga03_full_integrations.stdout.log"
    stderr_path = PROJECT_ROOT / "data" / "reports" / "ga03_full_integrations.stderr.log"
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


def wait_for_server(base_url: str, timeout_seconds: int = 25) -> bool:
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


def cleanup_booking(db, booking_id: str | None) -> None:
    if not booking_id:
        return
    db.manual_reservations.delete_many({"booking_id": booking_id})
    db.booking_status_history.delete_many({"booking_id": booking_id})
    db.booking_guests.delete_many({"booking_id": booking_id})
    db.booking_orders.delete_many({"booking_id": booking_id})


def cleanup_partner_test_data(db, prop_id: int) -> None:
    db.hotel_images.delete_many({"prop_id": prop_id, "image_url": "https://example.com/ga03-full-partner-image.jpg"})
    db.room_inventory_calendar.delete_many({"prop_id": prop_id, "room_type_id": f"RT-{prop_id}-ga03-full-room"})
    db.room_availability_blocks.delete_many({"prop_id": prop_id, "room_type_id": f"RT-{prop_id}-ga03-full-room"})
    db.blackout_dates.delete_many({"prop_id": prop_id, "room_type_id": f"RT-{prop_id}-ga03-full-room"})
    db.hotel_rooms.delete_many({"prop_id": prop_id, "room_type_id": f"RT-{prop_id}-ga03-full-room"})
    db.room_types.delete_many({"prop_id": prop_id, "room_type_id": f"RT-{prop_id}-ga03-full-room"})


def cleanup_revenue_test_data(db, prop_id: int) -> None:
    db.hotel_rate_calendar.delete_many({"prop_id": prop_id, "rate_plan_id": f"RP-{prop_id}-ga03-full-rate"})
    db.rate_rules.delete_many({"prop_id": prop_id, "rate_plan_id": f"RP-{prop_id}-ga03-full-rate"})
    db.rate_plans.delete_many({"prop_id": prop_id, "rate_plan_id": f"RP-{prop_id}-ga03-full-rate"})
    db.coupon_codes.delete_many({"prop_id": prop_id, "campaign_id": f"PC-{prop_id}-ga03-full-promo"})
    db.promotion_campaigns.delete_many({"prop_id": prop_id, "campaign_id": f"PC-{prop_id}-ga03-full-promo"})


def restore_singleton_documents(db, backups: dict[str, Any], prop_id: int) -> None:
    if backups["hotel_content_pages"] is None:
        db.hotel_content_pages.delete_many({"prop_id": prop_id})
    else:
        db.hotel_content_pages.replace_one({"_id": backups["hotel_content_pages"]["_id"]}, backups["hotel_content_pages"], upsert=True)
    if backups["hotel_policies"] is None:
        db.hotel_policies.delete_many({"prop_id": prop_id})
    else:
        db.hotel_policies.replace_one({"_id": backups["hotel_policies"]["_id"]}, backups["hotel_policies"], upsert=True)
    db.hotel_content_changes.delete_many({"prop_id": prop_id, "changed_by": "ga03_full_validation"})


def pick_prop_ids(db) -> tuple[int, int]:
    items = list(db.dim_hotels.find({}, {"_id": 0, "prop_id": 1}).sort([("prop_id", 1)]).limit(2))
    if not items:
        return 1, 1
    first = int(items[0]["prop_id"])
    second = int(items[1]["prop_id"]) if len(items) > 1 else first
    return first, second


def validate_collections(db) -> tuple[bool, dict[str, list[str]], list[str]]:
    existing = set(db.list_collection_names())
    required = SECURITY_COLLECTIONS + RESERVATION_COLLECTIONS + PARTNER_COLLECTIONS + REVENUE_COLLECTIONS
    missing = [name for name in required if name not in existing]
    return (
        not missing,
        {
            "checked": required,
            "present": [name for name in required if name in existing],
            "missing": missing,
        },
        [f"Missing collection: {name}" for name in missing],
    )


def login_admin(session: requests.Session, base_url: str) -> tuple[bool, dict[str, Any], str | None]:
    response = session.post(
        f"{base_url}/auth/login",
        data={"identifier": "superadmin", "password": "Admin12345*"},
        timeout=30,
        allow_redirects=False,
    )
    expected_location = get_default_redirect_for_role("super_admin")
    ok = response.status_code == 303 and response.headers.get("location") == expected_location
    details = {
        "status_code": response.status_code,
        "location": response.headers.get("location"),
        "expected_location": expected_location,
    }
    return ok, details, None if ok else "Admin login failed"


def extract_booking_id(location: str | None) -> str | None:
    if not location:
        return None
    parts = location.rstrip("/").split("/")
    return parts[-1] if parts else None


def run_validation() -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env")
    report: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "checks": [],
        "summary": {},
    }
    errors: list[str] = []
    total_routes_checked = 0
    routes_ok = 0
    routes_failed = 0

    app, import_error = import_app()
    report["checks"].append(make_check("app_import", app is not None, {}, import_error))
    if app is None:
        errors.append(f"app_import: {import_error}")
        report["summary"] = {
            "total_routes_checked": 0,
            "routes_ok": 0,
            "routes_failed": 0,
            "mongo_collections_checked": 0,
            "security_ok": False,
            "reservations_ok": False,
            "partner_ok": False,
            "revenue_ok": False,
            "analytics_ok": False,
            "redis_ok": False,
            "legacy_routes_ok": False,
            "errors": errors,
        }
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return report

    db = get_database()
    db.command("ping")
    prop_id, compare_prop_id = pick_prop_ids(db)
    collections_ok, collections_details, collection_errors = validate_collections(db)
    report["checks"].append(make_check("mongo_collections", collections_ok, collections_details, None if collections_ok else "Missing collections"))
    errors.extend(collection_errors)

    backups = {
        "hotel_content_pages": db.hotel_content_pages.find_one({"prop_id": prop_id}),
        "hotel_policies": db.hotel_policies.find_one({"prop_id": prop_id}),
    }

    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = start_server(port)
    booking_id: str | None = None
    manual_booking_id: str | None = None
    security_ok = reservations_ok = partner_ok = revenue_ok = analytics_ok = redis_ok = legacy_routes_ok = False
    try:
        if not wait_for_server(base_url):
            errors.append("web_server_boot: timed out waiting for app server")
            report["checks"].append(make_check("web_server_boot", False, {"base_url": base_url}, "Timed out waiting for app server"))
        else:
            report["checks"].append(make_check("web_server_boot", True, {"base_url": base_url}))
            anon = requests.Session()
            admin = requests.Session()

            # Security
            security_results: list[bool] = []
            for route, expected in {
                "/": {303},
                "/auth/login": {200},
                "/auth/me": {303},
                "/admin/security": {303},
                "/admin/users": {303},
                "/ta02": {303},
            }.items():
                response = anon.get(f"{base_url}{route}", timeout=30, allow_redirects=False)
                total_routes_checked += 1
                ok = response.status_code in expected
                report["checks"].append(make_check(route, ok, {"status_code": response.status_code, "location": response.headers.get("location")}, None if ok else "Unexpected status"))
                security_results.append(ok)
                if ok:
                    routes_ok += 1
                else:
                    routes_failed += 1
                    errors.append(f"{route}: unexpected status {response.status_code}")

            login_ok, login_details, login_error = login_admin(admin, base_url)
            total_routes_checked += 1
            report["checks"].append(make_check("/auth/login[POST]", login_ok, login_details, login_error))
            if login_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append(f"/auth/login[POST]: {login_error}")

            for route, expected in {
                "/auth/me": {200},
                "/admin/security": {200},
                "/admin/users": {200},
            }.items():
                response = admin.get(f"{base_url}{route}", timeout=30, allow_redirects=False)
                total_routes_checked += 1
                ok = response.status_code in expected
                report["checks"].append(make_check(f"{route}[auth]", ok, {"status_code": response.status_code}, None if ok else "Unexpected status"))
                security_results.append(ok)
                if ok:
                    routes_ok += 1
                else:
                    routes_failed += 1
                    errors.append(f"{route}[auth]: unexpected status {response.status_code}")

            logout_response = admin.get(f"{base_url}/auth/logout", timeout=30, allow_redirects=False)
            total_routes_checked += 1
            logout_ok = logout_response.status_code == 303
            report["checks"].append(make_check("/auth/logout", logout_ok, {"status_code": logout_response.status_code, "location": logout_response.headers.get("location")}, None if logout_ok else "Unexpected status"))
            security_results.append(logout_ok)
            if logout_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append(f"/auth/logout: unexpected status {logout_response.status_code}")
            security_ok = all(security_results)

            relogin_ok, relogin_details, relogin_error = login_admin(admin, base_url)
            report["checks"].append(make_check("/auth/login[POST][relogin]", relogin_ok, relogin_details, relogin_error))
            if not relogin_ok:
                errors.append(f"/auth/login[POST][relogin]: {relogin_error}")

            # Redis
            redis_response = admin.get(f"{base_url}/system/redis-status", timeout=30)
            total_routes_checked += 1
            redis_json = redis_response.json()
            redis_ok = redis_response.status_code == 200 and "connected" in redis_json and "enabled" in redis_json
            report["checks"].append(make_check("/system/redis-status", redis_ok, {"status_code": redis_response.status_code, "json": redis_json}, None if redis_ok else "Invalid redis status"))
            if redis_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append("/system/redis-status: invalid response")

            # Client / traveler
            client_routes = [
                f"/hotels/search",
                f"/hotels/{prop_id}",
                f"/hotels/compare?prop_id={prop_id}&prop_id={compare_prop_id}",
            ]
            client_results: list[bool] = []
            for route in client_routes:
                response = admin.get(f"{base_url}{route}", timeout=30, allow_redirects=False)
                total_routes_checked += 1
                ok = response.status_code == 200
                report["checks"].append(make_check(route, ok, {"status_code": response.status_code}, None if ok else "Unexpected status"))
                client_results.append(ok)
                if ok:
                    routes_ok += 1
                else:
                    routes_failed += 1
                    errors.append(f"{route}: unexpected status {response.status_code}")

            # Reservations
            reservation_results: list[bool] = []
            for route in ["/reservations", f"/reservations/new?prop_id={prop_id}", f"/partner/manual-reservations/new?prop_id={prop_id}"]:
                response = admin.get(f"{base_url}{route}", timeout=30, allow_redirects=False)
                total_routes_checked += 1
                ok = response.status_code == 200
                report["checks"].append(make_check(route, ok, {"status_code": response.status_code}, None if ok else "Unexpected status"))
                reservation_results.append(ok)
                if ok:
                    routes_ok += 1
                else:
                    routes_failed += 1
                    errors.append(f"{route}: unexpected status {response.status_code}")

            reservation_post = admin.post(
                f"{base_url}/reservations/new",
                data={
                    "prop_id": prop_id,
                    "guest_name": "GA03 Full Validation",
                    "guest_email": "ga03-full-validation@hoteldata.local",
                    "check_in_date": "2026-08-01",
                    "check_out_date": "2026-08-03",
                    "adults": 2,
                    "children": 0,
                    "rooms": 1,
                    "comment": "ga03_full_validation",
                },
                timeout=30,
                allow_redirects=False,
            )
            booking_id = extract_booking_id(reservation_post.headers.get("location"))
            post_ok = reservation_post.status_code == 303 and bool(booking_id)
            total_routes_checked += 1
            report["checks"].append(make_check("/reservations/new[POST]", post_ok, {"status_code": reservation_post.status_code, "location": reservation_post.headers.get("location"), "booking_id": booking_id}, None if post_ok else "Reservation creation failed"))
            reservation_results.append(post_ok)
            if post_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append("/reservations/new[POST]: creation failed")

            if booking_id:
                detail_response = admin.get(f"{base_url}/reservations/{booking_id}", timeout=30, allow_redirects=False)
                total_routes_checked += 1
                detail_ok = detail_response.status_code == 200
                report["checks"].append(make_check(f"/reservations/{booking_id}", detail_ok, {"status_code": detail_response.status_code}, None if detail_ok else "Unexpected status"))
                reservation_results.append(detail_ok)
                if detail_ok:
                    routes_ok += 1
                else:
                    routes_failed += 1
                    errors.append(f"/reservations/{booking_id}: unexpected status {detail_response.status_code}")

                cancel_response = admin.post(f"{base_url}/reservations/{booking_id}/cancel", timeout=30, allow_redirects=False)
                total_routes_checked += 1
                cancel_ok = cancel_response.status_code == 303
                report["checks"].append(make_check(f"/reservations/{booking_id}/cancel", cancel_ok, {"status_code": cancel_response.status_code}, None if cancel_ok else "Unexpected status"))
                reservation_results.append(cancel_ok)
                if cancel_ok:
                    routes_ok += 1
                else:
                    routes_failed += 1
                    errors.append(f"/reservations/{booking_id}/cancel: unexpected status {cancel_response.status_code}")

            manual_post = admin.post(
                f"{base_url}/partner/manual-reservations/new",
                data={
                    "prop_id": prop_id,
                    "guest_name": "GA03 Manual Validation",
                    "guest_email": "ga03-manual-validation@hoteldata.local",
                    "check_in_date": "2026-08-10",
                    "check_out_date": "2026-08-11",
                    "adults": 1,
                    "children": 0,
                    "rooms": 1,
                    "comment": "ga03_full_validation_manual",
                    "created_by": "ga03_full_validation",
                },
                timeout=30,
                allow_redirects=False,
            )
            manual_booking_id = extract_booking_id(manual_post.headers.get("location"))
            manual_ok = manual_post.status_code == 303 and bool(manual_booking_id)
            total_routes_checked += 1
            report["checks"].append(make_check("/partner/manual-reservations/new[POST]", manual_ok, {"status_code": manual_post.status_code, "location": manual_post.headers.get("location"), "booking_id": manual_booking_id}, None if manual_ok else "Manual reservation failed"))
            reservation_results.append(manual_ok)
            if manual_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append("/partner/manual-reservations/new[POST]: creation failed")
            reservations_ok = all(reservation_results)

            # Partner
            partner_results: list[bool] = []
            for route in [
                "/partner/hotels",
                f"/partner/hotels/{prop_id}",
                f"/partner/hotels/{prop_id}/performance",
                f"/partner/hotels/{prop_id}/content",
                f"/partner/hotels/{prop_id}/content/edit",
                f"/partner/hotels/{prop_id}/policies",
                f"/partner/hotels/{prop_id}/images",
                f"/partner/hotels/{prop_id}/rooms",
                f"/partner/hotels/{prop_id}/inventory",
            ]:
                response = admin.get(f"{base_url}{route}", timeout=30, allow_redirects=False)
                total_routes_checked += 1
                ok = response.status_code == 200
                report["checks"].append(make_check(route, ok, {"status_code": response.status_code}, None if ok else "Unexpected status"))
                partner_results.append(ok)
                if ok:
                    routes_ok += 1
                else:
                    routes_failed += 1
                    errors.append(f"{route}: unexpected status {response.status_code}")

            content_post = admin.post(
                f"{base_url}/partner/hotels/{prop_id}/content/edit",
                data={
                    "description": "GA03 full validation content",
                    "highlights": "validation highlight",
                    "amenities_text": "validation amenities",
                },
                timeout=30,
                allow_redirects=False,
            )
            total_routes_checked += 1
            content_ok = content_post.status_code == 303
            report["checks"].append(make_check(f"/partner/hotels/{prop_id}/content/edit[POST]", content_ok, {"status_code": content_post.status_code}, None if content_ok else "Unexpected status"))
            partner_results.append(content_ok)
            if content_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append(f"/partner/hotels/{prop_id}/content/edit[POST]: unexpected status {content_post.status_code}")

            policies_post = admin.post(
                f"{base_url}/partner/hotels/{prop_id}/policies",
                data={
                    "check_in_time": "15:00",
                    "check_out_time": "11:00",
                    "cancellation_policy": "GA03 full validation cancellation",
                    "pet_policy": "GA03 full validation pets",
                    "children_policy": "GA03 full validation children",
                },
                timeout=30,
                allow_redirects=False,
            )
            total_routes_checked += 1
            policies_ok = policies_post.status_code == 303
            report["checks"].append(make_check(f"/partner/hotels/{prop_id}/policies[POST]", policies_ok, {"status_code": policies_post.status_code}, None if policies_ok else "Unexpected status"))
            partner_results.append(policies_ok)
            if policies_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append(f"/partner/hotels/{prop_id}/policies[POST]: unexpected status {policies_post.status_code}")

            image_post = admin.post(
                f"{base_url}/partner/hotels/{prop_id}/images",
                data={"image_url": "https://example.com/ga03-full-partner-image.jpg", "title": "GA03 full validation"},
                timeout=30,
                allow_redirects=False,
            )
            total_routes_checked += 1
            image_ok = image_post.status_code == 303
            report["checks"].append(make_check(f"/partner/hotels/{prop_id}/images[POST]", image_ok, {"status_code": image_post.status_code}, None if image_ok else "Unexpected status"))
            partner_results.append(image_ok)
            if image_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append(f"/partner/hotels/{prop_id}/images[POST]: unexpected status {image_post.status_code}")

            room_post = admin.post(
                f"{base_url}/partner/hotels/{prop_id}/rooms/new",
                data={
                    "name": "GA03 Full Room",
                    "description": "GA03 full validation room",
                    "max_adults": 2,
                    "max_children": 1,
                    "base_capacity": 2,
                    "is_active": "on",
                },
                timeout=30,
                allow_redirects=False,
            )
            total_routes_checked += 1
            room_ok = room_post.status_code == 303
            report["checks"].append(make_check(f"/partner/hotels/{prop_id}/rooms/new[POST]", room_ok, {"status_code": room_post.status_code}, None if room_ok else "Unexpected status"))
            partner_results.append(room_ok)
            if room_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append(f"/partner/hotels/{prop_id}/rooms/new[POST]: unexpected status {room_post.status_code}")

            inventory_post = admin.post(
                f"{base_url}/partner/hotels/{prop_id}/inventory",
                data={
                    "room_type_id": f"RT-{prop_id}-ga03-full-room",
                    "date": "2026-09-01",
                    "total_rooms": 8,
                    "available_rooms": 6,
                    "blocked_rooms": 2,
                },
                timeout=30,
                allow_redirects=False,
            )
            total_routes_checked += 1
            inventory_ok = inventory_post.status_code == 303
            report["checks"].append(make_check(f"/partner/hotels/{prop_id}/inventory[POST]", inventory_ok, {"status_code": inventory_post.status_code}, None if inventory_ok else "Unexpected status"))
            partner_results.append(inventory_ok)
            if inventory_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append(f"/partner/hotels/{prop_id}/inventory[POST]: unexpected status {inventory_post.status_code}")

            blackout_post = admin.post(
                f"{base_url}/partner/hotels/{prop_id}/blackout-dates",
                data={
                    "room_type_id": f"RT-{prop_id}-ga03-full-room",
                    "start_date": "2026-09-02",
                    "end_date": "2026-09-03",
                    "reason": "ga03 full validation blackout",
                    "blocked_rooms": 3,
                },
                timeout=30,
                allow_redirects=False,
            )
            total_routes_checked += 1
            blackout_ok = blackout_post.status_code == 303
            report["checks"].append(make_check(f"/partner/hotels/{prop_id}/blackout-dates[POST]", blackout_ok, {"status_code": blackout_post.status_code}, None if blackout_ok else "Unexpected status"))
            partner_results.append(blackout_ok)
            if blackout_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append(f"/partner/hotels/{prop_id}/blackout-dates[POST]: unexpected status {blackout_post.status_code}")
            partner_ok = all(partner_results)

            # Revenue
            revenue_results: list[bool] = []
            for route in [
                "/revenue/rate-plans",
                f"/revenue/hotel/{prop_id}/rates",
                "/revenue/promotions",
                "/revenue/rate-plans/new",
                "/revenue/promotions/new",
            ]:
                response = admin.get(f"{base_url}{route}", timeout=30, allow_redirects=False)
                total_routes_checked += 1
                ok = response.status_code == 200
                report["checks"].append(make_check(route, ok, {"status_code": response.status_code}, None if ok else "Unexpected status"))
                revenue_results.append(ok)
                if ok:
                    routes_ok += 1
                else:
                    routes_failed += 1
                    errors.append(f"{route}: unexpected status {response.status_code}")

            rate_plan_post = admin.post(
                f"{base_url}/revenue/rate-plans/new",
                data={
                    "prop_id": prop_id,
                    "name": "GA03 Full Rate",
                    "description": "ga03 full validation rate plan",
                    "base_rate": 199.5,
                    "currency": "USD",
                    "is_active": "on",
                },
                timeout=30,
                allow_redirects=False,
            )
            total_routes_checked += 1
            rp_ok = rate_plan_post.status_code == 303
            report["checks"].append(make_check("/revenue/rate-plans/new[POST]", rp_ok, {"status_code": rate_plan_post.status_code}, None if rp_ok else "Unexpected status"))
            revenue_results.append(rp_ok)
            if rp_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append(f"/revenue/rate-plans/new[POST]: unexpected status {rate_plan_post.status_code}")

            hotel_rate_post = admin.post(
                f"{base_url}/revenue/hotel/{prop_id}/rates",
                data={
                    "rate_plan_id": f"RP-{prop_id}-ga03-full-rate",
                    "date": "2026-09-10",
                    "rate_amount": 225,
                    "min_stay_nights": 2,
                },
                timeout=30,
                allow_redirects=False,
            )
            total_routes_checked += 1
            hr_ok = hotel_rate_post.status_code == 303
            report["checks"].append(make_check(f"/revenue/hotel/{prop_id}/rates[POST]", hr_ok, {"status_code": hotel_rate_post.status_code}, None if hr_ok else "Unexpected status"))
            revenue_results.append(hr_ok)
            if hr_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append(f"/revenue/hotel/{prop_id}/rates[POST]: unexpected status {hotel_rate_post.status_code}")

            promo_post = admin.post(
                f"{base_url}/revenue/promotions/new",
                data={
                    "prop_id": prop_id,
                    "name": "GA03 Full Promo",
                    "description": "ga03 full validation promo",
                    "discount_percent": 10,
                    "start_date": "2026-09-10",
                    "end_date": "2026-09-15",
                    "coupon_code": "GA03FULL10",
                    "is_active": "on",
                },
                timeout=30,
                allow_redirects=False,
            )
            total_routes_checked += 1
            promo_ok = promo_post.status_code == 303
            report["checks"].append(make_check("/revenue/promotions/new[POST]", promo_ok, {"status_code": promo_post.status_code}, None if promo_ok else "Unexpected status"))
            revenue_results.append(promo_ok)
            if promo_ok:
                routes_ok += 1
            else:
                routes_failed += 1
                errors.append(f"/revenue/promotions/new[POST]: unexpected status {promo_post.status_code}")
            revenue_ok = all(revenue_results)

            # Analytics
            analytics_results: list[bool] = []
            for route in [
                "/analytics/reservations",
                "/analytics/conversion",
                "/analytics/revenue",
                "/analytics/promotions",
                "/analytics/visitor-markets",
            ]:
                response = admin.get(f"{base_url}{route}", timeout=30, allow_redirects=False)
                total_routes_checked += 1
                ok = response.status_code == 200
                report["checks"].append(make_check(route, ok, {"status_code": response.status_code}, None if ok else "Unexpected status"))
                analytics_results.append(ok)
                if ok:
                    routes_ok += 1
                else:
                    routes_failed += 1
                    errors.append(f"{route}: unexpected status {response.status_code}")
            analytics_ok = all(analytics_results)

            # Legacy routes
            legacy_results: list[bool] = []
            for route, expected in {
                "/ta02": {200},
                "/ta02/crud": {200, 307, 303},
                "/etl-status": {200},
            }.items():
                response = admin.get(f"{base_url}{route}", timeout=30, allow_redirects=False)
                total_routes_checked += 1
                ok = response.status_code in expected
                report["checks"].append(make_check(route, ok, {"status_code": response.status_code, "location": response.headers.get("location")}, None if ok else "Unexpected status"))
                legacy_results.append(ok)
                if ok:
                    routes_ok += 1
                else:
                    routes_failed += 1
                    errors.append(f"{route}: unexpected status {response.status_code}")
            legacy_routes_ok = all(legacy_results)

    finally:
        stop_server(server)
        cleanup_booking(db, booking_id)
        cleanup_booking(db, manual_booking_id)
        cleanup_partner_test_data(db, prop_id)
        cleanup_revenue_test_data(db, prop_id)
        restore_singleton_documents(db, backups, prop_id)

    report["summary"] = {
        "total_routes_checked": total_routes_checked,
        "routes_ok": routes_ok,
        "routes_failed": routes_failed,
        "mongo_collections_checked": len(collections_details["checked"]),
        "security_ok": security_ok,
        "reservations_ok": reservations_ok,
        "partner_ok": partner_ok,
        "revenue_ok": revenue_ok,
        "analytics_ok": analytics_ok,
        "redis_ok": redis_ok,
        "legacy_routes_ok": legacy_routes_ok,
        "errors": errors,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return report


def main() -> None:
    report = run_validation()
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    print(f"report_path={REPORT_PATH}")


if __name__ == "__main__":
    main()
