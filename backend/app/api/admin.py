from collections import OrderedDict
from datetime import date, datetime, time
import re

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.claims import hydrate_claim
from app.database import MongoSession, get_db
from app.dependencies.auth import require_admin
from app.models import (
    CLAIM_TYPES,
    Claim,
    ClaimDocument,
    ClaimHistory,
    ClaimStatus as S,
    Role,
    User,
    VerificationStatus as V,
    parse_date,
    parse_dt,
    utcnow,
)
from app.schemas import (
    ClaimDetail,
    ClaimSummary,
    CommentCreate,
    CustomerOut,
    DocumentOut,
    DocumentVerify,
    Page,
    SettlementUpdate,
    StatusUpdate,
)
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


def _status_counts(db: MongoSession) -> dict[str, int]:
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    counts = {doc["_id"]: doc["count"] for doc in db.claims.aggregate(pipeline)}
    return {s: counts.get(s, 0) for s in ALL_STATUSES}


def _monthly(db: MongoSession) -> list[dict]:
    keys = _month_keys()
    buckets = OrderedDict((k, {"month": k, "claims": 0, "requested": 0.0, "approved": 0.0}) for k in keys)
    for c in db.claims.find({}, {"submitted_at": 1, "requested_amount": 1, "approved_amount": 1}):
        dt = c.get("submitted_at")
        if isinstance(dt, datetime):
            m = dt.strftime("%Y-%m")
        elif isinstance(dt, str):
            m = dt[:7]
        else:
            continue
        if m in buckets:
            buckets[m]["claims"] += 1
            buckets[m]["requested"] += float(c.get("requested_amount") or 0.0)
            buckets[m]["approved"] += float(c.get("approved_amount") or 0.0)
    return list(buckets.values())


@router.get("/dashboard")
def dashboard(db: MongoSession = Depends(get_db)):
    counts = _status_counts(db)
    customers = db.users.count_documents({"role": Role.CUSTOMER.value})

    req_pipeline = [{"$group": {"_id": None, "total": {"$sum": "$requested_amount"}}}]
    req_res = list(db.claims.aggregate(req_pipeline))
    total_requested = float(req_res[0]["total"]) if req_res else 0.0

    appr_pipeline = [
        {"$match": {"status": {"$in": [S.APPROVED.value, S.SETTLEMENT_PENDING.value, S.SETTLED.value]}}},
        {"$group": {"_id": None, "total": {"$sum": "$approved_amount"}}},
    ]
    appr_res = list(db.claims.aggregate(appr_pipeline))
    total_approved = float(appr_res[0]["total"]) if appr_res else 0.0

    recent_cursor = db.claims.find().sort([("updated_at", -1), ("id", -1)]).limit(6)
    recent = [hydrate_claim(db, c) for c in recent_cursor]

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
def list_claims(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    claim_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    settlement: bool = Query(False, description="Only claims in the settlement workflow"),
    db: MongoSession = Depends(get_db),
):
    q: dict = {}
    if search and search.strip():
        term = search.strip()
        matching_user_ids = [
            u["id"]
            for u in db.users.find({"full_name": {"$regex": re.escape(term), "$options": "i"}}, {"id": 1})
        ]
        q["$or"] = [
            {"claim_reference": {"$regex": re.escape(term), "$options": "i"}},
            {"user_id": {"$in": matching_user_ids}},
        ]
    if status_filter:
        if status_filter not in ALL_STATUSES:
            raise HTTPException(status_code=422, detail="Unknown status filter.")
        q["status"] = status_filter
    if claim_type:
        q["claim_type"] = claim_type
    if date_from or date_to:
        dt_cond: dict = {}
        if date_from:
            dt_cond["$gte"] = datetime.combine(date_from, time.min)
        if date_to:
            dt_cond["$lte"] = datetime.combine(date_to, time.max)
        q["submitted_at"] = dt_cond
    if settlement:
        q["status"] = {"$in": [S.APPROVED.value, S.SETTLEMENT_PENDING.value, S.SETTLED.value]}

    total = db.claims.count_documents(q)
    cursor = (
        db.claims.find(q)
        .sort([("submitted_at", -1), ("id", -1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [hydrate_claim(db, c) for c in cursor]
    return Page(items=items, total=total, page=page, page_size=page_size, pages=svc.paginate(total, page, page_size))


def _get_claim(db: MongoSession, claim_id: int) -> Claim:
    doc = db.claims.find_one({"id": claim_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Claim not found.")
    return hydrate_claim(db, doc, include_details=True)


@router.get("/claims/{claim_id}", response_model=ClaimDetail)
def claim_detail(claim_id: int, db: MongoSession = Depends(get_db)):
    return _get_claim(db, claim_id)


@router.patch("/claims/{claim_id}/status", response_model=ClaimDetail)
def update_status(
    claim_id: int,
    body: StatusUpdate,
    admin: User = Depends(require_admin),
    db: MongoSession = Depends(get_db),
):
    claim = _get_claim(db, claim_id)
    if body.status in (S.REJECTED.value, S.DOCUMENTS_REQUIRED.value) and not body.comment:
        raise HTTPException(
            status_code=422,
            detail="A comment is required when rejecting a claim or requesting documents.",
        )
    if body.status == S.APPROVED.value:
        if body.approved_amount is None:
            raise HTTPException(status_code=422, detail="An approved amount is required to approve a claim.")
        if body.approved_amount > claim.requested_amount:
            raise HTTPException(status_code=422, detail="Approved amount cannot exceed the requested amount.")
    elif body.approved_amount is not None:
        raise HTTPException(status_code=422, detail="Approved amount can only be set when approving a claim.")

    svc.change_status(db, claim, body.status, admin, body.comment)
    if body.status == S.APPROVED.value:
        claim.approved_amount = round(body.approved_amount, 2)
        db.claims.update_one({"id": claim.id}, {"$set": {"approved_amount": claim.approved_amount}})

    return _get_claim(db, claim_id)


@router.post("/claims/{claim_id}/comments", response_model=ClaimDetail)
def add_comment(
    claim_id: int,
    body: CommentCreate,
    admin: User = Depends(require_admin),
    db: MongoSession = Depends(get_db),
):
    claim = _get_claim(db, claim_id)
    claim.admin_comments = body.comment
    now = utcnow()
    hid = db.next_id("claim_history")
    history_entry = ClaimHistory(
        id=hid,
        claim_id=claim.id,
        previous_status=claim.status,
        new_status=claim.status,
        changed_by=admin.id,
        comment=body.comment,
        changed_at=now,
    )
    db.claim_history.insert_one(history_entry.to_dict())
    db.claims.update_one(
        {"id": claim.id}, {"$set": {"admin_comments": body.comment, "updated_at": now}}
    )
    notify(db, claim, f"New comment on claim {claim.claim_reference}: {body.comment}"[:500])
    return _get_claim(db, claim_id)


@router.patch("/documents/{document_id}/verify", response_model=DocumentOut)
def verify_document(document_id: int, body: DocumentVerify, db: MongoSession = Depends(get_db)):
    doc = db.claim_documents.find_one({"id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    comment = (body.admin_comment or "").strip() or None
    db.claim_documents.update_one(
        {"id": document_id},
        {"$set": {"verification_status": body.verification_status, "admin_comment": comment}},
    )
    doc["verification_status"] = body.verification_status
    doc["admin_comment"] = comment

    if body.verification_status != V.PENDING.value:
        claim_doc = db.claims.find_one({"id": doc["claim_id"]})
        if claim_doc:
            claim = Claim(**claim_doc)
            msg = f"Document '{doc['original_filename']}' on claim {claim.claim_reference} is now: {body.verification_status}."
            if comment:
                msg += f" {comment}"
            notify(db, claim, msg[:500])

    return ClaimDocument(**doc)


@router.patch("/claims/{claim_id}/settlement", response_model=ClaimDetail)
def update_settlement(
    claim_id: int,
    body: SettlementUpdate,
    admin: User = Depends(require_admin),
    db: MongoSession = Depends(get_db),
):
    claim = _get_claim(db, claim_id)
    if claim.status not in (S.APPROVED.value, S.SETTLEMENT_PENDING.value):
        raise HTTPException(status_code=409, detail="Only approved claims can enter the settlement workflow.")
    if body.status == S.SETTLED.value and body.settlement_date > date.today():
        raise HTTPException(status_code=422, detail="Settlement date cannot be in the future.")

    svc.change_status(db, claim, body.status, admin, body.comment)
    settlement_updates = {}
    if body.settlement_date:
        claim.settlement_date = body.settlement_date
        settlement_updates["settlement_date"] = body.settlement_date.isoformat()
    if body.settlement_reference:
        claim.settlement_reference = body.settlement_reference
        settlement_updates["settlement_reference"] = body.settlement_reference

    if settlement_updates:
        db.claims.update_one({"id": claim.id}, {"$set": settlement_updates})

    return _get_claim(db, claim_id)


@router.get("/customers", response_model=Page[CustomerOut])
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = None,
    db: MongoSession = Depends(get_db),
):
    q: dict = {"role": Role.CUSTOMER.value}
    if search and search.strip():
        term = search.strip()
        q["$or"] = [
            {"full_name": {"$regex": re.escape(term), "$options": "i"}},
            {"email": {"$regex": re.escape(term), "$options": "i"}},
        ]
    total = db.users.count_documents(q)
    cursor = (
        db.users.find(q)
        .sort([("created_at", -1), ("id", -1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    users = [User(**u) for u in cursor]

    user_ids = [u.id for u in users]
    stats_pipeline = [
        {"$match": {"user_id": {"$in": user_ids}}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}, "total_requested": {"$sum": "$requested_amount"}}},
    ]
    stats = {
        s["_id"]: (s["count"], float(s.get("total_requested") or 0.0))
        for s in db.claims.aggregate(stats_pipeline)
    }

    items = [
        CustomerOut(
            id=u.id,
            full_name=u.full_name,
            email=u.email,
            phone=u.phone,
            role=u.role,
            created_at=u.created_at,
            claim_count=stats.get(u.id, (0, 0.0))[0],
            total_requested=stats.get(u.id, (0, 0.0))[1],
        )
        for u in users
    ]
    return Page(items=items, total=total, page=page, page_size=page_size, pages=svc.paginate(total, page, page_size))


@router.get("/reports")
def reports(db: MongoSession = Depends(get_db)):
    counts = _status_counts(db)
    total = sum(counts.values())
    decided = (
        counts[S.REJECTED.value]
        + counts[S.APPROVED.value]
        + counts[S.SETTLEMENT_PENDING.value]
        + counts[S.SETTLED.value]
    )
    approved_n = decided - counts[S.REJECTED.value]

    by_type = []
    for t in CLAIM_TYPES:
        pipe = [
            {"$match": {"claim_type": t}},
            {
                "$group": {
                    "_id": None,
                    "count": {"$sum": 1},
                    "requested": {"$sum": "$requested_amount"},
                    "approved": {"$sum": "$approved_amount"},
                }
            },
        ]
        res = list(db.claims.aggregate(pipe))
        if res:
            by_type.append({
                "claim_type": t,
                "claims": res[0]["count"],
                "requested": float(res[0]["requested"] or 0.0),
                "approved": float(res[0]["approved"] or 0.0),
            })
        else:
            by_type.append({"claim_type": t, "claims": 0, "requested": 0.0, "approved": 0.0})

    settled_pipe = [
        {"$match": {"status": S.SETTLED.value}},
        {"$group": {"_id": None, "total": {"$sum": "$approved_amount"}}},
    ]
    s_res = list(db.claims.aggregate(settled_pipe))
    settled_amount = float(s_res[0]["total"]) if s_res else 0.0

    awaiting_pipe = [
        {"$match": {"status": {"$in": [S.APPROVED.value, S.SETTLEMENT_PENDING.value]}}},
        {"$group": {"_id": None, "total": {"$sum": "$approved_amount"}}},
    ]
    a_res = list(db.claims.aggregate(awaiting_pipe))
    awaiting_amount = float(a_res[0]["total"]) if a_res else 0.0

    # average days to settle
    settled_claims = list(
        db.claims.find(
            {"status": S.SETTLED.value, "settlement_date": {"$ne": None}},
            {"submitted_at": 1, "settlement_date": 1},
        )
    )
    days_list = []
    for sc in settled_claims:
        s_date = parse_date(sc.get("submitted_at"))
        set_date = parse_date(sc.get("settlement_date"))
        if s_date and set_date:
            days_list.append(max((set_date - s_date).days, 0))

    avg_days = round(sum(days_list) / len(days_list), 1) if days_list else None

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
