import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import api, { errorMessage } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import Field from "../../components/Field";
import Spinner from "../../components/Spinner";
import FileUploader from "../../components/FileUploader";
import { money, todayISO } from "../../utils/format";

export default function SubmitClaim() {
  const toast = useToast();
  const navigate = useNavigate();
  const [policies, setPolicies] = useState(null);
  const [form, setForm] = useState({ policy_number: "", incident_date: "", incident_description: "", requested_amount: "" });
  const [files, setFiles] = useState([]);
  const [docType, setDocType] = useState("Supporting Document");
  const [fileError, setFileError] = useState("");
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);

  useEffect(() => {
    api.get("/api/policies").then((r) => setPolicies(r.data)).catch((e) => toast.error(errorMessage(e)));
  }, []); // eslint-disable-line

  if (!policies) return <Spinner />;
  const policy = policies.find((p) => p.policy_number === form.policy_number);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const validate = () => {
    const e = {};
    if (!policy) e.policy_number = "Choose the policy you are claiming under.";
    if (!form.incident_date) e.incident_date = "Enter the date of the incident.";
    else if (form.incident_date > todayISO()) e.incident_date = "The incident date cannot be in the future.";
    if (form.incident_description.trim().length < 10) e.incident_description = "Describe what happened (at least 10 characters).";
    const amt = Number(form.requested_amount);
    if (!form.requested_amount || !(amt > 0)) e.requested_amount = "Enter an amount greater than zero.";
    else if (policy && amt > policy.coverage_amount) e.requested_amount = `This policy covers up to ${money(policy.coverage_amount)}.`;
    return e;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setBusy(true);
    let claim;
    try {
      claim = (await api.post("/api/claims", {
        policy_number: policy.policy_number, claim_type: policy.policy_type, incident_date: form.incident_date,
        incident_description: form.incident_description, requested_amount: Number(form.requested_amount),
      })).data;
    } catch (err) {
      toast.error(errorMessage(err));
      setBusy(false);
      return;
    }
    let uploadFailed = false;
    if (files.length) {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f));
      fd.append("document_type", docType);
      try { await api.post(`/api/claims/${claim.id}/documents`, fd); }
      catch (err) { uploadFailed = true; toast.error(`Claim created, but documents were not uploaded: ${errorMessage(err)}`); }
    }
    setBusy(false);
    if (uploadFailed) navigate(`/customer/claims/${claim.id}`);
    else { toast.success("Claim submitted successfully."); setDone(claim); }
  };

  if (done) {
    return (
      <div className="panel center-text confirm">
        <CheckCircle2 size={44} className="accent" />
        <h1>Claim submitted</h1>
        <p className="muted">Keep this reference number to follow your claim.</p>
        <div className="refbox">{done.claim_reference}</div>
        <div className="row gap center wrap">
          <Link className="btn btn-primary" to={`/customer/claims/${done.id}`}>Track this claim</Link>
          <Link className="btn btn-ghost" to="/customer">Back to dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="page-head"><div><h1>Submit a claim</h1><p className="muted">A reference number is created as soon as you submit.</p></div></div>
      <form className="panel form-grid" onSubmit={submit} noValidate>
        <Field label="Policy" error={errors.policy_number}>
          <select value={form.policy_number} onChange={set("policy_number")}>
            <option value="">Select a policy</option>
            {policies.map((p) => <option key={p.id} value={p.policy_number}>{p.policy_number} - {p.policy_name} ({p.policy_type})</option>)}
          </select>
        </Field>
        <Field label="Claim type" hint="Set by the policy you choose"><input value={policy?.policy_type || ""} readOnly placeholder="-" /></Field>
        {policy && <div className="alert alert-info span-2">{policy.description} Coverage up to <strong>{money(policy.coverage_amount)}</strong>.</div>}
        <Field label="Incident date" error={errors.incident_date}><input type="date" max={todayISO()} value={form.incident_date} onChange={set("incident_date")} /></Field>
        <Field label="Requested amount (INR)" error={errors.requested_amount}><input type="number" min="1" step="0.01" value={form.requested_amount} onChange={set("requested_amount")} /></Field>
        <div className="span-2"><Field label="What happened?" error={errors.incident_description}><textarea rows={5} maxLength={3000} value={form.incident_description} onChange={set("incident_description")} /></Field></div>
        <div className="span-2">
          <h3>Supporting documents</h3>
          <FileUploader files={files} onChange={setFiles} docType={docType} onDocType={setDocType} error={fileError} onError={setFileError} />
        </div>
        <div className="span-2 row gap"><button className="btn btn-primary" disabled={busy}>{busy ? "Submitting..." : "Submit claim"}</button><Link className="btn btn-ghost" to="/customer">Cancel</Link></div>
      </form>
    </>
  );
}
