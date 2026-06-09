from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from pymongo import MongoClient

try:
    import redis
except Exception:
    redis = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "ga03_docker_healthcheck_report.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def app_base_url() -> str:
    return os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip("/")


def pocketbase_url() -> str:
    return os.getenv("POCKETBASE_URL", "http://localhost:8090").rstrip("/")


def mongo_uri() -> str:
    return os.getenv("MONGO_URI", "mongodb://localhost:27017")


def mongo_database() -> str:
    return os.getenv("MONGO_DATABASE", "hoteldata_hub")


def redis_host() -> str:
    return os.getenv("REDIS_HOST", "localhost")


def redis_port() -> int:
    return int(os.getenv("REDIS_PORT", "6379"))


def redis_db() -> int:
    return int(os.getenv("REDIS_DB", "0"))


def make_check(name: str, ok: bool, details: dict[str, Any] | None = None, error: str | None = None) -> dict[str, Any]:
    return {"name": name, "ok": ok, "details": details or {}, "error": error}


def request_check(name: str, url: str, expected_statuses: set[int]) -> tuple[bool, dict[str, Any], str | None]:
    try:
        response = requests.get(url, timeout=10, allow_redirects=False)
        ok = response.status_code in expected_statuses
        details = {
            "url": url,
            "status_code": response.status_code,
            "location": response.headers.get("location"),
        }
        return ok, details, None if ok else f"Unexpected status {response.status_code}"
    except Exception as exc:
        return False, {"url": url}, str(exc)


def check_mongo() -> tuple[bool, dict[str, Any], str | None]:
    client = None
    try:
        client = MongoClient(mongo_uri(), serverSelectionTimeoutMS=3000)
        ping = client.admin.command("ping")
        db = client[mongo_database()]
        return True, {"mongo_uri": mongo_uri(), "database": mongo_database(), "ping": ping.get("ok"), "collections": db.list_collection_names()[:10]}, None
    except Exception as exc:
        return False, {"mongo_uri": mongo_uri(), "database": mongo_database()}, str(exc)
    finally:
        if client is not None:
            client.close()


def check_redis() -> tuple[bool, dict[str, Any], str | None]:
    details = {
        "host": redis_host(),
        "port": redis_port(),
        "db": redis_db(),
    }
    if redis is None:
        return False, details, "Python package 'redis' is not installed."
    try:
        client = redis.Redis(host=redis_host(), port=redis_port(), db=redis_db(), socket_connect_timeout=2, socket_timeout=2, decode_responses=True)
        pong = client.ping()
        details["ping"] = pong
        return bool(pong), details, None if pong else "Redis ping returned false."
    except Exception as exc:
        return False, details, str(exc)


def run_healthcheck() -> dict[str, Any]:
    report: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "checks": [],
        "summary": {},
    }
    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    app_login_ok, app_login_details, app_login_error = request_check("app_login", f"{app_base_url()}/auth/login", {200})
    checks.append(make_check("app_login", app_login_ok, app_login_details, app_login_error))
    if not app_login_ok and app_login_error:
        errors.append(f"app_login: {app_login_error}")

    redis_status_ok, redis_status_details, redis_status_error = request_check(
        "redis_status_route",
        f"{app_base_url()}/system/redis-status",
        {200, 303},
    )
    checks.append(make_check("redis_status_route", redis_status_ok, redis_status_details, redis_status_error))
    if not redis_status_ok and redis_status_error:
        errors.append(f"redis_status_route: {redis_status_error}")

    hotels_ok, hotels_details, hotels_error = request_check(
        "hotels_search_route",
        f"{app_base_url()}/hotels/search",
        {200, 303},
    )
    checks.append(make_check("hotels_search_route", hotels_ok, hotels_details, hotels_error))
    if not hotels_ok and hotels_error:
        errors.append(f"hotels_search_route: {hotels_error}")

    pocketbase_ok, pocketbase_details, pocketbase_error = request_check(
        "pocketbase_health",
        f"{pocketbase_url()}/api/health",
        {200},
    )
    checks.append(make_check("pocketbase_health", pocketbase_ok, pocketbase_details, pocketbase_error))
    if not pocketbase_ok and pocketbase_error:
        errors.append(f"pocketbase_health: {pocketbase_error}")

    mongo_ok, mongo_details, mongo_error = check_mongo()
    checks.append(make_check("mongo_ping", mongo_ok, mongo_details, mongo_error))
    if not mongo_ok and mongo_error:
        errors.append(f"mongo_ping: {mongo_error}")

    redis_ok, redis_details, redis_error = check_redis()
    checks.append(make_check("redis_ping", redis_ok, redis_details, redis_error))
    if not redis_ok and redis_error:
        errors.append(f"redis_ping: {redis_error}")

    report["checks"] = checks
    report["summary"] = {
        "app_login_ok": app_login_ok,
        "mongo_ok": mongo_ok,
        "redis_ok": redis_ok,
        "pocketbase_ok": pocketbase_ok,
        "redis_status_route_ok": redis_status_ok,
        "hotels_search_route_ok": hotels_ok,
        "result": all(check["ok"] for check in checks),
        "errors": errors,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    report = run_healthcheck()
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    print(f"report_path={REPORT_PATH}")


if __name__ == "__main__":
    main()
