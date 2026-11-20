import { m } from "framer-motion";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import type { ApiError } from "../../api/http";
import { Background } from "../../components/Background";
import { Icon } from "../../components/Icon";
import { Logo } from "../../components/Logo";
import { adminApi } from "../api";
import { useAdminAuth } from "../auth";

export function LoginPage() {
  const setUser = useAdminAuth((s) => s.setUser);
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await adminApi.csrf();
      setUser(await adminApi.login(username, password));
      navigate("/admin", { replace: true });
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="page-center">
      <Background />
      <m.form
        className="glass login-card"
        onSubmit={submit}
        initial={{ opacity: 0, y: 24, rotateX: 10 }}
        animate={{ opacity: 1, y: 0, rotateX: 0 }}
        transition={{ type: "spring", stiffness: 200, damping: 22 }}
      >
        <Logo title="Aziz Academy" />
        <h1>Tizimga kirish</h1>
        <p className="muted">Faqat administratorlar uchun.</p>
        <div className="field">
          <label htmlFor="u">Login</label>
          <input id="u" className="input" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        </div>
        <div className="field">
          <label htmlFor="p">Parol</label>
          <input id="p" type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </div>
        {error && <div className="alert">{error}</div>}
        <button className="btn btn-primary btn-lg btn-block" disabled={busy}>
          {busy ? <span className="spinner" /> : <Icon name="shield" size={18} />} Kirish
        </button>
      </m.form>
    </main>
  );
}
