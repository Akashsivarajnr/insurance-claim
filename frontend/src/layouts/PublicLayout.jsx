import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { Menu, X } from "lucide-react";
import Logo from "../components/Logo";
import { useAuth } from "../context/AuthContext";

export default function PublicLayout() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  return (
    <div className="public">
      <header className="navbar">
        <div className="container navbar-inner">
          <Logo />
          <button className="icon-btn nav-toggle" aria-label="Menu" onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button>
          <nav className={open ? "nav-links open" : "nav-links"}>
            <NavLink to="/" end onClick={close}>Home</NavLink>
            <NavLink to="/about" onClick={close}>About</NavLink>
            {user ? (
              <Link className="btn btn-primary btn-sm" to={user.role === "admin" ? "/admin" : "/customer"} onClick={close}>Go to dashboard</Link>
            ) : (
              <>
                <NavLink to="/login" onClick={close}>Log in</NavLink>
                <Link className="btn btn-primary btn-sm" to="/register" onClick={close}>Create account</Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main><Outlet /></main>
      <footer className="footer">
        <div className="container">
          <span>ClaimFlow - college project demonstration. Not connected to any real insurer, bank or payment service.</span>
        </div>
      </footer>
    </div>
  );
}
