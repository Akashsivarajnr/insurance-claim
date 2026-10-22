import { Inbox } from "lucide-react";

export default function EmptyState({ title, text, action }) {
  return (
    <div className="empty">
      <Inbox size={36} />
      <h3>{title}</h3>
      {text && <p className="muted">{text}</p>}
      {action}
    </div>
  );
}
