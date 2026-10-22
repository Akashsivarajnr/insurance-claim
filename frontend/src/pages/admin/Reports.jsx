import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api, { errorMessage } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import Spinner from "../../components/Spinner";
import StatCard from "../../components/StatCard";
import { BarChart3, Clock, Landmark, ThumbsDown, ThumbsUp, Wallet } from "lucide-react";
import { money, monthLabel } from "../../utils/format";

export default function Reports() {
  const toast = useToast();
  const [r, setR] = useState(null);
  useEffect(() => { api.get("/api/admin/reports").then((x) => setR(x.data)).catch((e) => toast.error(errorMessage(e))); }, []); // eslint-disable-line
  if (!r) return <Spinner />;
  const monthly = r.monthly.map((m) => ({ ...m, label: monthLabel(m.month) }));
  return (
    <>
      <div className="page-head"><div><h1>Reports and analytics</h1><p className="muted">Calculated from all claims in the database.</p></div></div>
      <div className="stats">
        <StatCard icon={BarChart3} label="Total claims" value={r.total_claims} />
        <StatCard icon={ThumbsUp} label="Approval rate (decided)" value={`${r.approval_rate}%`} tone="green" />
        <StatCard icon={ThumbsDown} label="Rejection rate (decided)" value={`${r.rejection_rate}%`} tone="red" />
        <StatCard icon={Clock} label="Avg days to settle" value={r.average_days_to_settle ?? "-"} tone="purple" />
        <StatCard icon={Landmark} label="Amount settled" value={money(r.settled_amount)} tone="teal" />
        <StatCard icon={Wallet} label="Awaiting settlement" value={money(r.awaiting_settlement_amount)} tone="blue" />
      </div>

      <section className="panel">
        <h2>Requested and approved amounts by month</h2>
        <div className="chart">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={monthly} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" fontSize={12} />
              <YAxis fontSize={12} tickFormatter={(v) => (v >= 100000 ? `${v / 100000}L` : v)} />
              <Tooltip formatter={(v) => money(v)} /><Legend />
              <Bar dataKey="requested" name="Requested" fill="#0b2545" radius={[4, 4, 0, 0]} />
              <Bar dataKey="approved" name="Approved" fill="#14b8a6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <div className="two-col even">
        <section className="panel">
          <h2>Claims by type</h2>
          <div className="table-wrap"><table className="table">
            <thead><tr><th>Type</th><th>Claims</th><th>Requested</th><th>Approved</th></tr></thead>
            <tbody>{r.by_type.map((t) => <tr key={t.claim_type}><td className="strong">{t.claim_type}</td><td>{t.claims}</td><td>{money(t.requested)}</td><td>{money(t.approved)}</td></tr>)}</tbody>
          </table></div>
        </section>
        <section className="panel">
          <h2>Claims by status</h2>
          <div className="table-wrap"><table className="table">
            <thead><tr><th>Status</th><th>Claims</th></tr></thead>
            <tbody>{r.by_status.map((s) => <tr key={s.status}><td>{s.status}</td><td>{s.count}</td></tr>)}</tbody>
          </table></div>
        </section>
      </div>
    </>
  );
}
