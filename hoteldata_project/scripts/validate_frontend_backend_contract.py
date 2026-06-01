from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import date
from typing import Any


def fetch(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            content_type = response.headers.get("Content-Type", "")
            return {
                "url": url,
                "ok": True,
                "status": response.status,
                "content_type": content_type,
                "json": "application/json" in content_type.lower(),
                "body_preview": body[:240],
            }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
        return {
            "url": url,
            "ok": False,
            "status": exc.code,
            "content_type": content_type,
            "json": "application/json" in content_type.lower(),
            "body_preview": body[:240],
        }
    except Exception as exc:  # pragma: no cover - operational script
        return {
            "url": url,
            "ok": False,
            "status": None,
            "content_type": "",
            "json": False,
            "error": str(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate core frontend/backend JSON contracts.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="FastAPI base URL")
    parser.add_argument("--prop-id", default="1", help="Sample property id for management endpoints")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    prop_id = str(args.prop_id)
    today = date.today().isoformat()
    endpoints = [
      {"route": "/auth/login", "kind": "legacy_html", "required_json": False},
      {"route": "/api/auth/me", "kind": "json_auth_probe", "required_json": True},
      {"route": "/api/hotels/search", "kind": "json_public", "required_json": True},
      {"route": f"/api/hotels/{prop_id}", "kind": "json_public", "required_json": True},
      {"route": "/api/dashboard/overview", "kind": "json_private", "required_json": True},
      {"route": "/api/reservations", "kind": "json_private", "required_json": True},
      {"route": "/api/reservations/options", "kind": "json_private", "required_json": True},
      {"route": f"/api/management/properties/{prop_id}", "kind": "json_private", "required_json": True},
      {"route": "/api/management/properties", "kind": "json_private", "required_json": True},
      {"route": f"/api/management/rooms?prop_id={prop_id}", "kind": "json_private", "required_json": True},
      {"route": f"/api/management/availability?prop_id={prop_id}", "kind": "json_private", "required_json": True},
      {"route": f"/api/management/rates?prop_id={prop_id}", "kind": "json_private", "required_json": True},
      {"route": f"/api/management/policies?prop_id={prop_id}", "kind": "json_private", "required_json": True},
      {"route": f"/api/management/amenities?prop_id={prop_id}", "kind": "json_private", "required_json": True},
      {"route": f"/api/management/check-ins?date={today}&prop_id={prop_id}", "kind": "json_private", "required_json": True},
      {"route": f"/api/management/check-outs?date={today}&prop_id={prop_id}", "kind": "json_private", "required_json": True},
    ]

    results: list[dict[str, Any]] = []
    for endpoint in endpoints:
        result = fetch(f"{base_url}{endpoint['route']}")
        result["route"] = endpoint["route"]
        result["kind"] = endpoint["kind"]
        result["required_json"] = endpoint["required_json"]
        result["contract_ok"] = bool(
            result.get("status") in {200, 201, 400, 401, 403, 404, 405}
            and (not endpoint["required_json"] or result.get("json"))
        )
        results.append(result)

    summary = {
        "base_url": base_url,
        "prop_id": prop_id,
        "operation_date": today,
        "results": results,
        "ok_count": sum(1 for item in results if item["contract_ok"]),
        "error_count": sum(1 for item in results if not item["contract_ok"]),
    }
    json.dump(summary, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
