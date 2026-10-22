import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import EmptyState from "../../components/EmptyState";
import Pagination from "../../components/Pagination";
import Spinner from "../../components/Spinner";
import StatusBadge from "../../components/StatusBadge";
import SettlementForm from "../../components/SettlementForm";
import { dateOnly, money } from "../../utils/format";

const PAGE_SIZE = 10;

export default function Settlements() {
  const toast = useToast();
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [active, setActive] = useState(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    setData(null);
    api.get("/api/admin/claims", { params: { settlement: true, status: status || undefined, page, page_size: PAGE_SIZE } })
      .then((r) => setData(r.data)).catch((e) => { toast.error(errorMessage(e)); setData({ items: [], total: 0, page: 1, pages: 1 }); });
  }, [status, page, tick]); // eslint-disable-line

  return (
    <>
      <div className="page-head"><div><h1>Settlement management</h1><p className="muted">Approved claims waiting for payment or already settled.</p></div></div>
      <div className="panel">
        <div className="filters">
          <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} aria-label="Settlement status">
            <option value="">All settlement stages</option><option>Approved</option><option>Settlement Pending</option><option>Settled</option>
          </select>
        </div>
        {!data ? <Spinner /> : data.items.length === 0 ? <EmptyState title="Nothing to settle" text="Approved claims will appear here." /> : (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Reference</th><th>Customer</th><th>Approved amount</th><th>Stage</th><th>Settlement date</th><th>Action</th></tr></thead>
                <tbody>
                  {data.items.map((c) => (
                    <tr key={c.id}>
                      <td><Link className="link strong" to={`/admin/claims/${c.id}`}>{c.claim_reference}</Link></td>
                      <td>{c.customer_name}</td><td>{money(c.approved_amount)}</td><td><StatusBadge status={c.status} /></td><td>{dateOnly(c.settlement_date)}</td>
                      <td>{c.status === "Settled" ? <Link className="btn btn-ghost btn-sm" to={`/admin/claims/${c.id}`}>View</Link>
                        : <button className="btn btn-primary btn-sm" onClick={() => setActive(c)}>{c.status === "Approved" ? "Start settlement" : "Record settlement"}</button>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={PAGE_SIZE} onChange={setPage} />
          </>
        )}
      </div>
      {active && <SettlementForm claim={active} onClose={() => setActive(null)} onSaved={() => { setActive(null); setTick((t) => t + 1); }} />}
    </>
  );
}
