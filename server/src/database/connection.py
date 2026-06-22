from __future__ import annotations

from pymongo import MongoClient

from config.settings import get_settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    return _client


def get_database():
    return get_client()[get_settings().mongo_database]
