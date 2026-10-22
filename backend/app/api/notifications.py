from fastapi import APIRouter, Depends, HTTPException

from app.database import MongoSession, get_db
from app.dependencies.auth import get_current_user
from app.models import Notification, User
from app.schemas import Message, NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(user: User = Depends(get_current_user), db: MongoSession = Depends(get_db)):
    cursor = db.notifications.find({"user_id": user.id}).sort([("created_at", -1), ("id", -1)]).limit(100)
    return [Notification(**n) for n in cursor]


@router.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), db: MongoSession = Depends(get_db)):
    n = db.notifications.count_documents({"user_id": user.id, "is_read": False})
    return {"unread": n}


@router.patch("/read-all", response_model=Message)
def read_all(user: User = Depends(get_current_user), db: MongoSession = Depends(get_db)):
    db.notifications.update_many({"user_id": user.id}, {"$set": {"is_read": True}})
    return Message(message="All notifications marked as read.")


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int, user: User = Depends(get_current_user), db: MongoSession = Depends(get_db)
):
    doc = db.notifications.find_one({"id": notification_id, "user_id": user.id})
    if not doc:
        raise HTTPException(status_code=404, detail="Notification not found.")
    db.notifications.update_one({"id": notification_id}, {"$set": {"is_read": True}})
    doc["is_read"] = True
    return Notification(**doc)
