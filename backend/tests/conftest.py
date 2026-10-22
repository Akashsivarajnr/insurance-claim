import os
import tempfile

# Isolated test database + upload folder: set BEFORE the app is imported.
_TMP = tempfile.mkdtemp(prefix="claimflow_test_")
os.environ["MONGODB_DB_NAME"] = "claimflow_test"
os.environ["UPLOAD_DIR"] = os.path.join(_TMP, "uploads")
os.environ["SECRET_KEY"] = "test-secret-key-not-for-real-use-0123456789"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.database import MongoSession, get_client, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Role, User, utcnow  # noqa: E402
from app.seed import seed_policies  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.4\n" + b"0" * 64


@pytest.fixture(autouse=True)
def fresh_db():
    client = get_client()
    client.drop_database("claimflow_test")
    init_db()
    with MongoSession() as db:
        seed_policies(db)
        uid = db.next_id("users")
        admin_user = User(
            id=uid,
            full_name="Test Admin",
            email="admin@test.com",
            hashed_password=hash_password("Admin12345"),
            role=Role.ADMIN.value,
            created_at=utcnow(),
        )
        db.users.insert_one(admin_user.to_dict())
    yield


@pytest.fixture()
def client():
    return TestClient(app)


def _auth(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def admin(client):
    return _auth(client, "admin@test.com", "Admin12345")


def make_customer(client, email, name="Customer One"):
    r = client.post("/api/auth/register", json={"full_name": name, "email": email, "password": "Passw0rd123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def alice(client):
    return make_customer(client, "alice@test.com", "Alice Smith")


@pytest.fixture()
def bob(client):
    return make_customer(client, "bob@test.com", "Bob Jones")


CLAIM = {
    "policy_number": "HLT-1001",
    "claim_type": "Health",
    "incident_date": "2025-01-15",
    "incident_description": "Hospital admission for appendix surgery.",
    "requested_amount": 20000,
}


@pytest.fixture()
def claim(client, alice):
    r = client.post("/api/claims", json=CLAIM, headers=alice)
    assert r.status_code == 201, r.text
    return r.json()
