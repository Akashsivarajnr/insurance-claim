from collections import OrderedDict
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models import (CLAIM_TYPES, Claim, ClaimDocument, ClaimHistory, ClaimStatus as S, Role, User,
                        VerificationStatus as V, utcnow)
from app.schemas import (ClaimDetail, ClaimSummary, CommentCreate, CustomerOut, DocumentOut, DocumentVerify, Page,
                         SettlementUpdate, StatusUpdate)
from app.services import claims as svc
from app.services.notifications import notify

router = APIRouter(prefix="/api/admin", tags=["Administrator"], dependencies=[Depends(require_admin)])
ALL_STATUSES = [s.value for s in S]


def _month_keys(n: int = 12) -> list[str]:
    today = date.today()
    y, m = today.year, today.month
    keys = []
    for _ in range(n):
        keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(keys))


def _status_counts(db: Session) -> dict[str, int]:
    rows = dict(db.execute(select(Claim.status, func.count()).group_by(Claim.status)).all())
    return {s: rows.get(s, 0) for s in ALL_STATUSES}


def _monthly(db: Session) -> list[dict]:
    keys = _month_keys()
    buckets = OrderedDict((k, {"month": k, "claims": 0, "requested": 0.0, "approved": 0.0}) for k in keys)
    for submitted_at, requested, approved in db.execute(
            select(Claim.submitted_at, Claim.requested_amount, Claim.approved_amount)).all():
        b = buckets.get(submitted_at.strftime("%Y-%m"))
        if b:
            b["claims"] += 1
            b["requested"] += requested or 0
            b["approved"] += approved or 0
    return list(buckets.values())


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    counts = _status_counts(db)
    customers = db.scalar(select(func.count()).select_from(User).where(User.role == Role.CUSTOMER.value)) or 0
    total_requested = db.scalar(select(func.coalesce(func.sum(Claim.requested_amount), 0))) or 0
    total_approved = db.scalar(select(func.coalesce(func.sum(Claim.approved_amount), 0))
                               .where(Claim.status.in_([S.APPROVED.value, S.SETTLEMENT_PENDING.value, S.SETTLED.value]))) or 0
    recent = db.scalars(select(Claim).order_by(Claim.updated_at.desc()).limit(6)).all()
    return {
        "total_customers": customers,
        "total_claims": sum(counts.values()),
        "awaiting_review": counts[S.SUBMITTED.value] + counts[S.UNDER_REVIEW.value],
        "documents_required": counts[S.DOCUMENTS_REQUIRED.value],
        "approved": counts[S.APPROVED.value] + counts[S.SETTLEMENT_PENDING.value] + counts[S.SETTLED.value],
        "rejected": counts[S.REJECTED.value],
        "pending_settlements": counts[S.APPROVED.value] + counts[S.SETTLEMENT_PENDING.value],
        "settled": counts[S.SETTLED.value],
        "total_requested_amount": total_requested,
        "total_approved_amount": total_approved,
        "status_distribution": [{"status": s, "count": c} for s, c in counts.items()],
        "monthly_claims": [{"month": m["month"], "claims": m["claims"]} for m in _monthly(db)],
        "recent": [ClaimSummary.model_validate(c) for c in recent],
    }


@router.get("/claims", response_model=Page[ClaimSummary])
def list_claims(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100),
                search: str | None = None, status_filter: str | None = Query(None, alias="status"),
                claim_type: str | None = None, date_from: date | None = None, date_to: date | None = None,
                settlement: bool = Query(False, description="Only claims in the settlement workflow"),
                db: Session = Depends(get_db)):
    q = select(Claim).join(User, Claim.user_id == User.id)
    if search and search.strip():
        like = f"%{search.strip()}%"
        q = q.where(or_(Claim.claim_reference.ilike(like), User.full_name.ilike(like)))
    if status_filter:
        if status_filter not in ALL_STATUSES:
            raise HTTPException(status_code=422, detail="Unknown status filter.")
        q = q.where(Claim.status == status_filter)
    if claim_type:
        q = q.where(Claim.claim_type == claim_type)
    if date_from:
        q = q.where(Claim.submitted_at >= datetime.combine(date_from, time.min))
    if date_to:
        q = q.where(Claim.submitted_at <= datetime.combine(date_to, time.max))
    if settlement:
        q = q.where(Claim.status.in_([S.APPROVED.value, S.SETTLEMENT_PENDING.value, S.SETTLED.value]))
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = db.scalars(q.order_by(Claim.submitted_at.desc(), Claim.id.desc())
                       .offset((page - 1) * page_size).limit(page_size)).all()
    return Page(items=items, total=total, page=page, page_size=page_size, pages=svc.paginate(total, page, page_size))


def _get_claim(db: Session, claim_id: int) -> Claim:
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")
    return claim


@router.get("/claims/{claim_id}", response_model=ClaimDetail)
def claim_detail(claim_id: int, db: Session = Depends(get_db)):
    return _get_claim(db, claim_id)


@router.patch("/claims/{claim_id}/status", response_model=ClaimDetail)
def update_status(claim_id: int, body: StatusUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    claim = _get_claim(db, claim_id)
    if body.status in (S.REJECTED.value, S.DOCUMENTS_REQUIRED.value) and not body.comment:
        raise HTTPException(status_code=422, detail="A comment is required when rejecting a claim or requesting documents.")
    if body.status == S.APPROVED.value:
        if body.approved_amount is None:
            raise HTTPException(status_code=422, detail="An approved amount is required to approve a claim.")
        if body.approved_amount > claim.requested_amount:
            raise HTTPException(status_code=422, detail="Approved amount cannot exceed the requested amount.")
    elif body.approved_amount is not None:
        raise HTTPException(status_code=422, detail="Approved amount can only be set when approving a claim.")
    svc.change_status(db, claim, body.status, admin, body.comment)  # validates the transition
    if body.status == S.APPROVED.value:
        claim.approved_amount = round(body.approved_amount, 2)
    db.commit()
    db.refresh(claim)
    return claim


@router.post("/claims/{claim_id}/comments", response_model=ClaimDetail)
def add_comment(claim_id: int, body: CommentCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    claim = _get_claim(db, claim_id)
    claim.admin_comments = body.comment
    db.add(ClaimHistory(claim_id=claim.id, previous_status=claim.status, new_status=claim.status,
                        changed_by=admin.id, comment=body.comment))
    notify(db, claim, f"New comment on claim {claim.claim_reference}: {body.comment}"[:500])
    db.commit()
    db.refresh(claim)
    return claim


@router.patch("/documents/{document_id}/verify", response_model=DocumentOut)
def verify_document(document_id: int, body: DocumentVerify, db: Session = Depends(get_db)):
    doc = db.get(ClaimDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc.verification_status = body.verification_status
    doc.admin_comment = (body.admin_comment or "").strip() or None
    if body.verification_status != V.PENDING.value:
        msg = f"Document '{doc.original_filename}' on claim {doc.claim.claim_reference} is now: {body.verification_status}."
        if doc.admin_comment:
            msg += f" {doc.admin_comment}"
        notify(db, doc.claim, msg[:500])
    db.commit()
    db.refresh(doc)
    return doc


@router.patch("/claims/{claim_id}/settlement", response_model=ClaimDetail)
def update_settlement(claim_id: int, body: SettlementUpdate, admin: User = Depends(require_admin),
                      db: Session = Depends(get_db)):
    claim = _get_claim(db, claim_id)
    if claim.status not in (S.APPROVED.value, S.SETTLEMENT_PENDING.value):
        raise HTTPException(status_code=409, detail="Only approved claims can enter the settlement workflow.")
    if body.status == S.SETTLED.value and body.settlement_date > date.today():
        raise HTTPException(status_code=422, detail="Settlement date cannot be in the future.")
    svc.change_status(db, claim, body.status, admin, body.comment)
    if body.settlement_date:
        claim.settlement_date = body.settlement_date
    if body.settlement_reference:
        claim.settlement_reference = body.settlement_reference
    db.commit()
    db.refresh(claim)
    return claim


@router.get("/customers", response_model=Page[CustomerOut])
def list_customers(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100),
                   search: str | None = None, db: Session = Depends(get_db)):
    q = select(User).where(User.role == Role.CUSTOMER.value)
    if search and search.strip():
        like = f"%{search.strip()}%"
        q = q.where(or_(User.full_name.ilike(like), User.email.ilike(like)))
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    users = db.scalars(q.order_by(User.created_at.desc(), User.id.desc())
                       .offset((page - 1) * page_size).limit(page_size)).all()
    stats = {uid: (n, amt) for uid, n, amt in db.execute(
        select(Claim.user_id, func.count(), func.coalesce(func.sum(Claim.requested_amount), 0))
        .where(Claim.user_id.in_([u.id for u in users])).group_by(Claim.user_id)).all()} if users else {}
    items = [CustomerOut(**{k: getattr(u, k) for k in ("id", "full_name", "email", "phone", "role", "created_at")},
                         claim_count=stats.get(u.id, (0, 0))[0], total_requested=stats.get(u.id, (0, 0))[1])
             for u in users]
    return Page(items=items, total=total, page=page, page_size=page_size, pages=svc.paginate(total, page, page_size))


@router.get("/reports")
def reports(db: Session = Depends(get_db)):
    counts = _status_counts(db)
    total = sum(counts.values())
    decided = counts[S.REJECTED.value] + counts[S.APPROVED.value] + counts[S.SETTLEMENT_PENDING.value] + counts[S.SETTLED.value]
    approved_n = decided - counts[S.REJECTED.value]
    by_type = []
    for t in CLAIM_TYPES:
        n, req, appr = db.execute(select(
            func.count(), func.coalesce(func.sum(Claim.requested_amount), 0),
            func.coalesce(func.sum(Claim.approved_amount), 0)).where(Claim.claim_type == t)).one()
        by_type.append({"claim_type": t, "claims": n, "requested": req, "approved": appr})
    settled_amount = db.scalar(select(func.coalesce(func.sum(Claim.approved_amount), 0))
                               .where(Claim.status == S.SETTLED.value)) or 0
    awaiting_amount = db.scalar(select(func.coalesce(func.sum(Claim.approved_amount), 0))
                                .where(Claim.status.in_([S.APPROVED.value, S.SETTLEMENT_PENDING.value]))) or 0
    # average days from submission to settlement for settled claims
    settled = db.execute(select(Claim.submitted_at, Claim.settlement_date).where(
        Claim.status == S.SETTLED.value, Claim.settlement_date.is_not(None))).all()
    avg_days = round(sum(max((d - s.date()).days, 0) for s, d in settled) / len(settled), 1) if settled else None
    return {
        "total_claims": total,
        "approval_rate": round(approved_n / decided * 100, 1) if decided else 0,
        "rejection_rate": round(counts[S.REJECTED.value] / decided * 100, 1) if decided else 0,
        "average_days_to_settle": avg_days,
        "settled_amount": settled_amount,
        "awaiting_settlement_amount": awaiting_amount,
        "by_type": by_type,
        "by_status": [{"status": s, "count": c} for s, c in counts.items()],
        "monthly": _monthly(db),
    }
