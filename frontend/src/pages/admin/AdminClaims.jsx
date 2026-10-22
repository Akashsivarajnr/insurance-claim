import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
import api, { errorMessage } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import ClaimsTable from "../../components/ClaimsTable";
import EmptyState from "../../components/EmptyState";
import Pagination from "../../components/Pagination";
import Spinner from "../../components/Spinner";
import { CLAIM_TYPES, STATUSES } from "../../utils/format";

const PAGE_SIZE = 10;

export default function AdminClaims() {
  const toast = useToast();
  const [params] = useSearchParams();
  const [f, setF] = useState({ search: "", status: params.get("status") || "", claim_type: "", date_from: "", date_to: "" });
  const [applied, setApplied] = useState(f);
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);

  useEffect(() => {
    setData(null);
    const q = Object.fromEntries(Object.entries(applied).filter(([, v]) => v));
    api.get("/api/admin/claims", { params: { ...q, page, page_size: PAGE_SIZE } })
      .then((r) => setData(r.data)).catch((e) => { toast.error(errorMessage(e)); setData({ items: [], total: 0, page: 1, pages: 1 }); });
  }, [applied, page]); // eslint-disable-line

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const apply = (e) => { e?.preventDefault(); setPage(1); setApplied(f); };
  const clear = () => { const blank = { search: "", status: "", claim_type: "", date_from: "", date_to: "" }; setF(blank); setApplied(blank); setPage(1); };

  return (
    <>
      <div className="page-head"><div><h1>All claims</h1><p className="muted">Search, filter and open any claim.</p></div></div>
      <div className="panel">
        <form className="filters wrap" onSubmit={apply}>
          <div className="search grow"><Search size={16} /><input placeholder="Search by reference or customer name" value={f.search} onChange={set("search")} /></div>
          <select value={f.status} onChange={set("status")} aria-label="Status"><option value="">All statuses</option>{STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
          <select value={f.claim_type} onChange={set("claim_type")} aria-label="Claim type"><option value="">All types</option>{CLAIM_TYPES.map((s) => <option key={s}>{s}</option>)}</select>
          <label className="inline-field">From <input type="date" value={f.date_from} onChange={set("date_from")} /></label>
          <label className="inline-field">To <input type="date" value={f.date_to} onChange={set("date_to")} /></label>
          <button className="btn btn-primary">Apply</button>
          <button type="button" className="btn btn-ghost" onClick={clear}>Clear</button>
        </form>
        {!data ? <Spinner /> : data.items.length === 0 ? <EmptyState title="No claims match these filters" text="Change or clear the filters to see more." /> : (
          <>
            <ClaimsTable claims={data.items} basePath="/admin/claims" showCustomer />
            <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={PAGE_SIZE} onChange={setPage} />
          </>
        )}
      </div>
    </>
  );
}
