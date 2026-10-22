from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import InsurancePolicy, User
from app.schemas import PolicyOut

router = APIRouter(prefix="/api/policies", tags=["Policies"])


@router.get("", response_model=list[PolicyOut])
def list_policies(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(InsurancePolicy).where(InsurancePolicy.is_active.is_(True))
                      .order_by(InsurancePolicy.policy_type, InsurancePolicy.id)).all()


@router.get("/{policy_id}", response_model=PolicyOut)
def get_policy(policy_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    policy = db.get(InsurancePolicy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")
    return policy
