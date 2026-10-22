from datetime import date, datetime, timezone
from enum import Enum


def utcnow() -> datetime:
    """Naive UTC timestamp."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_dt(v) -> datetime:
    if v is None:
        return utcnow()
    if isinstance(v, datetime):
        return v.replace(tzinfo=None) if v.tzinfo else v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v)
        except Exception:
            return utcnow()
    return utcnow()


def parse_date(v) -> date | None:
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        try:
            return date.fromisoformat(v[:10])
        except Exception:
            return None
    return None


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


class User:
    def __init__(self, **kwargs):
        self.id: int = int(kwargs.get("id") or kwargs.get("_id") or 0)
        self.full_name: str = kwargs.get("full_name", "")
        self.email: str = (kwargs.get("email") or "").lower()
        self.hashed_password: str = kwargs.get("hashed_password", "")
        self.phone: str | None = kwargs.get("phone")
        self.role: str = kwargs.get("role", Role.CUSTOMER.value)
        self.created_at: datetime = parse_dt(kwargs.get("created_at"))

    def to_dict(self) -> dict:
        return {
            "_id": self.id,
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "hashed_password": self.hashed_password,
            "phone": self.phone,
            "role": self.role,
            "created_at": self.created_at,
        }


class InsurancePolicy:
    def __init__(self, **kwargs):
        self.id: int = int(kwargs.get("id") or kwargs.get("_id") or 0)
        self.policy_number: str = kwargs.get("policy_number", "")
        self.policy_name: str = kwargs.get("policy_name", "")
        self.policy_type: str = kwargs.get("policy_type", "")
        self.coverage_amount: float = float(kwargs.get("coverage_amount", 0.0))
        self.premium_amount: float = float(kwargs.get("premium_amount", 0.0))
        self.description: str = kwargs.get("description", "")
        self.is_active: bool = bool(kwargs.get("is_active", True))

    def to_dict(self) -> dict:
        return {
            "_id": self.id,
            "id": self.id,
            "policy_number": self.policy_number,
            "policy_name": self.policy_name,
            "policy_type": self.policy_type,
            "coverage_amount": self.coverage_amount,
            "premium_amount": self.premium_amount,
            "description": self.description,
            "is_active": self.is_active,
        }


class ClaimDocument:
    def __init__(self, **kwargs):
        self.id: int = int(kwargs.get("id") or kwargs.get("_id") or 0)
        self.claim_id: int = int(kwargs.get("claim_id", 0))
        self.original_filename: str = kwargs.get("original_filename", "")
        self.stored_filename: str = kwargs.get("stored_filename", "")
        self.document_type: str = kwargs.get("document_type", "Supporting Document")
        self.content_type: str = kwargs.get("content_type", "")
        self.file_size: int = int(kwargs.get("file_size", 0))
        self.uploaded_at: datetime = parse_dt(kwargs.get("uploaded_at"))
        self.verification_status: str = kwargs.get("verification_status", VerificationStatus.PENDING.value)
        self.admin_comment: str | None = kwargs.get("admin_comment")
        self.claim: "Claim | None" = kwargs.get("claim")

    def to_dict(self) -> dict:
        return {
            "_id": self.id,
            "id": self.id,
            "claim_id": self.claim_id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "document_type": self.document_type,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "uploaded_at": self.uploaded_at,
            "verification_status": self.verification_status,
            "admin_comment": self.admin_comment,
        }


class ClaimHistory:
    def __init__(self, **kwargs):
        self.id: int = int(kwargs.get("id") or kwargs.get("_id") or 0)
        self.claim_id: int = int(kwargs.get("claim_id", 0))
        self.previous_status: str | None = kwargs.get("previous_status")
        self.new_status: str = kwargs.get("new_status", "")
        self.changed_by: int | None = kwargs.get("changed_by")
        self.comment: str | None = kwargs.get("comment")
        self.changed_at: datetime = parse_dt(kwargs.get("changed_at"))
        self._changed_by_name: str | None = kwargs.get("changed_by_name")

    @property
    def changed_by_name(self) -> str | None:
        return self._changed_by_name

    @changed_by_name.setter
    def changed_by_name(self, value: str | None) -> None:
        self._changed_by_name = value

    def to_dict(self) -> dict:
        return {
            "_id": self.id,
            "id": self.id,
            "claim_id": self.claim_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "changed_by": self.changed_by,
            "comment": self.comment,
            "changed_at": self.changed_at,
        }


class Notification:
    def __init__(self, **kwargs):
        self.id: int = int(kwargs.get("id") or kwargs.get("_id") or 0)
        self.user_id: int = int(kwargs.get("user_id", 0))
        self.claim_id: int | None = kwargs.get("claim_id")
        self.message: str = kwargs.get("message", "")
        self.is_read: bool = bool(kwargs.get("is_read", False))
        self.created_at: datetime = parse_dt(kwargs.get("created_at"))

    def to_dict(self) -> dict:
        return {
            "_id": self.id,
            "id": self.id,
            "user_id": self.user_id,
            "claim_id": self.claim_id,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at,
        }


class Claim:
    def __init__(self, **kwargs):
        self.id: int = int(kwargs.get("id") or kwargs.get("_id") or 0)
        self.claim_reference: str = kwargs.get("claim_reference", "")
        self.user_id: int = int(kwargs.get("user_id", 0))
        self.policy_id: int = int(kwargs.get("policy_id", 0))
        self.claim_type: str = kwargs.get("claim_type", "")
        self.incident_date: date | None = parse_date(kwargs.get("incident_date"))
        self.incident_description: str = kwargs.get("incident_description", "")
        self.requested_amount: float = float(kwargs.get("requested_amount", 0.0))
        self.approved_amount: float | None = (
            float(kwargs["approved_amount"]) if kwargs.get("approved_amount") is not None else None
        )
        self.status: str = kwargs.get("status", ClaimStatus.SUBMITTED.value)
        self.admin_comments: str | None = kwargs.get("admin_comments")
        self.submitted_at: datetime = parse_dt(kwargs.get("submitted_at"))
        self.updated_at: datetime = parse_dt(kwargs.get("updated_at"))
        self.settlement_date: date | None = parse_date(kwargs.get("settlement_date"))
        self.settlement_reference: str | None = kwargs.get("settlement_reference")

        # Hydrated relationships/properties
        self.user: "User | None" = kwargs.get("user")
        self.policy: "InsurancePolicy | None" = kwargs.get("policy")
        self._customer_name: str | None = kwargs.get("customer_name")
        self._policy_number: str | None = kwargs.get("policy_number")
        self._policy_name: str | None = kwargs.get("policy_name")
        self.documents: list[ClaimDocument] = kwargs.get("documents", [])
        self.history: list[ClaimHistory] = kwargs.get("history", [])

    @property
    def customer_name(self) -> str:
        if self._customer_name:
            return self._customer_name
        return self.user.full_name if self.user else ""

    @customer_name.setter
    def customer_name(self, value: str) -> None:
        self._customer_name = value

    @property
    def policy_number(self) -> str:
        if self._policy_number:
            return self._policy_number
        return self.policy.policy_number if self.policy else ""

    @policy_number.setter
    def policy_number(self, value: str) -> None:
        self._policy_number = value

    @property
    def policy_name(self) -> str:
        if self._policy_name:
            return self._policy_name
        return self.policy.policy_name if self.policy else ""

    @policy_name.setter
    def policy_name(self, value: str) -> None:
        self._policy_name = value

    def to_dict(self) -> dict:
        return {
            "_id": self.id,
            "id": self.id,
            "claim_reference": self.claim_reference,
            "user_id": self.user_id,
            "policy_id": self.policy_id,
            "claim_type": self.claim_type,
            "incident_date": self.incident_date.isoformat() if self.incident_date else None,
            "incident_description": self.incident_description,
            "requested_amount": self.requested_amount,
            "approved_amount": self.approved_amount,
            "status": self.status,
            "admin_comments": self.admin_comments,
            "submitted_at": self.submitted_at,
            "updated_at": self.updated_at,
            "settlement_date": self.settlement_date.isoformat() if self.settlement_date else None,
            "settlement_reference": self.settlement_reference,
        }
