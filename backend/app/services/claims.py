import secrets
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Claim, ClaimHistory, ClaimStatus as S, User
from app.services.notifications import notify

# Allowed workflow transitions. Anything else is rejected with HTTP 409.
TRANSITIONS: dict[str, set[str]] = {
    S.SUBMITTED.value: {S.UNDER_REVIEW.value, S.DOCUMENTS_REQUIRED.value, S.REJECTED.value},
    S.UNDER_REVIEW.value: {S.DOCUMENTS_REQUIRED.value, S.APPROVED.value, S.REJECTED.value},
    S.DOCUMENTS_REQUIRED.value: {S.UNDER_REVIEW.value, S.REJECTED.value},
    S.APPROVED.value: {S.SETTLEMENT_PENDING.value},
    S.SETTLEMENT_PENDING.value: {S.SETTLED.value},
    S.REJECTED.value: set(),
    S.SETTLED.value: set(),
}
UPLOAD_OPEN_STATUSES = {S.SUBMITTED.value, S.UNDER_REVIEW.value, S.DOCUMENTS_REQUIRED.value}


def generate_reference(db: Session) -> str:
    for _ in range(10):
        ref = f"CF-{date.today().year}-{secrets.token_hex(3).upper()}"
        if not db.scalar(select(Claim.id).where(Claim.claim_reference == ref)):
            return ref
    raise HTTPException(status_code=500, detail="Could not generate a claim reference. Please try again.")


def change_status(db: Session, claim: Claim, new_status: str, actor: User, comment: str | None = None,
                  notify_customer: bool = True) -> None:
    current = claim.status
    if new_status not in TRANSITIONS.get(current, set()):
        raise HTTPException(status_code=409, detail=f"Invalid status change: '{current}' cannot move to '{new_status}'.")
    db.add(ClaimHistory(claim_id=claim.id, previous_status=current, new_status=new_status,
                        changed_by=actor.id, comment=comment))
    claim.status = new_status
    if comment:
        claim.admin_comments = comment
    if notify_customer:
        msg = f"Claim {claim.claim_reference} status changed from {current} to {new_status}."
        if comment:
            msg += f" Note: {comment}"
        notify(db, claim, msg[:500])


def paginate(total: int, page: int, page_size: int) -> int:
    return max(1, -(-total // page_size))
