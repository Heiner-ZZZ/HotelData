from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlencode

import requests

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta variable requerida en .env: {name}")
    return value


def authenticate(base_url: str, admin_email: str, admin_password: str) -> str:
    auth_url = f"{base_url}/api/collections/_superusers/auth-with-password"
    response = requests.post(
        auth_url,
        json={"identity": admin_email, "password": admin_password},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["token"]


def pocketbase_request(url: str, token: str) -> dict:
    response = requests.get(
        url,
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return {"status_code": response.status_code, "payload": response.json()}


def main() -> None:
    base_url = get_required_env("POCKETBASE_URL").rstrip("/")
    collection = get_required_env("POCKETBASE_COLLECTION")
    admin_email = get_required_env("POCKETBASE_ADMIN_EMAIL")
    admin_password = get_required_env("POCKETBASE_ADMIN_PASSWORD")

    token = authenticate(base_url, admin_email, admin_password)
    query = urlencode({"page": 1, "perPage": 5})
    url = f"{base_url}/api/collections/{collection}/records?{query}"

    result = pocketbase_request(url, token)
    payload = result["payload"]
    items = payload.get("items", [])
    columns = sorted({column for item in items for column in item.keys()})

    print(f"URL usada: {url}")
    print(f"coleccion usada: {collection}")
    print(f"status code: {result['status_code']}")
    print(f"totalItems: {payload.get('totalItems', 0)}")
    print("primeros 5 registros:")
    print(json.dumps(items, indent=2, ensure_ascii=False))
    print("columnas detectadas:")
    print(json.dumps(columns, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
