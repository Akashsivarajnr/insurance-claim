import { Link } from "react-router-dom";
import { CheckCircle2, FileSearch, FileUp, ShieldCheck, Wallet } from "lucide-react";
import StatusBadge from "../components/StatusBadge";

const SAMPLE = [
  { status: "Submitted", note: "Claim received with 3 documents", when: "Mon 09:12" },
  { status: "Documents Required", note: "Please upload the final hospital bill", when: "Mon 15:40" },
  { status: "Under Review", note: "Bill received, review resumed", when: "Tue 10:05" },
  { status: "Approved", note: "Approved for Rs 18,500", when: "Wed 11:30" },
  { status: "Settled", note: "Paid, reference TXN-0001", when: "Fri 16:00" },
];

export default function Landing() {
  return (
    <>
      <section className="hero">
        <div className="container hero-grid">
          <div>
            <h1>Know where your insurance claim stands, at every step.</h1>
            <p className="lead">Submit a claim with your documents, get a reference number straight away, and follow each review decision until the payment is settled.</p>
            <div className="row gap wrap">
              <Link to="/register" className="btn btn-primary btn-lg">Submit a claim</Link>
              <Link to="/login" className="btn btn-ghost btn-lg">Log in</Link>
            </div>
          </div>
          <div className="sample" aria-label="Example of a claim timeline">
            <div className="sample-head"><strong>CF-2026-A1B2C3</strong><small className="muted">Example timeline</small></div>
            <ol className="timeline">
              {SAMPLE.map((s) => (
                <li key={s.status}><span className="dot" /><StatusBadge status={s.status} /><p className="timeline-comment">{s.note}</p><small className="muted">{s.when}</small></li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      <section className="container section">
        <h2>What you can do with ClaimFlow</h2>
        <div className="grid-3">
          <div className="panel"><FileUp className="accent" /><h3>Upload evidence once</h3><p className="muted">Attach PDF, JPG or PNG files to a claim. If a reviewer asks for more, add it to the same claim.</p></div>
          <div className="panel"><FileSearch className="accent" /><h3>Clear review decisions</h3><p className="muted">Each document is marked verified or flagged, and every status change comes with the reviewer's comment.</p></div>
          <div className="panel"><Wallet className="accent" /><h3>Settlement tracking</h3><p className="muted">See the approved amount, the settlement date and the transaction reference once a claim is paid.</p></div>
        </div>
      </section>

      <section className="band">
        <div className="container">
          <h2>How a claim moves through the system</h2>
          <ol className="steps">
            <li><strong>Register</strong><span>Create a customer account.</span></li>
            <li><strong>Submit</strong><span>Enter policy and incident details, then upload documents.</span></li>
            <li><strong>Review</strong><span>An administrator verifies documents or asks for more.</span></li>
            <li><strong>Decision</strong><span>The claim is approved with an amount, or rejected with a reason.</span></li>
            <li><strong>Settlement</strong><span>Approved claims move to Settlement Pending, then Settled.</span></li>
          </ol>
        </div>
      </section>

      <section className="container section row gap center-y wrap">
        <ShieldCheck className="accent" size={28} />
        <p className="muted grow">Passwords are hashed, sessions expire, and documents can only be opened by the customer who uploaded them and by administrators.</p>
        <Link to="/about" className="btn btn-ghost">About the system <CheckCircle2 size={16} /></Link>
      </section>
    </>
  );
}
