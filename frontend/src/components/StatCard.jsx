export default function StatCard({ icon: Icon, label, value, tone = "navy" }) {
  return (
    <div className="stat">
      <div className={`stat-icon tone-${tone}`}><Icon size={20} /></div>
      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}
