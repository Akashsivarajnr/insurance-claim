import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";
import { dateOnly, money } from "../utils/format";

export default function ClaimsTable({ claims, basePath, showCustomer = false }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Reference</th>
            {showCustomer && <th>Customer</th>}
            <th>Type</th>
            <th>Requested</th>
            <th>Approved</th>
            <th>Status</th>
            <th>Submitted</th>
            <th><span className="sr-only">Open</span></th>
          </tr>
        </thead>
        <tbody>
          {claims.map((c) => (
            <tr key={c.id}>
              <td><Link className="link strong" to={`${basePath}/${c.id}`}>{c.claim_reference}</Link></td>
              {showCustomer && <td>{c.customer_name}</td>}
              <td>{c.claim_type}</td>
              <td>{money(c.requested_amount)}</td>
              <td>{money(c.approved_amount)}</td>
              <td><StatusBadge status={c.status} /></td>
              <td>{dateOnly(c.submitted_at)}</td>
              <td><Link className="btn btn-ghost btn-sm" to={`${basePath}/${c.id}`}>View</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
