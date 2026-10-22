export const STATUSES = ["Submitted", "Under Review", "Documents Required", "Approved", "Rejected", "Settlement Pending", "Settled"];
export const CLAIM_TYPES = ["Health", "Motor", "Home", "Travel", "Life"];
export const DOC_TYPES = ["Identity Proof", "Policy Document", "Medical Report", "Bill / Invoice", "Police / FIR Report", "Photograph", "Supporting Document"];

export const STATUS_COLORS = {
  Submitted: "#3b82f6",
  "Under Review": "#8b5cf6",
  "Documents Required": "#f59e0b",
  Approved: "#10b981",
  Rejected: "#ef4444",
  "Settlement Pending": "#0ea5e9",
  Settled: "#047857",
};

export const money = (n) =>
  n === null || n === undefined ? "-" : new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

export const dateOnly = (d) => (d ? new Date(d.length === 10 ? d + "T00:00:00" : d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "-");
export const dateTime = (d) => (d ? new Date(d).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "-");
export const fileSize = (b) => (b < 1024 * 1024 ? `${Math.max(1, Math.round(b / 1024))} KB` : `${(b / 1024 / 1024).toFixed(1)} MB`);
export const monthLabel = (ym) => new Date(ym + "-01T00:00:00").toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
export const todayISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
