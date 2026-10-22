import { useState } from "react";
import api, { errorMessage } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import Field from "../../components/Field";
import { dateOnly } from "../../utils/format";

export default function Profile() {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const [form, setForm] = useState({ full_name: user.full_name, phone: user.phone || "" });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    const errs = {};
    if (form.full_name.trim().length < 2) errs.full_name = "Enter your full name.";
    if (form.phone && !/^[0-9+\-() ]{7,20}$/.test(form.phone)) errs.phone = "Use 7-20 digits, spaces, +, - or brackets.";
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setBusy(true);
    try {
      const r = await api.patch("/api/auth/me", { full_name: form.full_name.trim(), phone: form.phone.trim() || null });
      setUser(r.data);
      toast.success("Profile updated.");
    } catch (err) { toast.error(errorMessage(err)); }
    setBusy(false);
  };

  return (
    <>
      <div className="page-head"><div><h1>Your profile</h1><p className="muted">Member since {dateOnly(user.created_at)}</p></div></div>
      <form className="panel narrow" onSubmit={submit} noValidate>
        <Field label="Full name" error={errors.full_name}><input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
        <Field label="Email" hint="Email cannot be changed"><input value={user.email} readOnly /></Field>
        <Field label="Phone" error={errors.phone}><input type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
        <button className="btn btn-primary" disabled={busy}>{busy ? "Saving..." : "Save changes"}</button>
      </form>
    </>
  );
}
