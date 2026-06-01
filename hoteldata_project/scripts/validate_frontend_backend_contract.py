from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
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
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    endpoints = [
        {"route": "/auth/login", "kind": "legacy_html", "required_json": False},
        {"route": "/auth/me", "kind": "legacy_html_or_redirect", "required_json": False},
        {"route": "/api/auth/me", "kind": "json_auth_probe", "required_json": True},
        {"route": "/api/reservations", "kind": "json_private", "required_json": True},
        {"route": "/api/reservations/options", "kind": "json_private", "required_json": True},
        {"route": "/api/hotels/search", "kind": "json_public", "required_json": True},
        {"route": "/api/hotels/1", "kind": "json_public", "required_json": True},
        {"route": "/api/dashboard/overview", "kind": "json_private", "required_json": True},
        {"route": "/api/management/properties", "kind": "json_private", "required_json": True},
        {"route": "/api/management/properties/1", "kind": "json_private", "required_json": True},
        {"route": "/api/management/rooms?prop_id=1", "kind": "json_private", "required_json": True},
        {"route": "/api/management/availability?prop_id=1", "kind": "json_private", "required_json": True},
        {"route": "/api/management/rates?prop_id=1", "kind": "json_private", "required_json": True},
        {"route": "/api/management/policies?prop_id=1", "kind": "json_private", "required_json": True},
        {"route": "/api/management/amenities?prop_id=1", "kind": "json_private", "required_json": True},
        {"route": "/api/management/check-ins", "kind": "json_private", "required_json": True},
        {"route": "/api/management/check-outs", "kind": "json_private", "required_json": True},
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
        "results": results,
        "ok_count": sum(1 for item in results if item["contract_ok"]),
        "error_count": sum(1 for item in results if not item["contract_ok"]),
    }
    json.dump(summary, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
