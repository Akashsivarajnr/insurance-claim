from sqlalchemy.orm import Session

from app.models import Claim, Notification


def notify(db: Session, claim: Claim, message: str) -> None:
    """Add an in-app notification for the claim owner (committed by the caller)."""
    db.add(Notification(user_id=claim.user_id, claim_id=claim.id, message=message))
