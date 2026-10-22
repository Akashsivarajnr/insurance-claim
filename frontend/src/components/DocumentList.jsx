import { useState } from "react";
import { Download, FileText, ImageIcon } from "lucide-react";
import { downloadDocument, errorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import { dateTime, fileSize } from "../utils/format";

const VERIFY_STYLE = { Verified: "badge-ok", "Needs Information": "badge-warn", Pending: "badge-muted" };

export default function DocumentList({ documents, renderActions }) {
  const toast = useToast();
  const [busy, setBusy] = useState(null);

  const download = async (doc) => {
    setBusy(doc.id);
    try { await downloadDocument(doc); } catch (e) { toast.error(errorMessage(e, "Could not download the document.")); }
    setBusy(null);
  };

  if (!documents.length) return <p className="muted">No documents uploaded yet.</p>;
  return (
    <ul className="doc-list">
      {documents.map((d) => (
        <li key={d.id}>
          <div className="doc-icon">{d.content_type === "application/pdf" ? <FileText size={20} /> : <ImageIcon size={20} />}</div>
          <div className="doc-main">
            <strong className="doc-name">{d.original_filename}</strong>
            <small className="muted">{d.document_type} - {fileSize(d.file_size)} - uploaded {dateTime(d.uploaded_at)}</small>
            <div><span className={`pill ${VERIFY_STYLE[d.verification_status]}`}>{d.verification_status}</span></div>
            {d.admin_comment && <small className="doc-note">Reviewer note: {d.admin_comment}</small>}
          </div>
          <div className="row gap-sm">
            <button className="btn btn-ghost btn-sm" onClick={() => download(d)} disabled={busy === d.id}><Download size={15} /> {busy === d.id ? "..." : "Download"}</button>
            {renderActions && renderActions(d)}
          </div>
        </li>
      ))}
    </ul>
  );
}
