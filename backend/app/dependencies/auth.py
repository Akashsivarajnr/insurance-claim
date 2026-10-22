from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.database import MongoSession, get_db
from app.models import Role, User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: MongoSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None:
        raise unauthorized
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise unauthorized
    doc = db.users.find_one({"id": user_id})
    if doc is None:
        raise unauthorized
    return User(**doc)


def require_customer(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.CUSTOMER.value:
        raise HTTPException(status_code=403, detail="This action is only available to customers.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ADMIN.value:
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user
