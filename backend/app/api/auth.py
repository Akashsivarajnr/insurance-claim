from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import create_access_token, hash_password, verify_password
from app.database import MongoSession, get_db
from app.dependencies.auth import get_current_user
from app.models import Role, User, utcnow
from app.schemas import LoginRequest, ProfileUpdate, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: MongoSession = Depends(get_db)):
    email = body.email.lower()
    if db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user_id = db.next_id("users")
    user = User(
        id=user_id,
        full_name=body.full_name,
        email=email,
        phone=body.phone,
        hashed_password=hash_password(body.password),
        role=Role.CUSTOMER.value,
        created_at=utcnow(),
    )
    db.users.insert_one(user.to_dict())
    return TokenResponse(access_token=create_access_token(user.id, user.role), user=user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: MongoSession = Depends(get_db)):
    doc = db.users.find_one({"email": body.email.lower()})
    user = User(**doc) if doc else None
    if not verify_password(body.password, user.hashed_password if user else None):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return TokenResponse(access_token=create_access_token(user.id, user.role), user=user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(
    body: ProfileUpdate, user: User = Depends(get_current_user), db: MongoSession = Depends(get_db)
):
    db.users.update_one(
        {"id": user.id},
        {"$set": {"full_name": body.full_name, "phone": body.phone}},
    )
    user.full_name = body.full_name
    user.phone = body.phone
    return user
