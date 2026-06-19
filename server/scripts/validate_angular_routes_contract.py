from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def has_all_patterns(text: str, patterns: Iterable[str]) -> bool:
    return all(re.search(pattern, text) for pattern in patterns)


def extract_endpoints(text: str, base_url: str) -> list[str]:
    pattern = re.compile(r"`\$\{this\.apiConfig\.baseUrl\}([^`]+)`")
    endpoints = []
    for match in pattern.finditer(text):
        endpoint = match.group(1)
        if endpoint.startswith("/"):
            endpoints.append(f"{base_url}{endpoint}")
    return sorted(set(endpoints))


def main() -> int:
    frontend_root = ROOT / "frontend"
    proxy_path = frontend_root / "proxy.conf.json"
    package_json_path = frontend_root / "package.json"
    auth_guard_path = frontend_root / "src" / "app" / "core" / "auth" / "auth.guard.ts"
    auth_interceptor_path = frontend_root / "src" / "app" / "core" / "auth" / "auth.interceptor.ts"
    app_routes_path = frontend_root / "src" / "app" / "app.routes.ts"
    account_routes_path = frontend_root / "src" / "app" / "features" / "account" / "account.routes.ts"
    management_routes_path = frontend_root / "src" / "app" / "features" / "management" / "management.routes.ts"
    reservations_routes_path = frontend_root / "src" / "app" / "features" / "reservations" / "reservations.routes.ts"
    hotel_detail_routes_path = frontend_root / "src" / "app" / "features" / "hotel-detail" / "hotel-detail.routes.ts"
    properties_routes_path = frontend_root / "src" / "app" / "features" / "properties" / "properties.routes.ts"
    system_routes_path = frontend_root / "src" / "app" / "features" / "system-admin" / "system-admin.routes.ts"

    checks: list[dict[str, object]] = []

    def check_exists(label: str, path: Path) -> str | None:
        ok = path.exists()
        checks.append({"check": label, "ok": ok, "path": normalize_path(path)})
        return read_text(path) if ok else None

    proxy_text = check_exists("proxy.conf.json exists", proxy_path)
    package_json_text = check_exists("package.json exists", package_json_path)
    auth_guard_text = check_exists("auth.guard.ts exists", auth_guard_path)
    auth_interceptor_text = check_exists("auth.interceptor.ts exists", auth_interceptor_path)
    app_routes_text = check_exists("app.routes.ts exists", app_routes_path)
    account_routes_text = check_exists("account.routes.ts exists", account_routes_path)
    management_routes_text = check_exists("management.routes.ts exists", management_routes_path)
    reservations_routes_text = check_exists("reservations.routes.ts exists", reservations_routes_path)
    hotel_detail_routes_text = check_exists("hotel-detail.routes.ts exists", hotel_detail_routes_path)
    properties_routes_text = check_exists("properties.routes.ts exists", properties_routes_path)
    system_routes_text = check_exists("system-admin.routes.ts exists", system_routes_path)

    if package_json_text:
        try:
            package_data = json.loads(package_json_text)
            start_script = (package_data.get("scripts") or {}).get("start", "")
            checks.append(
                {
                    "check": "npm start uses proxy.conf.json",
                    "ok": "proxy.conf.json" in start_script and "--proxy-config" in start_script,
                    "detail": start_script,
                }
            )
        except json.JSONDecodeError as exc:
            checks.append({"check": "package.json parse", "ok": False, "detail": str(exc)})

    if auth_interceptor_text:
        checks.append(
            {
                "check": "auth.interceptor applies withCredentials",
                "ok": "withCredentials: true" in auth_interceptor_text,
            }
        )

    if auth_guard_text:
        checks.append(
            {
                "check": "auth.guard uses AuthService/session probe",
                "ok": "AuthService" in auth_guard_text or "/api/auth/me" in auth_guard_text,
            }
        )

    route_checks = [
        {
            "route": "/login",
            "conditions": [
                (app_routes_text, r"path:\s*'login'")
            ],
        },
        {
            "route": "/search",
            "conditions": [
                (app_routes_text, r"path:\s*'search'")
            ],
        },
        {
            "route": "/hotels/:hotelId",
            "conditions": [
                (app_routes_text, r"path:\s*'hotels'"),
                (hotel_detail_routes_text, r"path:\s*':hotelId'")
            ],
        },
        {
            "route": "/account/bookings/new",
            "conditions": [
                (app_routes_text, r"path:\s*'account'"),
                (account_routes_text, r"path:\s*'bookings'"),
                (reservations_routes_text, r"path:\s*'new'")
            ],
        },
        {
            "route": "/account/bookings/:bookingId",
            "conditions": [
                (app_routes_text, r"path:\s*'account'"),
                (account_routes_text, r"path:\s*'bookings'"),
                (reservations_routes_text, r"path:\s*':bookingId'")
            ],
        },
        {
            "route": "/management",
            "conditions": [
                (app_routes_text, r"path:\s*'management'")
            ],
        },
        {
            "route": "/management/reservations",
            "conditions": [
                (app_routes_text, r"path:\s*'management'"),
                (management_routes_text, r"path:\s*'reservations'")
            ],
        },
        {
            "route": "/management/check-ins",
            "conditions": [
                (app_routes_text, r"path:\s*'management'"),
                (management_routes_text, r"path:\s*'check-ins'")
            ],
        },
        {
            "route": "/management/check-outs",
            "conditions": [
                (app_routes_text, r"path:\s*'management'"),
                (management_routes_text, r"path:\s*'check-outs'")
            ],
        },
        {
            "route": "/management/properties",
            "conditions": [
                (app_routes_text, r"path:\s*'management'"),
                (management_routes_text, r"path:\s*'properties'")
            ],
        },
        {
            "route": "/management/properties/:propertyId",
            "conditions": [
                (app_routes_text, r"path:\s*'management'"),
                (management_routes_text, r"path:\s*'properties'"),
                (properties_routes_text, r"path:\s*':propertyId'")
            ],
        },
        {
            "route": "/management/availability",
            "conditions": [
                (app_routes_text, r"path:\s*'management'"),
                (management_routes_text, r"path:\s*'availability'")
            ],
        },
        {
            "route": "/management/rooms",
            "conditions": [
                (app_routes_text, r"path:\s*'management'"),
                (management_routes_text, r"path:\s*'rooms'")
            ],
        },
        {
            "route": "/management/rates",
            "conditions": [
                (app_routes_text, r"path:\s*'management'"),
                (management_routes_text, r"path:\s*'rates'")
            ],
        },
        {
            "route": "/management/policies",
            "conditions": [
                (app_routes_text, r"path:\s*'management'"),
                (management_routes_text, r"path:\s*'policies'")
            ],
        },
        {
            "route": "/management/amenities",
            "conditions": [
                (app_routes_text, r"path:\s*'management'"),
                (management_routes_text, r"path:\s*'amenities'")
            ],
        },
        {
            "route": "/system",
            "conditions": [
                (app_routes_text, r"path:\s*'system'")
            ],
        },
    ]

    routes_report: list[dict[str, object]] = []
    for entry in route_checks:
        conditions = entry["conditions"]
        ok = True
        for text, pattern in conditions:
            if not text or not re.search(pattern, text):
                ok = False
                break
        routes_report.append({"route": entry["route"], "ok": ok})

    endpoints_by_service: dict[str, list[str]] = {}
    service_paths = {
        "auth.service.ts": auth_guard_path.parent / "auth.service.ts",
        "hotel-search-api.service.ts": frontend_root / "src" / "app" / "features" / "hotel-search" / "services" / "hotel-search-api.service.ts",
        "hotel-detail-api.service.ts": frontend_root / "src" / "app" / "features" / "hotel-detail" / "services" / "hotel-detail-api.service.ts",
        "reservations-api.service.ts": frontend_root / "src" / "app" / "features" / "reservations" / "services" / "reservations-api.service.ts",
        "dashboard-api.service.ts": frontend_root / "src" / "app" / "features" / "admin" / "services" / "dashboard-api.service.ts",
        "properties-api.service.ts": frontend_root / "src" / "app" / "features" / "properties" / "services" / "properties-api.service.ts",
        "availability-api.service.ts": frontend_root / "src" / "app" / "features" / "availability" / "services" / "availability-api.service.ts",
        "rooms-api.service.ts": frontend_root / "src" / "app" / "features" / "rooms" / "services" / "rooms-api.service.ts",
        "rates-api.service.ts": frontend_root / "src" / "app" / "features" / "rates" / "services" / "rates-api.service.ts",
        "policies-api.service.ts": frontend_root / "src" / "app" / "features" / "policies" / "services" / "policies-api.service.ts",
        "amenities-api.service.ts": frontend_root / "src" / "app" / "features" / "amenities" / "services" / "amenities-api.service.ts",
        "management-reports-api.service.ts": frontend_root / "src" / "app" / "features" / "management" / "services" / "management-reports-api.service.ts",
        "check-ins-api.service.ts": frontend_root / "src" / "app" / "features" / "check-ins" / "services" / "check-ins-api.service.ts",
        "check-outs-api.service.ts": frontend_root / "src" / "app" / "features" / "check-outs" / "services" / "check-outs-api.service.ts",
    }

    base_url = "/api"
    for label, path in service_paths.items():
        if not path.exists():
            continue
        text = read_text(path)
        endpoints = extract_endpoints(text, base_url)
        if endpoints:
            endpoints_by_service[normalize_path(path)] = endpoints

    summary = {
        "root": str(ROOT),
        "checks": checks,
        "routes": routes_report,
        "endpoints_by_service": endpoints_by_service,
        "ok_count": sum(1 for item in routes_report if item["ok"]),
        "error_count": sum(1 for item in routes_report if not item["ok"]),
    }

    json.dump(summary, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
