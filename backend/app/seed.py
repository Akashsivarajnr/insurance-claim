from app.database import MongoSession
from app.models import InsurancePolicy

SAMPLE_POLICIES = [
    ("HLT-1001", "Family Health Shield", "Health", 500000, 18500, "Hospitalisation, surgery, day-care procedures and pre/post hospital expenses for you and your family."),
    ("HLT-1002", "Senior Care Plus", "Health", 750000, 32000, "Comprehensive health cover with critical illness benefits designed for customers aged 55 and above."),
    ("MTR-2001", "Comprehensive Motor Cover", "Motor", 800000, 14200, "Own-damage, third-party liability and theft cover for private cars and two-wheelers."),
    ("HOM-3001", "HomeSecure", "Home", 2500000, 9800, "Protection for your home structure and contents against fire, flood, burglary and natural calamities."),
    ("TRV-4001", "Globetrotter Travel", "Travel", 300000, 2400, "Medical emergencies, baggage loss, trip cancellation and flight delay cover while travelling."),
    ("LIF-5001", "LifeGuard Term Plan", "Life", 5000000, 21000, "Term life cover that provides financial security for your family."),
]


def seed_policies(db: MongoSession) -> None:
    if db.policies.count_documents({}) > 0:
        return
    for number, name, ptype, cover, premium, desc in SAMPLE_POLICIES:
        pid = db.next_id("insurance_policies")
        policy = InsurancePolicy(
            id=pid,
            policy_number=number,
            policy_name=name,
            policy_type=ptype,
            coverage_amount=cover,
            premium_amount=premium,
            description=desc,
            is_active=True,
        )
        db.policies.insert_one(policy.to_dict())
