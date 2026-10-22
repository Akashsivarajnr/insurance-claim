import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import api, { errorMessage } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import EmptyState from "../../components/EmptyState";
import Pagination from "../../components/Pagination";
import Spinner from "../../components/Spinner";
import { dateOnly, money } from "../../utils/format";

const PAGE_SIZE = 10;

export default function Customers() {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);

  useEffect(() => {
    setData(null);
    api.get("/api/admin/customers", { params: { search: query || undefined, page, page_size: PAGE_SIZE } })
      .then((r) => setData(r.data)).catch((e) => { toast.error(errorMessage(e)); setData({ items: [], total: 0, page: 1, pages: 1 }); });
  }, [query, page]); // eslint-disable-line

  return (
    <>
      <div className="page-head"><div><h1>Customers</h1><p className="muted">Registered customer accounts.</p></div></div>
      <div className="panel">
        <form className="filters" onSubmit={(e) => { e.preventDefault(); setPage(1); setQuery(search.trim()); }}>
          <div className="search grow"><Search size={16} /><input placeholder="Search by name or email" value={search} onChange={(e) => setSearch(e.target.value)} /></div>
          <button className="btn btn-ghost">Search</button>
        </form>
        {!data ? <Spinner /> : data.items.length === 0 ? <EmptyState title="No customers found" /> : (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Joined</th><th>Claims</th><th>Total requested</th></tr></thead>
                <tbody>{data.items.map((c) => (
                  <tr key={c.id}><td className="strong">{c.full_name}</td><td>{c.email}</td><td>{c.phone || "-"}</td><td>{dateOnly(c.created_at)}</td><td>{c.claim_count}</td><td>{money(c.total_requested)}</td></tr>
                ))}</tbody>
              </table>
            </div>
            <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={PAGE_SIZE} onChange={setPage} />
          </>
        )}
      </div>
    </>
  );
}
