"""OPTIONAL: fill the database with demo customers and claims so dashboards and charts have data.

Run AFTER creating an administrator (python create_admin.py). Safe to run more than once.
Demo customer login: customer@claimflow.com / Customer123
"""
import sys
from datetime import date, datetime, timedelta

from sqlalchemy import func, select

from app.core.security import hash_password
from app.database import SessionLocal, init_db
from app.models import Claim, ClaimHistory, InsurancePolicy, Role, User, utcnow
from app.seed import seed_policies
from app.services import claims as svc
from app.services.notifications import notify

DEMO = [  # policy, amount, days ago, final status path, approved amount
    ("HLT-1001", 42000, 150, ["Under Review", "Approved", "Settlement Pending", "Settled"], 40000),
    ("MTR-2001", 65000, 110, ["Under Review", "Approved", "Settlement Pending"], 60000),
    ("HOM-3001", 180000, 75, ["Under Review", "Rejected"], None),
    ("TRV-4001", 22000, 40, ["Documents Required"], None),
    ("HLT-1002", 90000, 20, ["Under Review"], None),
    ("MTR-2001", 15000, 5, [], None),
]


def main() -> int:
    init_db()
    with SessionLocal() as db:
        seed_policies(db)
        admin = db.scalar(select(User).where(User.role == Role.ADMIN.value).order_by(User.id))
        if not admin:
            print("Create an administrator first:  python create_admin.py")
            return 1
        cust = db.scalar(select(User).where(func.lower(User.email) == "customer@claimflow.com"))
        if not cust:
            cust = User(full_name="Demo Customer", email="customer@claimflow.com", phone="+91 90000 00000",
                        hashed_password=hash_password("Customer123"), role=Role.CUSTOMER.value)
            db.add(cust)
            db.flush()
        if db.scalar(select(func.count()).select_from(Claim).where(Claim.user_id == cust.id)):
            print("Demo claims already exist - nothing to do.")
            db.commit()
            return 0
        for number, amount, ago, path, approved in DEMO:
            policy = db.scalar(select(InsurancePolicy).where(InsurancePolicy.policy_number == number))
            when = utcnow() - timedelta(days=ago)
            claim = Claim(claim_reference=svc.generate_reference(db), user_id=cust.id, policy_id=policy.id,
                          claim_type=policy.policy_type, incident_date=(when - timedelta(days=3)).date(),
                          incident_description=f"Sample {policy.policy_type.lower()} claim created for demonstration purposes.",
                          requested_amount=amount, submitted_at=when, updated_at=when)
            db.add(claim)
            db.flush()
            db.add(ClaimHistory(claim_id=claim.id, previous_status=None, new_status="Submitted",
                                changed_by=cust.id, comment="Claim submitted by customer", changed_at=when))
            notify(db, claim, f"Your claim {claim.claim_reference} was submitted successfully.")
            for step in path:
                comment = {"Documents Required": "Please upload the original invoice.", "Rejected": "Damage is not covered under this policy."}.get(step)
                svc.change_status(db, claim, step, admin, comment)
                if step == "Approved":
                    claim.approved_amount = approved
                if step == "Settled":
                    claim.settlement_date = date.today() - timedelta(days=max(ago - 30, 1))
                    claim.settlement_reference = f"TXN-DEMO-{claim.id:04d}"
            for h in claim.history[1:]:
                h.changed_at = when + timedelta(days=2)
        db.commit()
    print("Demo data created. Customer login: customer@claimflow.com / Customer123")
    return 0


if __name__ == "__main__":
    sys.exit(main())
