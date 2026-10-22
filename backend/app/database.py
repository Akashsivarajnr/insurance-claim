import os
from datetime import datetime, timezone
import pymongo
from pymongo import MongoClient, ReturnDocument

from app.core.config import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
    return _client


def get_database():
    db_name = os.environ.get("MONGODB_DB_NAME") or settings.mongodb_db_name
    return get_client()[db_name]


class MongoSession:
    def __init__(self, database=None):
        self.db = database if database is not None else get_database()
        self.users = self.db["users"]
        self.policies = self.db["insurance_policies"]
        self.claims = self.db["claims"]
        self.claim_documents = self.db["claim_documents"]
        self.claim_history = self.db["claim_history"]
        self.notifications = self.db["notifications"]
        self.counters = self.db["counters"]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def refresh(self, obj):
        pass

    def next_id(self, collection_name: str) -> int:
        doc = self.counters.find_one_and_update(
            {"_id": collection_name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        return doc["seq"]


SessionLocal = MongoSession


def get_db():
    with MongoSession() as s:
        try:
            yield s
        except Exception:
            raise


def init_db() -> None:
    session = MongoSession()
    # Ensure indexes
    session.users.create_index("email", unique=True)
    session.policies.create_index("policy_number", unique=True)
    session.claims.create_index("claim_reference", unique=True)
    session.claims.create_index([("user_id", 1), ("status", 1)])
    session.claims.create_index("submitted_at")
    session.claim_documents.create_index("stored_filename", unique=True)
    session.claim_documents.create_index("claim_id")
    session.claim_history.create_index("claim_id")
    session.notifications.create_index([("user_id", 1), ("is_read", 1)])
