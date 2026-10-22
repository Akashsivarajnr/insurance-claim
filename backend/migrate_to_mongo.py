"""Migrate existing data from SQLite (claimflow.db) to MongoDB (claimflow)."""
from datetime import datetime, timezone
import os
import sqlite3

from app.core.config import settings
from app.database import get_database, init_db

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "claimflow.db")


def parse_dt(v):
    if not v:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v)
        except Exception:
            try:
                return datetime.strptime(v, "%Y-%m-%d %H:%M:%S.%f")
            except Exception:
                return datetime.now(timezone.utc).replace(tzinfo=None)
    return v


def migrate():
    if not os.path.isfile(SQLITE_PATH):
        print(f"No SQLite database found at {SQLITE_PATH}. Nothing to migrate.")
        return

    init_db()
    db = get_database()
    con = sqlite3.connect(SQLITE_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    tables = [
        t[0]
        for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if not t[0].startswith("sqlite_")
    ]
    print(f"Found SQLite tables: {tables}")

    max_ids = {}

    # 1. users
    if "users" in tables:
        rows = cur.execute("SELECT * FROM users").fetchall()
        for r in rows:
            d = dict(r)
            d["_id"] = d["id"]
            d["created_at"] = parse_dt(d.get("created_at"))
            db.users.replace_one({"_id": d["_id"]}, d, upsert=True)
            max_ids["users"] = max(max_ids.get("users", 0), d["id"])
        print(f"Migrated {len(rows)} users.")

    # 2. insurance_policies
    if "insurance_policies" in tables:
        rows = cur.execute("SELECT * FROM insurance_policies").fetchall()
        for r in rows:
            d = dict(r)
            d["_id"] = d["id"]
            d["is_active"] = bool(d.get("is_active", 1))
            db.insurance_policies.replace_one({"_id": d["_id"]}, d, upsert=True)
            max_ids["insurance_policies"] = max(max_ids.get("insurance_policies", 0), d["id"])
        print(f"Migrated {len(rows)} insurance policies.")

    # 3. claims
    if "claims" in tables:
        rows = cur.execute("SELECT * FROM claims").fetchall()
        for r in rows:
            d = dict(r)
            d["_id"] = d["id"]
            d["submitted_at"] = parse_dt(d.get("submitted_at"))
            d["updated_at"] = parse_dt(d.get("updated_at"))
            db.claims.replace_one({"_id": d["_id"]}, d, upsert=True)
            max_ids["claims"] = max(max_ids.get("claims", 0), d["id"])
        print(f"Migrated {len(rows)} claims.")

    # 4. claim_documents
    if "claim_documents" in tables:
        rows = cur.execute("SELECT * FROM claim_documents").fetchall()
        for r in rows:
            d = dict(r)
            d["_id"] = d["id"]
            d["uploaded_at"] = parse_dt(d.get("uploaded_at"))
            db.claim_documents.replace_one({"_id": d["_id"]}, d, upsert=True)
            max_ids["claim_documents"] = max(max_ids.get("claim_documents", 0), d["id"])
        print(f"Migrated {len(rows)} claim documents.")

    # 5. claim_history
    if "claim_history" in tables:
        rows = cur.execute("SELECT * FROM claim_history").fetchall()
        for r in rows:
            d = dict(r)
            d["_id"] = d["id"]
            d["changed_at"] = parse_dt(d.get("changed_at"))
            db.claim_history.replace_one({"_id": d["_id"]}, d, upsert=True)
            max_ids["claim_history"] = max(max_ids.get("claim_history", 0), d["id"])
        print(f"Migrated {len(rows)} claim history records.")

    # 6. notifications
    if "notifications" in tables:
        rows = cur.execute("SELECT * FROM notifications").fetchall()
        for r in rows:
            d = dict(r)
            d["_id"] = d["id"]
            d["is_read"] = bool(d.get("is_read", 0))
            d["created_at"] = parse_dt(d.get("created_at"))
            db.notifications.replace_one({"_id": d["_id"]}, d, upsert=True)
            max_ids["notifications"] = max(max_ids.get("notifications", 0), d["id"])
        print(f"Migrated {len(rows)} notifications.")

    # Set counters
    for coll_name, max_id in max_ids.items():
        db.counters.replace_one(
            {"_id": coll_name},
            {"_id": coll_name, "seq": max_id},
            upsert=True,
        )
    print("Updated ID counters in MongoDB:", max_ids)
    print("Migration to MongoDB completed successfully!")


if __name__ == "__main__":
    migrate()
