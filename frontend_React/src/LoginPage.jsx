import { useState } from "react";
import { api, auth } from "./api";


export default function LoginPage({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const isSignup = mode === "signup";

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    try {
      const result = isSignup
        ? await api.signup(name, email, password)
        : await api.login(email, password);
      auth.set(result);
      setError(null);
      onAuthenticated(result.customer);
    } catch (err) {
      // The backend returns field errors, e.g. {"email": ["...already exists"]}
      const detail = err.details
        ? Object.values(err.details).flat().join(" ")
        : err.message;
      setError(detail);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="nav-mark">₿</span>
          <span>Olive Bank</span>
        </div>

        <h1>{isSignup ? "Create your account" : "Welcome back"}</h1>
        <p className="muted">
          {isSignup
            ? "Opening an account takes a moment."
            : "Sign in to see your accounts."}
        </p>

        {error && <div className="alert">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          {isSignup && (
            <div className="field">
              <label htmlFor="name">Full name</label>
              <input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ada Lovelace"
                required
              />
            </div>
          )}

          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>

          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={isSignup ? "at least 8 characters" : "••••••••"}
              required
            />
          </div>

          <button className="btn-primary btn-block" disabled={busy}>
            {busy ? "Please wait…" : isSignup ? "Create account" : "Sign in"}
          </button>
        </form>

        <div className="auth-switch">
          {isSignup ? "Already have an account?" : "New here?"}{" "}
          <button
            className="link"
            type="button"
            onClick={() => {
              setMode(isSignup ? "login" : "signup");
              setError(null);
            }}
          >
            {isSignup ? "Sign in" : "Create one"}
          </button>
        </div>
      </div>
    </div>
  );
}
