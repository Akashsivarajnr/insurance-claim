from app.database import MongoSession
from app.models import Claim, Notification, utcnow


def notify(db: MongoSession, claim: Claim, message: str) -> None:
    """Add an in-app notification for the claim owner."""
    nid = db.next_id("notifications")
    notif = Notification(
        id=nid,
        user_id=claim.user_id,
        claim_id=claim.id,
        message=message,
        is_read=False,
        created_at=utcnow(),
    )
    db.notifications.insert_one(notif.to_dict())
