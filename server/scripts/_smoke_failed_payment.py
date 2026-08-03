"""Smoke test temporal: crea un pago fallido vía API y lo limpia al final."""
from __future__ import annotations

import json
import urllib.request

from config.settings import get_settings
from pymongo import MongoClient

BASE = "http://localhost:8000/api"


def _req(method: str, url: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def main() -> None:
    # 1. Login
    code, body = _req(
        "POST", f"{BASE}/auth/login",
        {"identifier": "superadmin", "password": "Admin12345*"},
    )
    print("login:", code)
    token = (body.get("session") or {}).get("access_token") or body.get("access_token") or body.get("token")
    if not token:
        print("no token:", json.dumps(body, default=str)[:400])
        return

    # 2. Invalid booking -> 400 con mensaje claro
    code, body = _req(
        "POST", f"{BASE}/billing/payments",
        {"booking_id": "NONEXISTENT-123", "amount": 10.0, "method": "card", "status": "failed"},
        token,
    )
    print("invalid booking ->", code, "|", body.get("detail", "")[:80])

    # 3. Crear pago fallido real y limpiarlo al final
    settings = get_settings()
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]
    booking = db.booking_orders.find_one({"prop_id": 1}, {"booking_id": 1})
    if not booking:
        print("no booking for prop 1; skip")
        return
    bid = booking["booking_id"]
    code, body = _req(
        "POST", f"{BASE}/billing/payments",
        {"booking_id": bid, "amount": 42.50, "method": "card", "status": "failed"},
        token,
    )
    print("create failed ->", code, "| status:", body.get("status"), "| ref:", body.get("reference", ""))
    pay_id = body.get("id")
    if code == 201 and pay_id:
        # Limpiar ambas colecciones
        from bson import ObjectId
        op = db.reservation_payments.delete_one({"_id": ObjectId(pay_id)})
        fact = db.fact_reservation_payments.delete_one({"_id": ObjectId(pay_id)})
        print("cleanup -> op:", op.deleted_count, "fact:", fact.deleted_count)
    client.close()


if __name__ == "__main__":
    main()
