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
from pymongo import MongoClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "ga03_display_dimensions_report.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def mongo():
    client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=3000)
    return client, client["hoteldata_hub"]


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(port: int) -> subprocess.Popen[str]:
    stdout_path = PROJECT_ROOT / "data" / "reports" / "ga03_display_dimensions.stdout.log"
    stderr_path = PROJECT_ROOT / "data" / "reports" / "ga03_display_dimensions.stderr.log"
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


def login_cliente(base_url: str) -> requests.Session:
    session = requests.Session()
    session.post(
        f"{base_url}/auth/login",
        data={"identifier": "cliente", "password": "Cliente123*"},
        allow_redirects=False,
        timeout=30,
    )
    return session


def run_validation() -> dict[str, Any]:
    report: dict[str, Any] = {"generated_at": utc_now_iso(), "result": False, "checks": [], "errors": []}
    errors: list[str] = []

    client, db = mongo()
    try:
        sample_hotel = db.dim_hotels.find_one({}, {"_id": 0, "prop_id": 1, "display_name": 1})
        sample_destination = db.dim_destinations.find_one({}, {"_id": 0, "srch_destination_id": 1, "destination_display_name": 1})
        sample_country = db.dim_visitor_countries.find_one({}, {"_id": 0, "visitor_location_country_id": 1, "country_display_name": 1})
        sample_site = db.dim_sites.find_one({}, {"_id": 0, "site_id": 1, "site_display_name": 1})
        dimension_checks = {
            "dim_hotels_display": (
                db.dim_hotels.count_documents({"display_name": {"$exists": True, "$ne": ""}}),
                sample_hotel or {},
            ),
            "dim_destinations_display": (
                db.dim_destinations.count_documents({"destination_display_name": {"$exists": True, "$ne": ""}}),
                sample_destination or {},
            ),
            "dim_countries_display": (
                db.dim_visitor_countries.count_documents({"country_display_name": {"$exists": True, "$ne": ""}}),
                sample_country or {},
            ),
            "dim_sites_display": (
                db.dim_sites.count_documents({"site_display_name": {"$exists": True, "$ne": ""}}),
                sample_site or {},
            ),
        }
        for name, (count, sample) in dimension_checks.items():
            ok = count > 0
            report["checks"].append({"name": name, "ok": ok, "details": {"count": count, "sample": sample}})
            if not ok:
                errors.append(f"{name}: missing display field sample")

        port = find_free_port()
        base_url = f"http://127.0.0.1:{port}"
        process = start_server(port)
        try:
            if not wait_for_server(base_url):
                errors.append("server did not start")
                return report
            session = login_cliente(base_url)
            search_response = session.get(f"{base_url}/hotels/search", timeout=30)
            search_ok = search_response.status_code == 200 and "Hotel Partner " in search_response.text and "País " not in search_response.text
            report["checks"].append({"name": "hotels_search_enriched", "ok": search_ok, "details": {"status_code": search_response.status_code}})
            if not search_ok:
                errors.append("hotels_search_enriched: page did not show enriched labels as expected")

            prop_id = sample_hotel["prop_id"] if sample_hotel else 61529
            detail_response = session.get(f"{base_url}/hotels/{prop_id}", timeout=30)
            detail_ok = detail_response.status_code == 200 and f"ID propiedad: {prop_id}" in detail_response.text
            report["checks"].append({"name": "hotels_detail_enriched", "ok": detail_ok, "details": {"status_code": detail_response.status_code, "prop_id": prop_id}})
            if not detail_ok:
                errors.append("hotels_detail_enriched: detail did not show friendly name with technical id")
        finally:
            stop_server(process)
    finally:
        client.close()

    report["errors"] = errors
    report["result"] = not errors
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return report


def main() -> None:
    report = run_validation()
    print(json.dumps({"result": report["result"], "checks": len(report["checks"]), "errors": report["errors"]}, indent=2, ensure_ascii=False))
    print(f"report_path={REPORT_PATH}")


if __name__ == "__main__":
    main()
