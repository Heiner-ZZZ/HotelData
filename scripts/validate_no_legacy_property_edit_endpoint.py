from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / "frontend" / "src" / "app"
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "validate_no_legacy_property_edit_endpoint.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    matches: list[dict[str, object]] = []
    get_legacy_calls: list[dict[str, object]] = []

    for path in FRONTEND_ROOT.rglob("*.ts"):
        relative_path = path.relative_to(PROJECT_ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if "/management/properties/${propId}/edit" in line or re.search(r"/api/management/properties/.*/edit", line):
                matches.append({
                    "path": relative_path,
                    "line": lineno,
                    "content": line.strip(),
                })
            if "getLegacyEditProfile(" in line and "getLegacyEditProfile(propId: number)" not in line:
                get_legacy_calls.append({
                    "path": relative_path,
                    "line": lineno,
                    "content": line.strip(),
                })

    ok = not matches and not get_legacy_calls
    report = {
        "generated_at": utc_now_iso(),
        "ok": ok,
        "legacy_endpoint_references": matches,
        "legacy_method_usages": get_legacy_calls,
        "error_count": len(matches) + len(get_legacy_calls),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
