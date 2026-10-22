import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, FileQuestion, Play, XCircle } from "lucide-react";
import api, { errorMessage } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import Spinner from "../../components/Spinner";
import StatusBadge from "../../components/StatusBadge";
import DocumentList from "../../components/DocumentList";
import ClaimTimeline from "../../components/ClaimTimeline";
import Modal from "../../components/Modal";
import Field from "../../components/Field";
import SettlementForm from "../../components/SettlementForm";
import { dateOnly, money } from "../../utils/format";

// Mirrors the transitions enforced by the backend (the backend is still the final authority).
const NEXT = {
  Submitted: ["Under Review", "Documents Required", "Rejected"],
  "Under Review": ["Documents Required", "Approved", "Rejected"],
  "Documents Required": ["Under Review", "Rejected"],
};
const ACTIONS = {
  "Under Review": { label: "Start review", icon: Play, cls: "btn-primary", needComment: false, text: "Mark this claim as under review?" },
  "Documents Required": { label: "Request documents", icon: FileQuestion, cls: "btn-ghost", needComment: true, text: "Tell the customer which documents or details are missing." },
  Approved: { label: "Approve", icon: CheckCircle2, cls: "btn-success", needComment: false, text: "Enter the approved amount. It cannot exceed the requested amount." },
  Rejected: { label: "Reject", icon: XCircle, cls: "btn-danger", needComment: true, text: "Give the customer a reason. A rejected claim cannot be reopened." },
};

function StatusDialog({ claim, target, onClose, onDone }) {
  const toast = useToast();
  const a = ACTIONS[target];
  const [comment, setComment] = useState("");
  const [amount, setAmount] = useState(target === "Approved" ? String(claim.requested_amount) : "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (a.needComment && !comment.trim()) return setError("A comment is required for this action.");
    if (target === "Approved") {
      const n = Number(amount);
      if (amount === "" || Number.isNaN(n) || n < 0) return setError("Enter a valid approved amount (0 or more).");
      if (n > claim.requested_amount) return setError(`Approved amount cannot exceed ${money(claim.requested_amount)}.`);
    }
    setBusy(true);
    try {
      await api.patch(`/api/admin/claims/${claim.id}/status`, { status: target, comment: comment.trim() || null, approved_amount: target === "Approved" ? Number(amount) : null });
      toast.success(`Claim moved to ${target}.`);
      onDone();
    } catch (e) { setError(errorMessage(e)); }
    setBusy(false);
  };

  return (
    <Modal title={`${a.label} - ${claim.claim_reference}`} onClose={onClose}
      footer={<><button className="btn btn-ghost" onClick={onClose} disabled={busy}>Cancel</button><button className={`btn ${a.cls === "btn-ghost" ? "btn-primary" : a.cls}`} onClick={submit} disabled={busy}>{busy ? "Saving..." : `Confirm: ${a.label}`}</button></>}>
      <p>{a.text}</p>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {target === "Approved" && <Field label="Approved amount (INR)" hint={`Requested: ${money(claim.requested_amount)}`}><input type="number" min="0" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>}
      <Field label={a.needComment ? "Comment (required)" : "Comment (optional)"}><textarea rows={3} maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} /></Field>
    </Modal>
  );
}

function VerifyDialog({ doc, onClose, onDone }) {
  const toast = useToast();
  const [status, setStatus] = useState(doc.verification_status === "Pending" ? "Verified" : doc.verification_status);
  const [comment, setComment] = useState(doc.admin_comment || "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (status === "Needs Information" && !comment.trim()) return setError("Describe what information is needed.");
    setBusy(true);
    try {
      await api.patch(`/api/admin/documents/${doc.id}/verify`, { verification_status: status, admin_comment: comment.trim() || null });
      toast.success("Document updated.");
      onDone();
    } catch (e) { setError(errorMessage(e)); }
    setBusy(false);
  };
  return (
    <Modal title="Verify document" onClose={onClose} footer={<><button className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-primary" onClick={submit} disabled={busy}>{busy ? "Saving..." : "Save"}</button></>}>
      <p className="muted">{doc.original_filename}</p>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      <Field label="Verification result"><select value={status} onChange={(e) => setStatus(e.target.value)}><option>Verified</option><option>Needs Information</option><option>Pending</option></select></Field>
      <Field label="Comment"><textarea rows={3} maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} /></Field>
    </Modal>
  );
}

export default function ClaimReview() {
  const { id } = useParams();
  const toast = useToast();
  const [claim, setClaim] = useState(null);
  const [missing, setMissing] = useState(false);
  const [target, setTarget] = useState(null);
  const [verifyDoc, setVerifyDoc] = useState(null);
  const [settle, setSettle] = useState(false);
  const [note, setNote] = useState("");
  const [noteBusy, setNoteBusy] = useState(false);

  const load = useCallback(() => {
    api.get(`/api/admin/claims/${id}`).then((r) => setClaim(r.data)).catch((e) => {
      if (e.response?.status === 404) setMissing(true); else toast.error(errorMessage(e));
    });
  }, [id]); // eslint-disable-line
  useEffect(load, [load]);
  const done = () => { setTarget(null); setVerifyDoc(null); setSettle(false); load(); };

  const addNote = async () => {
    if (!note.trim()) return;
    setNoteBusy(true);
    try { await api.post(`/api/admin/claims/${id}/comments`, { comment: note }); toast.success("Comment added and sent to the customer."); setNote(""); load(); }
    catch (e) { toast.error(errorMessage(e)); }
    setNoteBusy(false);
  };

  if (missing) return <div className="panel center-text"><h1>Claim not found</h1><Link className="btn btn-primary" to="/admin/claims">Back to claims</Link></div>;
  if (!claim) return <Spinner />;
  const options = NEXT[claim.status] || [];
  const inSettlement = ["Approved", "Settlement Pending"].includes(claim.status);

  return (
    <>
      <Link to="/admin/claims" className="back"><ArrowLeft size={16} /> All claims</Link>
      <div className="page-head">
        <div><h1>{claim.claim_reference}</h1><p className="muted">{claim.claim_type} claim - {claim.policy_name} ({claim.policy_number})</p></div>
        <StatusBadge status={claim.status} />
      </div>

      <section className="panel">
        <h2>Decision</h2>
        {options.length === 0 && !inSettlement ? <p className="muted">This claim is {claim.status.toLowerCase()}. No further review actions are available.</p> : (
          <div className="row gap wrap">
            {options.map((t) => { const A = ACTIONS[t]; return <button key={t} className={`btn ${A.cls}`} onClick={() => setTarget(t)}><A.icon size={17} /> {A.label}</button>; })}
            {inSettlement && <button className="btn btn-primary" onClick={() => setSettle(true)}>{claim.status === "Approved" ? "Start settlement" : "Record settlement"}</button>}
          </div>
        )}
      </section>

      <div className="two-col">
        <div className="stack">
          <section className="panel">
            <h2>Claim and customer</h2>
            <dl className="kv">
              <dt>Customer</dt><dd>{claim.user.full_name}</dd>
              <dt>Email</dt><dd>{claim.user.email}</dd>
              <dt>Phone</dt><dd>{claim.user.phone || "-"}</dd>
              <dt>Incident date</dt><dd>{dateOnly(claim.incident_date)}</dd>
              <dt>Submitted</dt><dd>{dateOnly(claim.submitted_at)}</dd>
              <dt>Policy coverage</dt><dd>{money(claim.policy.coverage_amount)}</dd>
              <dt>Requested amount</dt><dd>{money(claim.requested_amount)}</dd>
              <dt>Approved amount</dt><dd>{money(claim.approved_amount)}</dd>
              <dt>Settlement date</dt><dd>{dateOnly(claim.settlement_date)}</dd>
              <dt>Transaction reference</dt><dd>{claim.settlement_reference || "-"}</dd>
            </dl>
            <h3>Incident description</h3><p className="pre">{claim.incident_description}</p>
          </section>

          <section className="panel">
            <h2>Documents</h2>
            <DocumentList documents={claim.documents} renderActions={(d) => <button className="btn btn-primary btn-sm" onClick={() => setVerifyDoc(d)}>Verify</button>} />
          </section>

          <section className="panel">
            <h2>Add a comment</h2>
            <p className="muted">Comments are saved in the claim history and shown to the customer.</p>
            <textarea rows={3} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} aria-label="Comment" />
            <div><button className="btn btn-ghost" onClick={addNote} disabled={noteBusy || !note.trim()}>{noteBusy ? "Saving..." : "Add comment"}</button></div>
          </section>
        </div>
        <aside className="panel"><h2>Claim history</h2><ClaimTimeline history={claim.history} /></aside>
      </div>

      {target && <StatusDialog claim={claim} target={target} onClose={() => setTarget(null)} onDone={done} />}
      {verifyDoc && <VerifyDialog doc={verifyDoc} onClose={() => setVerifyDoc(null)} onDone={done} />}
      {settle && <SettlementForm claim={claim} onClose={() => setSettle(false)} onSaved={done} />}
    </>
  );
}
