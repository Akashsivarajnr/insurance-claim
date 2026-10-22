import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { FilePlus2, Search } from "lucide-react";
import api, { errorMessage } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import ClaimsTable from "../../components/ClaimsTable";
import EmptyState from "../../components/EmptyState";
import Pagination from "../../components/Pagination";
import Spinner from "../../components/Spinner";
import { STATUSES } from "../../utils/format";

const PAGE_SIZE = 8;

export default function MyClaims() {
  const toast = useToast();
  const [params] = useSearchParams();
  const [status, setStatus] = useState(params.get("status") || "");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);

  useEffect(() => {
    setData(null);
    api.get("/api/claims/my", { params: { page, page_size: PAGE_SIZE, status: status || undefined, search: query || undefined } })
      .then((r) => setData(r.data)).catch((e) => { toast.error(errorMessage(e)); setData({ items: [], total: 0, page: 1, pages: 1 }); });
  }, [page, status, query]); // eslint-disable-line

  return (
    <>
      <div className="page-head"><div><h1>My claims</h1></div><Link to="/customer/submit" className="btn btn-primary"><FilePlus2 size={18} /> Submit a claim</Link></div>
      <div className="panel">
        <form className="filters" onSubmit={(e) => { e.preventDefault(); setPage(1); setQuery(search.trim()); }}>
          <div className="search"><Search size={16} /><input placeholder="Search by reference number" value={search} onChange={(e) => setSearch(e.target.value)} /></div>
          <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} aria-label="Filter by status">
            <option value="">All statuses</option>{STATUSES.map((s) => <option key={s}>{s}</option>)}
          </select>
          <button className="btn btn-ghost">Search</button>
        </form>
        {!data ? <Spinner /> : data.items.length === 0 ? (
          <EmptyState title="No claims found" text={status || query ? "Try a different filter." : "Submit a claim to get started."} />
        ) : (
          <>
            <ClaimsTable claims={data.items} basePath="/customer/claims" />
            <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={PAGE_SIZE} onChange={setPage} />
          </>
        )}
      </div>
    </>
  );
}
