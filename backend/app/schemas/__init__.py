import re
from datetime import date, datetime
from typing import Annotated, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, field_validator, model_validator

# Datetimes are stored as naive UTC; send them with a "Z" so browsers show local time correctly.
UTCDateTime = Annotated[datetime, PlainSerializer(
    lambda d: (d.isoformat() + "Z") if d.tzinfo is None else d.isoformat(), return_type=str)]

T = TypeVar("T")
ORM = ConfigDict(from_attributes=True)
ClaimTypeLiteral = Literal["Health", "Motor", "Home", "Travel", "Life"]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class Message(BaseModel):
    message: str


def _validate_phone(v: Optional[str]) -> Optional[str]:
    if v is None or v.strip() == "":
        return None
    v = v.strip()
    if not re.fullmatch(r"[0-9+\-() ]{7,20}", v):
        raise ValueError("Phone number may only contain digits, spaces, +, -, ( and ) and must be 7-20 characters")
    return v


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    phone: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def _name(cls, v):
        return v.strip()

    @field_validator("password")
    @classmethod
    def _password(cls, v):
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("Password must contain at least one letter and one number")
        return v

    _phone = field_validator("phone")(_validate_phone)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=64)


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def _name(cls, v):
        return v.strip()

    _phone = field_validator("phone")(_validate_phone)


class UserOut(BaseModel):
    model_config = ORM
    id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    role: str
    created_at: UTCDateTime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PolicyOut(BaseModel):
    model_config = ORM
    id: int
    policy_number: str
    policy_name: str
    policy_type: str
    coverage_amount: float
    premium_amount: float
    description: str
    is_active: bool


class ClaimCreate(BaseModel):
    policy_number: str = Field(min_length=3, max_length=40)
    claim_type: ClaimTypeLiteral
    incident_date: date
    incident_description: str = Field(min_length=10, max_length=3000)
    requested_amount: float = Field(gt=0, le=100_000_000)

    @field_validator("policy_number")
    @classmethod
    def _pn(cls, v):
        return v.strip().upper()

    @field_validator("incident_date")
    @classmethod
    def _date(cls, v):
        if v > date.today():
            raise ValueError("Incident date cannot be in the future")
        return v

    @field_validator("incident_description")
    @classmethod
    def _desc(cls, v):
        return v.strip()


class DocumentOut(BaseModel):
    model_config = ORM
    id: int
    claim_id: int
    original_filename: str
    document_type: str
    content_type: str
    file_size: int
    uploaded_at: UTCDateTime
    verification_status: str
    admin_comment: Optional[str] = None


class HistoryOut(BaseModel):
    model_config = ORM
    id: int
    claim_id: int
    previous_status: Optional[str] = None
    new_status: str
    changed_by: Optional[int] = None
    changed_by_name: Optional[str] = None
    comment: Optional[str] = None
    changed_at: UTCDateTime


class ClaimSummary(BaseModel):
    model_config = ORM
    id: int
    claim_reference: str
    claim_type: str
    policy_number: str
    policy_name: str
    customer_name: str
    requested_amount: float
    approved_amount: Optional[float] = None
    status: str
    submitted_at: UTCDateTime
    updated_at: UTCDateTime
    settlement_date: Optional[date] = None


class CustomerBrief(BaseModel):
    model_config = ORM
    id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    created_at: UTCDateTime


class ClaimDetail(ClaimSummary):
    user_id: int
    policy_id: int
    incident_date: date
    incident_description: str
    admin_comments: Optional[str] = None
    settlement_reference: Optional[str] = None
    user: CustomerBrief
    policy: PolicyOut
    documents: list[DocumentOut]
    history: list[HistoryOut]


class StatusUpdate(BaseModel):
    status: Literal["Under Review", "Documents Required", "Approved", "Rejected"]
    comment: Optional[str] = Field(default=None, max_length=1000)
    approved_amount: Optional[float] = Field(default=None, ge=0)

    @field_validator("comment")
    @classmethod
    def _c(cls, v):
        return (v.strip() or None) if v else None


class CommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=1000)

    @field_validator("comment")
    @classmethod
    def _c(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Comment cannot be empty")
        return v


class SettlementUpdate(BaseModel):
    status: Literal["Settlement Pending", "Settled"]
    settlement_date: Optional[date] = None
    settlement_reference: Optional[str] = Field(default=None, max_length=80)
    comment: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("settlement_reference", "comment")
    @classmethod
    def _strip(cls, v):
        return (v.strip() or None) if v else None

    @model_validator(mode="after")
    def _settled(self):
        if self.status == "Settled" and (not self.settlement_date or not self.settlement_reference):
            raise ValueError("Settlement date and transaction reference are required to mark a claim as Settled")
        return self


class DocumentVerify(BaseModel):
    verification_status: Literal["Verified", "Needs Information", "Pending"]
    admin_comment: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _need_comment(self):
        if self.verification_status == "Needs Information" and not (self.admin_comment or "").strip():
            raise ValueError("Please describe what information is needed")
        return self


class NotificationOut(BaseModel):
    model_config = ORM
    id: int
    claim_id: Optional[int] = None
    message: str
    is_read: bool
    created_at: UTCDateTime


class CustomerOut(UserOut):
    claim_count: int = 0
    total_requested: float = 0
