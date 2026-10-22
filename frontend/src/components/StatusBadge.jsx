import { STATUS_COLORS } from "../utils/format";

export default function StatusBadge({ status }) {
  const color = STATUS_COLORS[status] || "#64748b";
  return (
    <span className="badge" style={{ color, background: color + "1a", borderColor: color + "55" }}>
      <i style={{ background: color }} />{status}
    </span>
  );
}
