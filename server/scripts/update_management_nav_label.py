"""Update the /management navigation item label to 'Operaciones'."""
from __future__ import annotations

import os
import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from dotenv import load_dotenv
from pymongo import MongoClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def main() -> None:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27018")
    mongo_database = os.getenv("MONGO_DATABASE", "hoteldata_hub")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client[mongo_database]

    result = db.navigation.update_one(
        {"href": "/management"},
        {"$set": {"label": "Operaciones"}},
    )
    print(f"matched={result.matched_count} modified={result.modified_count}")
    client.close()


if __name__ == "__main__":
    main()
