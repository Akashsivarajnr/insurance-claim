import { Link } from "react-router-dom";

export default function Logo({ to = "/", light = false }) {
  return (
    <Link to={to} className={light ? "logo logo-light" : "logo"} aria-label="ClaimFlow home">
      <span className="logo-mark" aria-hidden="true">
        <svg viewBox="0 0 32 32" width="28" height="28"><rect width="32" height="32" rx="7" fill="currentColor" opacity=".12" /><path d="M8 17l5 5 11-12" fill="none" stroke="#14B8A6" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </span>
      <span>Claim<b>Flow</b></span>
    </Link>
  );
}
