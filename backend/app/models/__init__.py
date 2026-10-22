from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite does not keep timezone info)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"


class ClaimStatus(str, Enum):
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under Review"
    DOCUMENTS_REQUIRED = "Documents Required"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    SETTLEMENT_PENDING = "Settlement Pending"
    SETTLED = "Settled"


class VerificationStatus(str, Enum):
    PENDING = "Pending"
    VERIFIED = "Verified"
    NEEDS_INFO = "Needs Information"


CLAIM_TYPES = ["Health", "Motor", "Home", "Travel", "Life"]


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default=Role.CUSTOMER.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    claims: Mapped[list["Claim"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    policy_name: Mapped[str] = mapped_column(String(120))
    policy_type: Mapped[str] = mapped_column(String(30), index=True)
    coverage_amount: Mapped[float] = mapped_column(Float)
    premium_amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    claims: Mapped[list["Claim"]] = relationship(back_populates="policy")


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (Index("ix_claims_user_status", "user_id", "status"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_reference: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("insurance_policies.id"), index=True)
    claim_type: Mapped[str] = mapped_column(String(30), index=True)
    incident_date: Mapped[datetime] = mapped_column(Date)
    incident_description: Mapped[str] = mapped_column(Text)
    requested_amount: Mapped[float] = mapped_column(Float)
    approved_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default=ClaimStatus.SUBMITTED.value, index=True)
    admin_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    settlement_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    settlement_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)

    user: Mapped[User] = relationship(back_populates="claims")
    policy: Mapped[InsurancePolicy] = relationship(back_populates="claims")
    documents: Mapped[list["ClaimDocument"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan", order_by="ClaimDocument.id")
    history: Mapped[list["ClaimHistory"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan", order_by="ClaimHistory.id")

    @property
    def customer_name(self) -> str:
        return self.user.full_name

    @property
    def policy_number(self) -> str:
        return self.policy.policy_number

    @property
    def policy_name(self) -> str:
        return self.policy.policy_name


class ClaimDocument(Base):
    __tablename__ = "claim_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(80), unique=True)
    document_type: Mapped[str] = mapped_column(String(60), default="Supporting Document")
    content_type: Mapped[str] = mapped_column(String(60))
    file_size: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    verification_status: Mapped[str] = mapped_column(String(30), default=VerificationStatus.PENDING.value)
    admin_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    claim: Mapped[Claim] = relationship(back_populates="documents")


class ClaimHistory(Base):
    __tablename__ = "claim_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30))
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    claim: Mapped[Claim] = relationship(back_populates="history")
    actor: Mapped[User | None] = relationship()

    @property
    def changed_by_name(self) -> str | None:
        return self.actor.full_name if self.actor else None


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_read", "user_id", "is_read"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    claim_id: Mapped[int | None] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), nullable=True)
    message: Mapped[str] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="notifications")
