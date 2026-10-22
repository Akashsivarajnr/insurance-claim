import re
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.database import MongoSession, get_db
from app.dependencies.auth import get_current_user, require_customer
from app.models import (
    Claim,
    ClaimDocument,
    ClaimHistory,
    ClaimStatus as S,
    InsurancePolicy,
    Role,
    User,
    VerificationStatus,
    utcnow,
)
from app.schemas import ClaimCreate, ClaimDetail, ClaimSummary, DocumentOut, HistoryOut, Page
from app.services import claims as svc
from app.services import uploads
from app.services.notifications import notify

router = APIRouter(tags=["Claims"])
MAX_DOCS_PER_CLAIM = 10
DOC_TYPES = {
    "Identity Proof",
    "Policy Document",
    "Medical Report",
    "Bill / Invoice",
    "Police / FIR Report",
    "Photograph",
    "Supporting Document",
}


def hydrate_claim(db: MongoSession, doc: dict, include_details: bool = False) -> Claim:
    claim = Claim(**doc)
    user_doc = db.users.find_one({"id": claim.user_id})
    policy_doc = db.policies.find_one({"id": claim.policy_id})
    claim.user = User(**user_doc) if user_doc else None
    claim.policy = InsurancePolicy(**policy_doc) if policy_doc else None
    claim.customer_name = claim.user.full_name if claim.user else ""
    claim.policy_number = claim.policy.policy_number if claim.policy else ""
    claim.policy_name = claim.policy.policy_name if claim.policy else ""

    if include_details:
        doc_cursor = db.claim_documents.find({"claim_id": claim.id}).sort("id", 1)
        doc_list = []
        for d in doc_cursor:
            cd = ClaimDocument(**d)
            cd.claim = claim
            doc_list.append(cd)
        claim.documents = doc_list

        hist_cursor = db.claim_history.find({"claim_id": claim.id}).sort("id", 1)
        history_list = []
        for h in hist_cursor:
            entry = ClaimHistory(**h)
            if entry.changed_by:
                actor = db.users.find_one({"id": entry.changed_by})
                entry.changed_by_name = actor["full_name"] if actor else None
            history_list.append(entry)
        claim.history = history_list

    return claim


def get_claim_for_user(db: MongoSession, claim_id: int, user: User) -> Claim:
    doc = db.claims.find_one({"id": claim_id})
    if not doc or (user.role != Role.ADMIN.value and doc["user_id"] != user.id):
        raise HTTPException(status_code=404, detail="Claim not found.")
    return hydrate_claim(db, doc, include_details=True)


@router.post("/api/claims", response_model=ClaimDetail, status_code=status.HTTP_201_CREATED)
def create_claim(
    body: ClaimCreate, user: User = Depends(require_customer), db: MongoSession = Depends(get_db)
):
    policy_doc = db.policies.find_one({"policy_number": body.policy_number})
    if not policy_doc or not policy_doc.get("is_active"):
        raise HTTPException(status_code=404, detail="No active policy found with that policy number.")
    if policy_doc.get("policy_type") != body.claim_type:
        raise HTTPException(
            status_code=422,
            detail=f"This is a {policy_doc.get('policy_type')} policy; claim type must be {policy_doc.get('policy_type')}.",
        )
    if body.requested_amount > policy_doc.get("coverage_amount", 0):
        raise HTTPException(
            status_code=422,
            detail=f"Requested amount exceeds the policy coverage of {policy_doc.get('coverage_amount', 0):,.2f}.",
        )

    cid = db.next_id("claims")
    now = utcnow()
    ref = svc.generate_reference(db)
    claim = Claim(
        id=cid,
        claim_reference=ref,
        user_id=user.id,
        policy_id=policy_doc["id"],
        claim_type=body.claim_type,
        incident_date=body.incident_date,
        incident_description=body.incident_description,
        requested_amount=round(body.requested_amount, 2),
        status=S.SUBMITTED.value,
        submitted_at=now,
        updated_at=now,
    )
    db.claims.insert_one(claim.to_dict())

    hid = db.next_id("claim_history")
    history_entry = ClaimHistory(
        id=hid,
        claim_id=claim.id,
        previous_status=None,
        new_status=S.SUBMITTED.value,
        changed_by=user.id,
        comment="Claim submitted by customer",
        changed_at=now,
    )
    db.claim_history.insert_one(history_entry.to_dict())

    notify(db, claim, f"Your claim {claim.claim_reference} was submitted successfully.")
    return hydrate_claim(db, claim.to_dict(), include_details=True)


@router.get("/api/claims/my", response_model=Page[ClaimSummary])
def my_claims(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = None,
    user: User = Depends(require_customer),
    db: MongoSession = Depends(get_db),
):
    query_filter: dict = {"user_id": user.id}
    if status_filter:
        query_filter["status"] = status_filter
    if search and search.strip():
        query_filter["claim_reference"] = {"$regex": re.escape(search.strip()), "$options": "i"}

    total = db.claims.count_documents(query_filter)
    cursor = (
        db.claims.find(query_filter)
        .sort([("submitted_at", -1), ("id", -1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [hydrate_claim(db, c) for c in cursor]
    return Page(items=items, total=total, page=page, page_size=page_size, pages=svc.paginate(total, page, page_size))


@router.get("/api/claims/my/stats")
def my_stats(user: User = Depends(require_customer), db: MongoSession = Depends(get_db)):
    pipe = [
        {"$match": {"user_id": user.id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    rows = {r["_id"]: r["count"] for r in db.claims.aggregate(pipe)}
    total = sum(rows.values())

    recent_cursor = db.claims.find({"user_id": user.id}).sort([("updated_at", -1), ("id", -1)]).limit(5)
    recent = [hydrate_claim(db, c) for c in recent_cursor]

    appr_pipe = [
        {"$match": {"user_id": user.id}},
        {"$group": {"_id": None, "total": {"$sum": "$approved_amount"}}},
    ]
    appr_res = list(db.claims.aggregate(appr_pipe))
    approved_total = float(appr_res[0]["total"]) if appr_res else 0.0

    return {
        "total_claims": total,
        "under_review": rows.get(S.UNDER_REVIEW.value, 0)
        + rows.get(S.SUBMITTED.value, 0)
        + rows.get(S.DOCUMENTS_REQUIRED.value, 0),
        "approved": rows.get(S.APPROVED.value, 0)
        + rows.get(S.SETTLEMENT_PENDING.value, 0)
        + rows.get(S.SETTLED.value, 0),
        "rejected": rows.get(S.REJECTED.value, 0),
        "settled": rows.get(S.SETTLED.value, 0),
        "documents_required": rows.get(S.DOCUMENTS_REQUIRED.value, 0),
        "total_approved_amount": approved_total,
        "recent": [ClaimSummary.model_validate(c) for c in recent],
    }


@router.get("/api/claims/{claim_id}", response_model=ClaimDetail)
def get_claim(
    claim_id: int, user: User = Depends(get_current_user), db: MongoSession = Depends(get_db)
):
    return get_claim_for_user(db, claim_id, user)


@router.get("/api/claims/{claim_id}/history", response_model=list[HistoryOut])
def claim_history(
    claim_id: int, user: User = Depends(get_current_user), db: MongoSession = Depends(get_db)
):
    return get_claim_for_user(db, claim_id, user).history


@router.post("/api/claims/{claim_id}/documents", response_model=list[DocumentOut], status_code=status.HTTP_201_CREATED)
async def upload_documents(
    claim_id: int,
    files: list[UploadFile] = File(...),
    document_type: str = Form("Supporting Document"),
    user: User = Depends(require_customer),
    db: MongoSession = Depends(get_db),
):
    claim = get_claim_for_user(db, claim_id, user)
    if claim.status not in svc.UPLOAD_OPEN_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Documents cannot be added to a claim that is {claim.status}.",
        )
    if document_type not in DOC_TYPES:
        document_type = "Supporting Document"
    if not files:
        raise HTTPException(status_code=400, detail="Please choose at least one file.")
    existing_docs = db.claim_documents.count_documents({"claim_id": claim.id})
    if existing_docs + len(files) > MAX_DOCS_PER_CLAIM:
        raise HTTPException(
            status_code=400, detail=f"A claim can have at most {MAX_DOCS_PER_CLAIM} documents."
        )

    saved, created = [], []
    try:
        for f in files:
            saved.append(await uploads.validate_and_save(f))
        for original, stored, ctype, size in saved:
            did = db.next_id("claim_documents")
            doc = ClaimDocument(
                id=did,
                claim_id=claim.id,
                original_filename=original,
                stored_filename=stored,
                document_type=document_type,
                content_type=ctype,
                file_size=size,
                uploaded_at=utcnow(),
                verification_status=VerificationStatus.PENDING.value,
                admin_comment=None,
            )
            db.claim_documents.insert_one(doc.to_dict())
            created.append(doc)

        if claim.status == S.DOCUMENTS_REQUIRED.value:
            svc.change_status(
                db,
                claim,
                S.UNDER_REVIEW.value,
                user,
                "Customer uploaded additional documents",
                notify_customer=False,
            )
            notify(
                db,
                claim,
                f"Thanks - your additional documents for {claim.claim_reference} were received and the claim is back under review.",
            )

        now = utcnow()
        claim.updated_at = now
        db.claims.update_one({"id": claim.id}, {"$set": {"updated_at": now}})
    except Exception:
        for _, stored, _, _ in saved:
            try:
                (uploads.upload_root() / stored).unlink(missing_ok=True)
            except OSError:
                pass
        raise

    return created


@router.get("/api/documents/{document_id}/download")
def download_document(
    document_id: int, user: User = Depends(get_current_user), db: MongoSession = Depends(get_db)
):
    doc = db.claim_documents.find_one({"id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    get_claim_for_user(db, doc["claim_id"], user)
    path = uploads.stored_path(doc["stored_filename"])
    return FileResponse(
        path,
        media_type=doc["content_type"],
        filename=doc["original_filename"],
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )
