import StatusBadge from "./StatusBadge";
import { dateTime } from "../utils/format";

export default function ClaimTimeline({ history }) {
  return (
    <ol className="timeline">
      {[...history].reverse().map((h) => (
        <li key={h.id}>
          <span className="dot" />
          <div className="row wrap gap-sm">
            {h.previous_status && h.previous_status !== h.new_status ? (
              <><StatusBadge status={h.previous_status} /><span className="muted">to</span></>
            ) : null}
            <StatusBadge status={h.new_status} />
            {h.previous_status === h.new_status && <span className="muted">comment added</span>}
          </div>
          {h.comment && <p className="timeline-comment">{h.comment}</p>}
          <small className="muted">{dateTime(h.changed_at)}{h.changed_by_name ? ` by ${h.changed_by_name}` : ""}</small>
        </li>
      ))}
    </ol>
  );
}
