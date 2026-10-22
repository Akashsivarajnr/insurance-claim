import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { BarChart3, Bell, FilePlus2, FileText, Gauge, LogOut, Menu, Users, UserCircle, Wallet, X } from "lucide-react";
import Logo from "../components/Logo";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

const CUSTOMER_NAV = [
  { to: "/customer", label: "Dashboard", icon: Gauge, end: true },
  { to: "/customer/submit", label: "Submit a claim", icon: FilePlus2 },
  { to: "/customer/claims", label: "My claims", icon: FileText },
  { to: "/customer/notifications", label: "Notifications", icon: Bell, badge: true },
  { to: "/customer/profile", label: "Profile", icon: UserCircle },
];
const ADMIN_NAV = [
  { to: "/admin", label: "Dashboard", icon: Gauge, end: true },
  { to: "/admin/claims", label: "All claims", icon: FileText },
  { to: "/admin/settlements", label: "Settlements", icon: Wallet },
  { to: "/admin/customers", label: "Customers", icon: Users },
  { to: "/admin/reports", label: "Reports", icon: BarChart3 },
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const isAdmin = user.role === "admin";
  const nav = isAdmin ? ADMIN_NAV : CUSTOMER_NAV;

  useEffect(() => { setOpen(false); }, [location.pathname]);
  useEffect(() => {
    if (isAdmin) return;
    api.get("/api/notifications/unread-count").then((r) => setUnread(r.data.unread)).catch(() => {});
  }, [location.pathname, isAdmin]);

  return (
    <div className="shell">
      <aside className={open ? "sidebar open" : "sidebar"}>
        <div className="sidebar-top"><Logo to={isAdmin ? "/admin" : "/customer"} light /></div>
        <nav>
          {nav.map(({ to, label, icon: Icon, end, badge }) => (
            <NavLink key={to} to={to} end={end} className="side-link">
              <Icon size={18} /> <span>{label}</span>
              {badge && unread > 0 && <em className="count">{unread}</em>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="who"><strong>{user.full_name}</strong><small>{isAdmin ? "Administrator" : "Customer"}</small></div>
          <button className="side-link as-button" onClick={() => { logout(); navigate("/"); }}><LogOut size={18} /> <span>Log out</span></button>
        </div>
      </aside>
      {open && <div className="scrim" onClick={() => setOpen(false)} />}
      <div className="main">
        <header className="topbar">
          <button className="icon-btn menu-btn" aria-label="Open menu" onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button>
          <span className="topbar-title">{isAdmin ? "Administrator console" : "Customer portal"}</span>
        </header>
        <div className="content"><Outlet /></div>
      </div>
    </div>
  );
}
