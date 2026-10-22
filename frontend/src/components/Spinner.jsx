export default function Spinner({ full = false, label = "Loading..." }) {
  return (
    <div className={full ? "spinner-wrap full" : "spinner-wrap"} role="status">
      <span className="spinner" />
      <span className="muted">{label}</span>
    </div>
  );
}
