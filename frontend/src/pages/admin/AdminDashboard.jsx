import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AlertCircle, CheckCircle2, ClipboardList, FileText, Hourglass, Landmark, Users, Wallet, XCircle } from "lucide-react";
import api, { errorMessage } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import Spinner from "../../components/Spinner";
import StatCard from "../../components/StatCard";
import ClaimsTable from "../../components/ClaimsTable";
import EmptyState from "../../components/EmptyState";
import { STATUS_COLORS, money, monthLabel } from "../../utils/format";

export default function AdminDashboard() {
  const toast = useToast();
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/api/admin/dashboard").then((r) => setD(r.data)).catch((e) => toast.error(errorMessage(e))); }, []); // eslint-disable-line
  if (!d) return <Spinner />;

  const pie = d.status_distribution.filter((s) => s.count > 0);
  const monthly = d.monthly_claims.map((m) => ({ ...m, label: monthLabel(m.month) }));
  return (
    <>
      <div className="page-head"><div><h1>Administrator dashboard</h1><p className="muted">Live figures from the claims database.</p></div>
        <Link to="/admin/claims?status=Submitted" className="btn btn-primary">Review new claims</Link></div>
      <div className="stats">
        <StatCard icon={Users} label="Registered customers" value={d.total_customers} />
        <StatCard icon={FileText} label="Claims received" value={d.total_claims} />
        <StatCard icon={Hourglass} label="Awaiting review" value={d.awaiting_review} tone="purple" />
        <StatCard icon={AlertCircle} label="Documents required" value={d.documents_required} tone="amber" />
        <StatCard icon={CheckCircle2} label="Approved" value={d.approved} tone="green" />
        <StatCard icon={XCircle} label="Rejected" value={d.rejected} tone="red" />
        <StatCard icon={ClipboardList} label="Total requested" value={money(d.total_requested_amount)} />
        <StatCard icon={Landmark} label="Total approved" value={money(d.total_approved_amount)} tone="teal" />
        <StatCard icon={Wallet} label="Pending settlements" value={d.pending_settlements} tone="blue" />
      </div>

      <div className="two-col even">
        <section className="panel">
          <h2>Claims submitted per month</h2>
          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthly} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" fontSize={12} /><YAxis allowDecimals={false} fontSize={12} />
                <Tooltip /><Bar dataKey="claims" name="Claims" fill="#0f766e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="panel">
          <h2>Claim status distribution</h2>
          {pie.length === 0 ? <EmptyState title="No claims yet" text="The chart appears once claims are submitted." /> : (
            <div className="chart">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pie} dataKey="count" nameKey="status" innerRadius={55} outerRadius={95} paddingAngle={2}>
                    {pie.map((s) => <Cell key={s.status} fill={STATUS_COLORS[s.status]} />)}
                  </Pie>
                  <Tooltip /><Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>
      </div>

      <section className="panel">
        <h2>Recently updated claims</h2>
        {d.recent.length === 0 ? <EmptyState title="No claims received yet" /> : <ClaimsTable claims={d.recent} basePath="/admin/claims" showCustomer />}
      </section>
    </>
  );
}
