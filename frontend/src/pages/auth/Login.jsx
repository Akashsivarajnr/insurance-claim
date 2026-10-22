import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { errorMessage } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import Field from "../../components/Field";

export default function Login() {
  const { login } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    const errs = {};
    if (!/^\S+@\S+\.\S+$/.test(form.email)) errs.email = "Enter a valid email address.";
    if (!form.password) errs.password = "Enter your password.";
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setBusy(true);
    try {
      const user = await login(form.email.trim(), form.password);
      toast.success(`Welcome back, ${user.full_name.split(" ")[0]}.`);
      const from = location.state?.from?.pathname;
      const home = user.role === "admin" ? "/admin" : "/customer";
      navigate(from && from.startsWith(home) ? from : home, { replace: true });
    } catch (err) {
      setErrors({ form: errorMessage(err) });
    }
    setBusy(false);
  };

  return (
    <div className="auth-wrap">
      <form className="panel auth-card" onSubmit={submit} noValidate>
        <h1>Log in</h1>
        <p className="muted">Use your customer or administrator account.</p>
        {errors.form && <div className="alert alert-error" role="alert">{errors.form}</div>}
        <Field label="Email" error={errors.email}><input type="email" autoComplete="email" value={form.email} onChange={set("email")} /></Field>
        <Field label="Password" error={errors.password}><input type="password" autoComplete="current-password" value={form.password} onChange={set("password")} /></Field>
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? "Signing in..." : "Log in"}</button>
        <p className="muted center-text">New to ClaimFlow? <Link className="link" to="/register">Create an account</Link></p>
      </form>
    </div>
  );
}
