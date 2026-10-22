import { Link } from "react-router-dom";

export default function About() {
  return (
    <div className="container section prose">
      <h1>About ClaimFlow</h1>
      <p>ClaimFlow is a full-stack web application built as a college project to show how insurance claim handling can be made faster and more transparent. Manual verification stages usually cause delays, data-entry errors and repeated phone calls asking "where is my claim?". ClaimFlow keeps submission, document checks, approval and settlement in one place.</p>

      <h2>Objectives</h2>
      <ul>
        <li>Let customers submit claims and documents online.</li>
        <li>Give administrators one place to review, verify, approve or reject claims.</li>
        <li>Keep a permanent history of every status change and comment.</li>
        <li>Show customers their claim status, approved amount and settlement details.</li>
      </ul>

      <h2>Technology</h2>
      <p>React with Vite and React Router on the front end; Python FastAPI, SQLAlchemy and SQLite on the back end; JWT authentication with hashed passwords and role-based access control.</p>

      <h2>Important notice</h2>
      <div className="alert alert-warn">This is a demonstration system. It is not connected to any real insurance company, bank or payment gateway, and its document storage is not designed for real insurance documents, which need stronger production-grade storage, encryption and privacy controls.</div>
      <p><Link className="btn btn-primary" to="/register">Create a customer account</Link></p>
    </div>
  );
}
