from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user, require_customer
from app.models import Claim, ClaimDocument, ClaimHistory, ClaimStatus as S, InsurancePolicy, Role, User, utcnow
from app.schemas import ClaimCreate, ClaimDetail, ClaimSummary, DocumentOut, HistoryOut, Page
from app.services import claims as svc
from app.services import uploads
from app.services.notifications import notify

router = APIRouter(tags=["Claims"])
MAX_DOCS_PER_CLAIM = 10
DOC_TYPES = {"Identity Proof", "Policy Document", "Medical Report", "Bill / Invoice", "Police / FIR Report",
             "Photograph", "Supporting Document"}


def get_claim_for_user(db: Session, claim_id: int, user: User) -> Claim:
    """Customers only ever see their own claims; a foreign claim looks like it does not exist (404)."""
    claim = db.get(Claim, claim_id)
    if not claim or (user.role != Role.ADMIN.value and claim.user_id != user.id):
        raise HTTPException(status_code=404, detail="Claim not found.")
    return claim


@router.post("/api/claims", response_model=ClaimDetail, status_code=status.HTTP_201_CREATED)
def create_claim(body: ClaimCreate, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    policy = db.scalar(select(InsurancePolicy).where(InsurancePolicy.policy_number == body.policy_number))
    if not policy or not policy.is_active:
        raise HTTPException(status_code=404, detail="No active policy found with that policy number.")
    if policy.policy_type != body.claim_type:
        raise HTTPException(status_code=422, detail=f"This is a {policy.policy_type} policy; claim type must be {policy.policy_type}.")
    if body.requested_amount > policy.coverage_amount:
        raise HTTPException(status_code=422, detail=f"Requested amount exceeds the policy coverage of {policy.coverage_amount:,.2f}.")
    claim = Claim(claim_reference=svc.generate_reference(db), user_id=user.id, policy_id=policy.id,
                  claim_type=body.claim_type, incident_date=body.incident_date,
                  incident_description=body.incident_description, requested_amount=round(body.requested_amount, 2),
                  status=S.SUBMITTED.value)
    db.add(claim)
    db.flush()
    db.add(ClaimHistory(claim_id=claim.id, previous_status=None, new_status=S.SUBMITTED.value,
                        changed_by=user.id, comment="Claim submitted by customer"))
    notify(db, claim, f"Your claim {claim.claim_reference} was submitted successfully.")
    db.commit()
    db.refresh(claim)
    return claim


@router.get("/api/claims/my", response_model=Page[ClaimSummary])
def my_claims(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50),
              status_filter: str | None = Query(None, alias="status"), search: str | None = None,
              user: User = Depends(require_customer), db: Session = Depends(get_db)):
    q = select(Claim).where(Claim.user_id == user.id)
    if status_filter:
        q = q.where(Claim.status == status_filter)
    if search:
        q = q.where(Claim.claim_reference.ilike(f"%{search.strip()}%"))
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = db.scalars(q.order_by(Claim.submitted_at.desc(), Claim.id.desc())
                       .offset((page - 1) * page_size).limit(page_size)).all()
    return Page(items=items, total=total, page=page, page_size=page_size, pages=svc.paginate(total, page, page_size))


@router.get("/api/claims/my/stats")
def my_stats(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    rows = dict(db.execute(select(Claim.status, func.count()).where(Claim.user_id == user.id)
                           .group_by(Claim.status)).all())
    total = sum(rows.values())
    recent = db.scalars(select(Claim).where(Claim.user_id == user.id)
                        .order_by(Claim.updated_at.desc()).limit(5)).all()
    approved_total = db.scalar(select(func.coalesce(func.sum(Claim.approved_amount), 0))
                               .where(Claim.user_id == user.id)) or 0
    return {
        "total_claims": total,
        "under_review": rows.get(S.UNDER_REVIEW.value, 0) + rows.get(S.SUBMITTED.value, 0)
                        + rows.get(S.DOCUMENTS_REQUIRED.value, 0),
        "approved": rows.get(S.APPROVED.value, 0) + rows.get(S.SETTLEMENT_PENDING.value, 0) + rows.get(S.SETTLED.value, 0),
        "rejected": rows.get(S.REJECTED.value, 0),
        "settled": rows.get(S.SETTLED.value, 0),
        "documents_required": rows.get(S.DOCUMENTS_REQUIRED.value, 0),
        "total_approved_amount": approved_total,
        "recent": [ClaimSummary.model_validate(c) for c in recent],
    }


@router.get("/api/claims/{claim_id}", response_model=ClaimDetail)
def get_claim(claim_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_claim_for_user(db, claim_id, user)


@router.get("/api/claims/{claim_id}/history", response_model=list[HistoryOut])
def claim_history(claim_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_claim_for_user(db, claim_id, user).history


@router.post("/api/claims/{claim_id}/documents", response_model=list[DocumentOut], status_code=status.HTTP_201_CREATED)
async def upload_documents(claim_id: int, files: list[UploadFile] = File(...),
                           document_type: str = Form("Supporting Document"),
                           user: User = Depends(require_customer), db: Session = Depends(get_db)):
    claim = get_claim_for_user(db, claim_id, user)
    if claim.status not in svc.UPLOAD_OPEN_STATUSES:
        raise HTTPException(status_code=409, detail=f"Documents cannot be added to a claim that is {claim.status}.")
    if document_type not in DOC_TYPES:
        document_type = "Supporting Document"
    if not files:
        raise HTTPException(status_code=400, detail="Please choose at least one file.")
    if len(claim.documents) + len(files) > MAX_DOCS_PER_CLAIM:
        raise HTTPException(status_code=400, detail=f"A claim can have at most {MAX_DOCS_PER_CLAIM} documents.")

    saved, created = [], []
    try:
        for f in files:  # validate everything first; a bad file rejects the whole batch
            saved.append(await uploads.validate_and_save(f))
        for original, stored, ctype, size in saved:
            doc = ClaimDocument(claim_id=claim.id, original_filename=original, stored_filename=stored,
                                document_type=document_type, content_type=ctype, file_size=size)
            db.add(doc)
            created.append(doc)
        if claim.status == S.DOCUMENTS_REQUIRED.value:  # customer answered the request
            svc.change_status(db, claim, S.UNDER_REVIEW.value, user,
                              "Customer uploaded additional documents", notify_customer=False)
            notify(db, claim, f"Thanks - your additional documents for {claim.claim_reference} were received and the claim is back under review.")
        claim.updated_at = utcnow()
        db.commit()
    except Exception:
        db.rollback()
        for _, stored, _, _ in saved:  # remove orphaned files
            try:
                (uploads.upload_root() / stored).unlink(missing_ok=True)
            except OSError:
                pass
        raise
    for d in created:
        db.refresh(d)
    return created


@router.get("/api/documents/{document_id}/download")
def download_document(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.get(ClaimDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    get_claim_for_user(db, doc.claim_id, user)  # ownership / admin check
    path = uploads.stored_path(doc.stored_filename)
    return FileResponse(path, media_type=doc.content_type, filename=doc.original_filename,
                        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})
