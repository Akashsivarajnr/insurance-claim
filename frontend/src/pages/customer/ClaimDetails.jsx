import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, MessageSquare } from "lucide-react";
import api, { errorMessage } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import Spinner from "../../components/Spinner";
import StatusBadge from "../../components/StatusBadge";
import DocumentList from "../../components/DocumentList";
import ClaimTimeline from "../../components/ClaimTimeline";
import FileUploader from "../../components/FileUploader";
import { dateOnly, money } from "../../utils/format";

const OPEN = ["Submitted", "Under Review", "Documents Required"];

export default function ClaimDetails() {
  const { id } = useParams();
  const toast = useToast();
  const [claim, setClaim] = useState(null);
  const [missing, setMissing] = useState(false);
  const [files, setFiles] = useState([]);
  const [docType, setDocType] = useState("Supporting Document");
  const [fileError, setFileError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.get(`/api/claims/${id}`).then((r) => setClaim(r.data)).catch((e) => {
      if (e.response?.status === 404) setMissing(true); else toast.error(errorMessage(e));
    });
  }, [id]); // eslint-disable-line
  useEffect(load, [load]);

  const upload = async () => {
    if (!files.length) return setFileError("Choose at least one file.");
    setBusy(true);
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    fd.append("document_type", docType);
    try {
      await api.post(`/api/claims/${id}/documents`, fd);
      toast.success("Documents uploaded.");
      setFiles([]);
      load();
    } catch (e) { setFileError(errorMessage(e)); }
    setBusy(false);
  };

  if (missing) return <div className="panel center-text"><h1>Claim not found</h1><p className="muted">It may not exist, or it belongs to another account.</p><Link className="btn btn-primary" to="/customer/claims">Back to my claims</Link></div>;
  if (!claim) return <Spinner />;

  return (
    <>
      <Link to="/customer/claims" className="back"><ArrowLeft size={16} /> My claims</Link>
      <div className="page-head">
        <div><h1>{claim.claim_reference}</h1><p className="muted">{claim.claim_type} claim under {claim.policy_name} ({claim.policy_number})</p></div>
        <StatusBadge status={claim.status} />
      </div>

      {claim.status === "Documents Required" && (
        <div className="alert alert-warn"><strong>Action needed:</strong> the reviewer needs more documents. {claim.admin_comments}</div>
      )}

      <div className="two-col">
        <div className="stack">
          <section className="panel">
            <h2>Claim details</h2>
            <dl className="kv">
              <dt>Incident date</dt><dd>{dateOnly(claim.incident_date)}</dd>
              <dt>Submitted</dt><dd>{dateOnly(claim.submitted_at)}</dd>
              <dt>Requested amount</dt><dd>{money(claim.requested_amount)}</dd>
              <dt>Approved amount</dt><dd>{money(claim.approved_amount)}</dd>
            </dl>
            <h3>Description</h3><p className="pre">{claim.incident_description}</p>
          </section>

          {claim.approved_amount !== null && !["Rejected"].includes(claim.status) && (
            <section className="panel">
              <h2>Settlement</h2>
              <dl className="kv">
                <dt>Settlement status</dt><dd><StatusBadge status={claim.status} /></dd>
                <dt>Settlement date</dt><dd>{dateOnly(claim.settlement_date)}</dd>
                <dt>Transaction reference</dt><dd>{claim.settlement_reference || "-"}</dd>
              </dl>
              {claim.status === "Approved" && <p className="muted">Your claim is approved. Settlement will start soon.</p>}
            </section>
          )}

          {claim.admin_comments && claim.status !== "Documents Required" && (
            <section className="panel"><h2><MessageSquare size={18} /> Reviewer comments</h2><p className="pre">{claim.admin_comments}</p></section>
          )}

          <section className="panel">
            <h2>Documents</h2>
            <DocumentList documents={claim.documents} />
            {OPEN.includes(claim.status) && (
              <div className="upload-block">
                <h3>{claim.status === "Documents Required" ? "Upload the requested documents" : "Add more documents"}</h3>
                <FileUploader files={files} onChange={setFiles} docType={docType} onDocType={setDocType} error={fileError} onError={setFileError} />
                <button className="btn btn-primary" onClick={upload} disabled={busy || !files.length}>{busy ? "Uploading..." : "Upload documents"}</button>
              </div>
            )}
          </section>
        </div>

        <aside className="panel"><h2>Claim history</h2><ClaimTimeline history={claim.history} /></aside>
      </div>
    </>
  );
}
