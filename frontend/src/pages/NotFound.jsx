import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="container section center-text">
      <h1>Page not found</h1>
      <p className="muted">The page you are looking for does not exist or has moved.</p>
      <Link className="btn btn-primary" to="/">Back to home</Link>
    </div>
  );
}
