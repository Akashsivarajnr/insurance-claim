"""Create (or promote) an administrator account. Safe to run more than once.

Usage (from the backend folder, with the virtual environment active):
    python create_admin.py                       -> asks for details
    python create_admin.py --email a@b.com --name "Admin" --password "YourPass123"
"""
import argparse
import getpass
import sys

from email_validator import EmailNotValidError, validate_email

from app.core.security import hash_password
from app.database import SessionLocal, init_db
from app.models import Role, User, utcnow
from app.seed import seed_policies


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--email")
    p.add_argument("--name")
    p.add_argument("--password")
    a = p.parse_args()
    email = (a.email or input("Admin email: ")).strip().lower()
    name = (a.name or input("Admin full name: ")).strip()
    password = a.password or getpass.getpass("Admin password (min 8 chars, letters + numbers): ")
    try:
        email = validate_email(email, check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        print(f"Invalid email: {exc}")
        return 1
    if len(name) < 2 or len(password) < 8 or len(password) > 64 or password.isalpha() or password.isdigit():
        print("Invalid input: need a name and a password of 8-64 characters with letters and numbers.")
        return 1
    init_db()
    with SessionLocal() as db:
        seed_policies(db)
        user_doc = db.users.find_one({"email": email})
        if user_doc:
            db.users.update_one(
                {"id": user_doc["id"]},
                {
                    "$set": {
                        "role": Role.ADMIN.value,
                        "full_name": name,
                        "hashed_password": hash_password(password),
                    }
                },
            )
            print(f"Existing account {email} updated and set to administrator.")
        else:
            uid = db.next_id("users")
            user = User(
                id=uid,
                full_name=name,
                email=email,
                hashed_password=hash_password(password),
                role=Role.ADMIN.value,
                created_at=utcnow(),
            )
            db.users.insert_one(user.to_dict())
            print(f"Administrator account created: {email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
