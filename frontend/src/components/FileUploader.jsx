import { useRef } from "react";
import { UploadCloud, X } from "lucide-react";
import { DOC_TYPES, fileSize } from "../utils/format";

export const MAX_MB = 5;
const OK_EXT = [".pdf", ".jpg", ".jpeg", ".png"];

/** Returns an error string for an unsuitable file, otherwise null. (The server re-checks everything.) */
export function checkFile(file) {
  const name = file.name.toLowerCase();
  if (!OK_EXT.some((e) => name.endsWith(e))) return `${file.name}: only PDF, JPG and PNG files are allowed.`;
  if (file.size > MAX_MB * 1024 * 1024) return `${file.name}: larger than ${MAX_MB} MB.`;
  if (file.size === 0) return `${file.name}: the file is empty.`;
  return null;
}

export default function FileUploader({ files, onChange, docType, onDocType, error, onError }) {
  const input = useRef(null);
  const add = (list) => {
    const picked = Array.from(list);
    for (const f of picked) {
      const problem = checkFile(f);
      if (problem) { onError(problem); return; }
    }
    onError("");
    onChange([...files, ...picked].slice(0, 10));
    if (input.current) input.current.value = "";
  };
  return (
    <div className="uploader">
      <label className="field">
        <span className="field-label">Document type</span>
        <select value={docType} onChange={(e) => onDocType(e.target.value)}>{DOC_TYPES.map((t) => <option key={t}>{t}</option>)}</select>
      </label>
      <div className="dropzone" onClick={() => input.current?.click()} onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); add(e.dataTransfer.files); }} role="button" tabIndex={0}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}>
        <UploadCloud size={26} />
        <strong>Choose files or drop them here</strong>
        <small className="muted">PDF, JPG or PNG, up to {MAX_MB} MB each (max 10 files)</small>
        <input ref={input} type="file" multiple accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" hidden onChange={(e) => add(e.target.files)} />
      </div>
      {error && <div className="field-error" role="alert">{error}</div>}
      {files.length > 0 && (
        <ul className="chosen">
          {files.map((f, i) => (
            <li key={i}><span>{f.name}</span><small className="muted">{fileSize(f.size)}</small>
              <button type="button" className="icon-btn" aria-label={`Remove ${f.name}`} onClick={() => onChange(files.filter((_, j) => j !== i))}><X size={15} /></button></li>
          ))}
        </ul>
      )}
    </div>
  );
}
