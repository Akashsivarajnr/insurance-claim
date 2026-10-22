import { ChevronLeft, ChevronRight } from "lucide-react";

export default function Pagination({ page, pages, total, pageSize, onChange }) {
  if (!total) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  return (
    <div className="pagination">
      <span className="muted">Showing {from}-{to} of {total}</span>
      <div className="row gap-sm">
        <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => onChange(page - 1)}><ChevronLeft size={16} /> Previous</button>
        <span className="muted">Page {page} of {pages}</span>
        <button className="btn btn-ghost btn-sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>Next <ChevronRight size={16} /></button>
      </div>
    </div>
  );
}
