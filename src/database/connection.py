from __future__ import annotations

from pymongo import MongoClient

from config.settings import get_settings


def get_client() -> MongoClient:
    settings = get_settings()
    return MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)


def get_database():
    settings = get_settings()
    return get_client()[settings.mongo_database]
