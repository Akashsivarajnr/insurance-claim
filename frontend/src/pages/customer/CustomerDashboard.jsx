import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Clock, FileText, FilePlus2, Landmark, XCircle } from "lucide-react";
import api, { errorMessage } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import Spinner from "../../components/Spinner";
import StatCard from "../../components/StatCard";
import ClaimsTable from "../../components/ClaimsTable";
import EmptyState from "../../components/EmptyState";
import { money } from "../../utils/format";

export default function CustomerDashboard() {
  const { user } = useAuth();
  const toast = useToast();
  const [stats, setStats] = useState(null);
  const [policies, setPolicies] = useState([]);

  useEffect(() => {
    Promise.all([api.get("/api/claims/my/stats"), api.get("/api/policies")])
      .then(([s, p]) => { setStats(s.data); setPolicies(p.data); })
      .catch((e) => toast.error(errorMessage(e)));
  }, []); // eslint-disable-line

  if (!stats) return <Spinner />;
  return (
    <>
      <div className="page-head">
        <div><h1>Hello, {user.full_name.split(" ")[0]}</h1><p className="muted">Here is where your claims stand.</p></div>
        <Link to="/customer/submit" className="btn btn-primary"><FilePlus2 size={18} /> Submit a claim</Link>
      </div>

      {stats.documents_required > 0 && (
        <div className="alert alert-warn">{stats.documents_required} of your claims need additional documents. <Link className="link" to="/customer/claims?status=Documents Required">Review them</Link></div>
      )}

      <div className="stats">
        <StatCard icon={FileText} label="Total claims" value={stats.total_claims} />
        <StatCard icon={Clock} label="In review" value={stats.under_review} tone="purple" />
        <StatCard icon={CheckCircle2} label="Approved" value={stats.approved} tone="green" />
        <StatCard icon={XCircle} label="Rejected" value={stats.rejected} tone="red" />
        <StatCard icon={Landmark} label="Settled" value={stats.settled} tone="teal" />
      </div>

      <section className="panel">
        <h2>Recent claim activity</h2>
        {stats.recent.length === 0 ? (
          <EmptyState title="No claims yet" text="When you submit a claim it will appear here." action={<Link to="/customer/submit" className="btn btn-primary">Submit your first claim</Link>} />
        ) : <ClaimsTable claims={stats.recent} basePath="/customer/claims" />}
      </section>

      <section>
        <h2>Insurance policy categories</h2>
        <div className="grid-3">
          {policies.map((p) => (
            <div className="panel policy" key={p.id}>
              <div className="row between"><span className="pill badge-muted">{p.policy_type}</span><small className="muted">{p.policy_number}</small></div>
              <h3>{p.policy_name}</h3>
              <p className="muted">{p.description}</p>
              <dl className="kv"><dt>Coverage</dt><dd>{money(p.coverage_amount)}</dd><dt>Premium / year</dt><dd>{money(p.premium_amount)}</dd></dl>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
