from conftest import CLAIM, PDF, PNG, make_customer


def set_status(client, admin, cid, status, **extra):
    return client.patch(f"/api/admin/claims/{cid}/status", json={"status": status, **extra}, headers=admin)


# ---------- authentication ----------
def test_register_and_login(client):
    r = client.post("/api/auth/register", json={"full_name": "New User", "email": "new@test.com", "password": "Passw0rd123"})
    assert r.status_code == 201
    assert r.json()["user"]["role"] == "customer"
    assert "hashed_password" not in r.text
    r = client.post("/api/auth/login", json={"email": "new@test.com", "password": "Passw0rd123"})
    assert r.status_code == 200
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == "new@test.com"


def test_register_cannot_choose_admin_role(client):
    r = client.post("/api/auth/register", json={"full_name": "Sneaky", "email": "s@test.com",
                                                "password": "Passw0rd123", "role": "admin"})
    assert r.status_code == 201 and r.json()["user"]["role"] == "customer"


def test_duplicate_and_weak_registration(client, alice):
    dup = client.post("/api/auth/register", json={"full_name": "Alice", "email": "ALICE@test.com", "password": "Passw0rd123"})
    assert dup.status_code == 409
    weak = client.post("/api/auth/register", json={"full_name": "Weak", "email": "w@test.com", "password": "password"})
    assert weak.status_code == 422


def test_invalid_credentials(client, alice):
    assert client.post("/api/auth/login", json={"email": "alice@test.com", "password": "wrong-pass1"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "Passw0rd123"}).status_code == 401
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_profile_update(client, alice):
    r = client.patch("/api/auth/me", json={"full_name": "Alice Updated", "phone": "+91 98765 43210"}, headers=alice)
    assert r.status_code == 200 and r.json()["full_name"] == "Alice Updated"
    assert client.patch("/api/auth/me", json={"full_name": "A", "phone": "abc"}, headers=alice).status_code == 422


# ---------- claim submission ----------
def test_policies_listed(client, alice):
    r = client.get("/api/policies", headers=alice)
    assert r.status_code == 200 and len(r.json()) >= 5
    assert client.get("/api/policies/1", headers=alice).status_code == 200
    assert client.get("/api/policies/999", headers=alice).status_code == 404


def test_submit_claim(client, alice, claim):
    assert claim["claim_reference"].startswith("CF-")
    assert claim["status"] == "Submitted"
    assert len(claim["history"]) == 1 and claim["history"][0]["new_status"] == "Submitted"
    notes = client.get("/api/notifications", headers=alice).json()
    assert any(claim["claim_reference"] in n["message"] for n in notes)
    mine = client.get("/api/claims/my", headers=alice).json()
    assert mine["total"] == 1 and mine["items"][0]["claim_reference"] == claim["claim_reference"]


def test_claim_validation(client, alice):
    bad = [
        {**CLAIM, "incident_date": "2999-01-01"},
        {**CLAIM, "requested_amount": -5},
        {**CLAIM, "requested_amount": 99_000_000},
        {**CLAIM, "incident_description": "short"},
        {**CLAIM, "policy_number": "NOPE-1"},
        {**CLAIM, "claim_type": "Motor"},
    ]
    for payload in bad:
        assert client.post("/api/claims", json=payload, headers=alice).status_code in (404, 422), payload


def test_admin_cannot_submit_claim(client, admin):
    assert client.post("/api/claims", json=CLAIM, headers=admin).status_code == 403


# ---------- ownership / authorization ----------
def test_customers_cannot_see_each_others_claims(client, alice, bob, claim):
    cid = claim["id"]
    assert client.get(f"/api/claims/{cid}", headers=bob).status_code == 404
    assert client.get(f"/api/claims/{cid}/history", headers=bob).status_code == 404
    assert client.post(f"/api/claims/{cid}/documents", files={"files": ("a.png", PNG, "image/png")}, headers=bob).status_code == 404
    assert client.get("/api/claims/my", headers=bob).json()["total"] == 0
    assert client.get(f"/api/claims/{cid}", headers=alice).status_code == 200


def test_admin_endpoints_blocked_for_customers_and_anonymous(client, alice, claim):
    urls = [("get", "/api/admin/dashboard"), ("get", "/api/admin/claims"), ("get", "/api/admin/customers"),
            ("get", "/api/admin/reports"), ("get", f"/api/admin/claims/{claim['id']}")]
    for method, url in urls:
        assert getattr(client, method)(url, headers=alice).status_code == 403, url
        assert getattr(client, method)(url).status_code == 401, url
    assert client.patch(f"/api/admin/claims/{claim['id']}/status", json={"status": "Approved", "approved_amount": 1}, headers=alice).status_code == 403
    assert client.patch(f"/api/admin/claims/{claim['id']}/settlement", json={"status": "Settlement Pending"}, headers=alice).status_code == 403


# ---------- documents ----------
def upload(client, headers, cid, name, content, ctype="application/octet-stream"):
    return client.post(f"/api/claims/{cid}/documents", files={"files": (name, content, ctype)},
                       data={"document_type": "Medical Report"}, headers=headers)


def test_document_upload_and_protected_download(client, alice, bob, admin, claim):
    r = upload(client, alice, claim["id"], "../../evil name.pdf", PDF, "application/pdf")
    assert r.status_code == 201, r.text
    doc = r.json()[0]
    assert doc["original_filename"] == "evil name.pdf"            # path stripped
    assert client.get(f"/api/documents/{doc['id']}/download", headers=alice).status_code == 200
    assert client.get(f"/api/documents/{doc['id']}/download", headers=admin).status_code == 200
    assert client.get(f"/api/documents/{doc['id']}/download", headers=bob).status_code == 404
    assert client.get(f"/api/documents/{doc['id']}/download").status_code == 401
    assert client.get("/uploads/anything.pdf").status_code == 404   # uploads are not a static folder


def test_document_upload_validation(client, alice, claim):
    cid = claim["id"]
    assert upload(client, alice, cid, "x.exe", b"MZ" + b"0" * 50).status_code == 400            # extension
    assert upload(client, alice, cid, "fake.png", b"this is not a png at all").status_code == 400  # content
    assert upload(client, alice, cid, "mismatch.jpg", PNG).status_code == 400                    # png named jpg
    assert upload(client, alice, cid, "empty.pdf", b"").status_code == 400
    assert upload(client, alice, cid, "big.pdf", b"%PDF-" + b"0" * (5 * 1024 * 1024 + 10)).status_code == 413
    assert upload(client, alice, cid, "ok.png", PNG, "image/png").status_code == 201


# ---------- workflow ----------
def test_full_approval_and_settlement_flow(client, alice, admin, claim):
    cid = claim["id"]
    assert set_status(client, admin, cid, "Under Review").status_code == 200
    r = set_status(client, admin, cid, "Approved", approved_amount=15000, comment="Approved after review")
    assert r.status_code == 200 and r.json()["approved_amount"] == 15000
    r = client.patch(f"/api/admin/claims/{cid}/settlement", json={"status": "Settlement Pending"}, headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "Settlement Pending"
    r = client.patch(f"/api/admin/claims/{cid}/settlement",
                     json={"status": "Settled", "settlement_date": "2025-02-01", "settlement_reference": "TXN-12345"}, headers=admin)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "Settled" and body["settlement_reference"] == "TXN-12345" and body["settlement_date"] == "2025-02-01"
    path = [h["new_status"] for h in client.get(f"/api/claims/{cid}/history", headers=alice).json()]
    assert path == ["Submitted", "Under Review", "Approved", "Settlement Pending", "Settled"]
    hist = client.get(f"/api/claims/{cid}/history", headers=alice).json()
    assert hist[2]["previous_status"] == "Under Review" and hist[2]["comment"] == "Approved after review"
    msgs = " ".join(n["message"] for n in client.get("/api/notifications", headers=alice).json())
    assert "Approved" in msgs and "Settled" in msgs


def test_invalid_transitions_rejected(client, admin, claim):
    cid = claim["id"]
    assert set_status(client, admin, cid, "Approved", approved_amount=100).status_code == 409   # Submitted -> Approved
    assert client.patch(f"/api/admin/claims/{cid}/settlement", json={"status": "Settlement Pending"}, headers=admin).status_code == 409
    assert set_status(client, admin, cid, "Rejected", comment="Not covered").status_code == 200
    assert set_status(client, admin, cid, "Under Review").status_code == 409                    # terminal
    assert client.patch(f"/api/admin/claims/{cid}/status", json={"status": "Settled"}, headers=admin).status_code == 422


def test_approval_amount_rules(client, admin, claim):
    cid = claim["id"]
    set_status(client, admin, cid, "Under Review")
    assert set_status(client, admin, cid, "Approved").status_code == 422                        # amount missing
    assert set_status(client, admin, cid, "Approved", approved_amount=-1).status_code == 422
    assert set_status(client, admin, cid, "Approved", approved_amount=20001).status_code == 422  # > requested
    assert set_status(client, admin, cid, "Rejected").status_code == 422                        # comment required
    assert set_status(client, admin, cid, "Approved", approved_amount=20000).status_code == 200


def test_documents_required_flow(client, alice, admin, claim):
    cid = claim["id"]
    assert set_status(client, admin, cid, "Documents Required").status_code == 422              # needs comment
    assert set_status(client, admin, cid, "Documents Required", comment="Please upload the hospital bill").status_code == 200
    d = client.get(f"/api/claims/{cid}", headers=alice).json()
    assert d["status"] == "Documents Required" and "hospital bill" in d["admin_comments"]
    assert upload(client, alice, cid, "bill.pdf", PDF, "application/pdf").status_code == 201
    assert client.get(f"/api/claims/{cid}", headers=alice).json()["status"] == "Under Review"


def test_document_verification(client, alice, admin, claim):
    doc = upload(client, alice, claim["id"], "id.png", PNG, "image/png").json()[0]
    assert doc["verification_status"] == "Pending"
    url = f"/api/admin/documents/{doc['id']}/verify"
    assert client.patch(url, json={"verification_status": "Needs Information"}, headers=admin).status_code == 422
    r = client.patch(url, json={"verification_status": "Verified", "admin_comment": "Looks good"}, headers=admin)
    assert r.status_code == 200 and r.json()["verification_status"] == "Verified"
    assert client.patch(url, json={"verification_status": "Verified"}, headers=alice).status_code == 403


def test_no_uploads_on_closed_claims(client, alice, admin, claim):
    set_status(client, admin, claim["id"], "Rejected", comment="Not covered")
    assert upload(client, alice, claim["id"], "late.pdf", PDF, "application/pdf").status_code == 409


def test_admin_comment_recorded(client, alice, admin, claim):
    r = client.post(f"/api/admin/claims/{claim['id']}/comments", json={"comment": "Checking with hospital"}, headers=admin)
    assert r.status_code == 200 and r.json()["admin_comments"] == "Checking with hospital"
    assert client.get(f"/api/claims/{claim['id']}", headers=alice).json()["history"][-1]["comment"] == "Checking with hospital"


# ---------- listing, filtering, dashboards ----------
def test_admin_search_filter_pagination(client, admin, alice, bob, claim):
    client.post("/api/claims", json={**CLAIM, "policy_number": "MTR-2001", "claim_type": "Motor"}, headers=bob)
    assert client.get("/api/admin/claims", headers=admin).json()["total"] == 2
    assert client.get("/api/admin/claims?search=Bob", headers=admin).json()["total"] == 1
    assert client.get(f"/api/admin/claims?search={claim['claim_reference'][:8]}", headers=admin).json()["total"] == 2
    assert client.get("/api/admin/claims?claim_type=Motor", headers=admin).json()["total"] == 1
    assert client.get("/api/admin/claims?status=Approved", headers=admin).json()["total"] == 0
    assert client.get("/api/admin/claims?date_from=2000-01-01&date_to=2999-01-01", headers=admin).json()["total"] == 2
    p = client.get("/api/admin/claims?page=2&page_size=1", headers=admin).json()
    assert p["pages"] == 2 and len(p["items"]) == 1
    assert client.get("/api/admin/claims?status=Bogus", headers=admin).status_code == 422
    cust = client.get("/api/admin/customers", headers=admin).json()
    assert cust["total"] == 2 and all(c["role"] == "customer" for c in cust["items"])


def test_dashboard_statistics_come_from_database(client, alice, bob, admin, claim):
    empty = client.get("/api/admin/dashboard", headers=admin).json()
    assert empty["total_claims"] == 1 and empty["total_customers"] == 2 and empty["awaiting_review"] == 1
    c2 = client.post("/api/claims", json={**CLAIM, "requested_amount": 10000}, headers=bob).json()
    set_status(client, admin, c2["id"], "Under Review")
    set_status(client, admin, c2["id"], "Approved", approved_amount=8000)
    d = client.get("/api/admin/dashboard", headers=admin).json()
    assert d["total_claims"] == 2 and d["approved"] == 1 and d["pending_settlements"] == 1
    assert d["total_requested_amount"] == 30000 and d["total_approved_amount"] == 8000
    dist = {x["status"]: x["count"] for x in d["status_distribution"]}
    assert dist["Submitted"] == 1 and dist["Approved"] == 1
    assert sum(m["claims"] for m in d["monthly_claims"]) == 2
    rep = client.get("/api/admin/reports", headers=admin).json()
    assert rep["total_claims"] == 2 and rep["approval_rate"] == 100
    mine = client.get("/api/claims/my/stats", headers=bob).json()
    assert mine["total_claims"] == 1 and mine["approved"] == 1 and mine["total_approved_amount"] == 8000


def test_notifications_are_private(client, alice, bob, claim):
    n = client.get("/api/notifications", headers=alice).json()[0]
    assert client.patch(f"/api/notifications/{n['id']}/read", headers=bob).status_code == 404
    r = client.patch(f"/api/notifications/{n['id']}/read", headers=alice)
    assert r.status_code == 200 and r.json()["is_read"] is True
    assert client.get("/api/notifications/unread-count", headers=alice).json()["unread"] == 0
