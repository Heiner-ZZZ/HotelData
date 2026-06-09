from __future__ import annotations

import json
import socket
import sys
from typing import Any

from pymongo import MongoClient


def check_port(host: str, port: int, timeout: float = 2.0) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def main() -> int:
    host = "localhost"
    port = 27017
    expected_docker_uri = "mongodb://host.docker.internal:27017"
    db_name = "hoteldata_hub"
    required_collections = {
        "users",
        "roles",
        "fact_hotel_reservations",
        "dim_hotels",
    }

    port_check = check_port(host, port)
    result: dict[str, Any] = {
        "local_mongo_host": host,
        "local_mongo_port": port,
        "docker_expected_uri": expected_docker_uri,
        "port_open": port_check["ok"],
        "port_error": port_check.get("error"),
        "database": db_name,
        "database_exists": False,
        "collections_present": [],
        "collections_missing": [],
    }

    if not port_check["ok"]:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 1

    client = MongoClient(f"mongodb://{host}:{port}", serverSelectionTimeoutMS=2000)
    try:
        database_names = set(client.list_database_names())
        result["database_exists"] = db_name in database_names
        if result["database_exists"]:
            collection_names = set(client[db_name].list_collection_names())
            result["collections_present"] = sorted(required_collections & collection_names)
            result["collections_missing"] = sorted(required_collections - collection_names)
        else:
            result["collections_missing"] = sorted(required_collections)
    finally:
        client.close()

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
