import os
import tempfile

# Isolated test database + upload folder: set BEFORE the app is imported.
_TMP = tempfile.mkdtemp(prefix="claimflow_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP.replace(chr(92), '/')}/test.db"
os.environ["UPLOAD_DIR"] = os.path.join(_TMP, "uploads")
os.environ["SECRET_KEY"] = "test-secret-key-not-for-real-use-0123456789"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Role, User  # noqa: E402
from app.seed import seed_policies  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.4\n" + b"0" * 64


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_policies(db)
        db.add(User(full_name="Test Admin", email="admin@test.com", hashed_password=hash_password("Admin12345"),
                    role=Role.ADMIN.value))
        db.commit()
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


CLAIM = {"policy_number": "HLT-1001", "claim_type": "Health", "incident_date": "2025-01-15",
         "incident_description": "Hospital admission for appendix surgery.", "requested_amount": 20000}


@pytest.fixture()
def claim(client, alice):
    r = client.post("/api/claims", json=CLAIM, headers=alice)
    assert r.status_code == 201, r.text
    return r.json()
