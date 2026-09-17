import { useEffect, useState } from "react";
import { api, money } from "./api";

export default function HomePage({ customer, onGoToAccounts }) {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // One call gets the customer, their accounts, and the total — the
    // backend does the summing so the frontend can't disagree with it.
    api.me().then(setSummary).catch((e) => setError(e.message));
  }, []);

  return (
    <main className="page">
      <div className="page-head">
        <h1>Welcome back, {customer.name.split(" ")[0]}</h1>
        <p>Here's where things stand today.</p>
      </div>

      {error && <div className="alert">{error}</div>}

      <div className="summary-grid">
        <div className="card stat">
          <div className="stat-label">Total balance</div>
          <div className="stat-value">
            {summary ? money(summary.total_balance) : "—"}
          </div>
        </div>
        <div className="card stat">
          <div className="stat-label">Open accounts</div>
          <div className="stat-value">{summary ? summary.accounts.length : "—"}</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Customer since</div>
          <div className="stat-value small">
            {new Date(customer.created_at).toLocaleDateString(undefined, {
              month: "short",
              year: "numeric",
            })}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <span>Your accounts</span>
          <button className="btn-secondary btn-sm" onClick={onGoToAccounts}>
            Manage accounts
          </button>
        </div>
        {!summary ? (
          <div className="empty">Loading…</div>
        ) : summary.accounts.length === 0 ? (
          <div className="empty">
            No accounts yet — open one from the Accounts tab.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Account</th>
                <th>Balance</th>
                <th>Opened</th>
              </tr>
            </thead>
            <tbody>
              {summary.accounts.map((a) => (
                <tr key={a.id}>
                  <td className="mono">#{a.id}</td>
                  <td className="mono">{money(a.balance)}</td>
                  <td className="muted">
                    {new Date(a.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
}
