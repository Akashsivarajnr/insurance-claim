import { useState } from "react";
import api, { errorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import Field from "./Field";
import Modal from "./Modal";
import { money, todayISO } from "../utils/format";

/** Modal used by admins to move an approved claim through settlement. */
export default function SettlementForm({ claim, onClose, onSaved }) {
  const toast = useToast();
  const next = claim.status === "Approved" ? "Settlement Pending" : "Settled";
  const [date, setDate] = useState(todayISO());
  const [ref, setRef] = useState("");
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError("");
    if (next === "Settled" && (!date || !ref.trim())) return setError("Enter the settlement date and transaction reference.");
    setBusy(true);
    try {
      const body = { status: next, comment: comment || null };
      if (next === "Settled") { body.settlement_date = date; body.settlement_reference = ref; }
      await api.patch(`/api/admin/claims/${claim.id}/settlement`, body);
      toast.success(next === "Settled" ? "Claim marked as settled." : "Claim moved to Settlement Pending.");
      onSaved();
    } catch (e) { setError(errorMessage(e)); }
    setBusy(false);
  };

  return (
    <Modal title={`${next === "Settled" ? "Record settlement" : "Start settlement"} - ${claim.claim_reference}`} onClose={onClose}
      footer={<><button className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-primary" onClick={submit} disabled={busy}>{busy ? "Saving..." : next === "Settled" ? "Mark as settled" : "Move to Settlement Pending"}</button></>}>
      <p className="muted">Approved amount: <strong>{money(claim.approved_amount)}</strong></p>
      {error && <div className="alert alert-error">{error}</div>}
      {next === "Settled" ? (
        <>
          <Field label="Settlement date"><input type="date" max={todayISO()} value={date} onChange={(e) => setDate(e.target.value)} /></Field>
          <Field label="Transaction reference" hint="Reference from your payment record, for example TXN-20250201-001"><input value={ref} maxLength={80} onChange={(e) => setRef(e.target.value)} /></Field>
        </>
      ) : <p>This tells the customer that payment is being prepared.</p>}
      <Field label="Comment (optional)"><textarea rows={2} maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} /></Field>
    </Modal>
  );
}
