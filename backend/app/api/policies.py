from fastapi import APIRouter, Depends, HTTPException

from app.database import MongoSession, get_db
from app.dependencies.auth import get_current_user
from app.models import InsurancePolicy, User
from app.schemas import PolicyOut

router = APIRouter(prefix="/api/policies", tags=["Policies"])


@router.get("", response_model=list[PolicyOut])
def list_policies(_: User = Depends(get_current_user), db: MongoSession = Depends(get_db)):
    cursor = db.policies.find({"is_active": True}).sort([("policy_type", 1), ("id", 1)])
    return [InsurancePolicy(**p) for p in cursor]


@router.get("/{policy_id}", response_model=PolicyOut)
def get_policy(policy_id: int, _: User = Depends(get_current_user), db: MongoSession = Depends(get_db)):
    doc = db.policies.find_one({"id": policy_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Policy not found.")
    return InsurancePolicy(**doc)
