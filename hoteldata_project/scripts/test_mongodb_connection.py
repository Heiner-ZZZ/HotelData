from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database


def main() -> None:
    db = get_database()
    db.command("ping")
    print(f"MongoDB connection OK: {db.name}")


if __name__ == "__main__":
    main()
