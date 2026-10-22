import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bell, CheckCheck } from "lucide-react";
import api, { errorMessage } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import EmptyState from "../../components/EmptyState";
import Spinner from "../../components/Spinner";
import { dateTime } from "../../utils/format";

export default function Notifications() {
  const toast = useToast();
  const [items, setItems] = useState(null);
  const load = () => api.get("/api/notifications").then((r) => setItems(r.data)).catch((e) => { toast.error(errorMessage(e)); setItems([]); });
  useEffect(() => { load(); }, []); // eslint-disable-line

  const markRead = async (n) => {
    if (n.is_read) return;
    try { await api.patch(`/api/notifications/${n.id}/read`); setItems((l) => l.map((x) => (x.id === n.id ? { ...x, is_read: true } : x))); }
    catch (e) { toast.error(errorMessage(e)); }
  };
  const markAll = async () => {
    try { await api.patch("/api/notifications/read-all"); setItems((l) => l.map((x) => ({ ...x, is_read: true }))); toast.success("All notifications marked as read."); }
    catch (e) { toast.error(errorMessage(e)); }
  };

  if (!items) return <Spinner />;
  const unread = items.filter((n) => !n.is_read).length;
  return (
    <>
      <div className="page-head"><div><h1>Notifications</h1><p className="muted">{unread} unread</p></div>
        <button className="btn btn-ghost" onClick={markAll} disabled={!unread}><CheckCheck size={18} /> Mark all as read</button></div>
      <div className="panel">
        {items.length === 0 ? <EmptyState title="No notifications yet" text="Updates about your claims will show up here." /> : (
          <ul className="notes">
            {items.map((n) => (
              <li key={n.id} className={n.is_read ? "" : "unread"}>
                <Bell size={18} />
                <div className="grow"><p>{n.message}</p><small className="muted">{dateTime(n.created_at)}</small>
                  {n.claim_id && <> <Link className="link" to={`/customer/claims/${n.claim_id}`} onClick={() => markRead(n)}>Open claim</Link></>}</div>
                {!n.is_read && <button className="btn btn-ghost btn-sm" onClick={() => markRead(n)}>Mark read</button>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
