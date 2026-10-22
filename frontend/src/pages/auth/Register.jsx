import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { errorMessage } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import Field from "../../components/Field";

export default function Register() {
  const { register } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", password: "", confirm: "" });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const validate = () => {
    const e = {};
    if (form.full_name.trim().length < 2) e.full_name = "Enter your full name.";
    if (!/^\S+@\S+\.\S+$/.test(form.email)) e.email = "Enter a valid email address.";
    if (form.phone && !/^[0-9+\-() ]{7,20}$/.test(form.phone)) e.phone = "Use 7-20 digits, spaces, +, - or brackets.";
    if (form.password.length < 8) e.password = "Use at least 8 characters.";
    else if (!/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) e.password = "Include at least one letter and one number.";
    if (form.confirm !== form.password) e.confirm = "Passwords do not match.";
    return e;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setBusy(true);
    try {
      await register({ full_name: form.full_name.trim(), email: form.email.trim(), phone: form.phone.trim() || null, password: form.password });
      toast.success("Account created. Welcome to ClaimFlow.");
      navigate("/customer", { replace: true });
    } catch (err) {
      setErrors({ form: errorMessage(err) });
    }
    setBusy(false);
  };

  return (
    <div className="auth-wrap">
      <form className="panel auth-card" onSubmit={submit} noValidate>
        <h1>Create your account</h1>
        <p className="muted">Customer accounts can submit and track claims.</p>
        {errors.form && <div className="alert alert-error" role="alert">{errors.form}</div>}
        <Field label="Full name" error={errors.full_name}><input autoComplete="name" value={form.full_name} onChange={set("full_name")} /></Field>
        <Field label="Email" error={errors.email}><input type="email" autoComplete="email" value={form.email} onChange={set("email")} /></Field>
        <Field label="Phone (optional)" error={errors.phone}><input type="tel" autoComplete="tel" value={form.phone} onChange={set("phone")} /></Field>
        <Field label="Password" error={errors.password} hint="At least 8 characters with letters and numbers"><input type="password" autoComplete="new-password" value={form.password} onChange={set("password")} /></Field>
        <Field label="Confirm password" error={errors.confirm}><input type="password" autoComplete="new-password" value={form.confirm} onChange={set("confirm")} /></Field>
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? "Creating account..." : "Create account"}</button>
        <p className="muted center-text">Already registered? <Link className="link" to="/login">Log in</Link></p>
      </form>
    </div>
  );
}
