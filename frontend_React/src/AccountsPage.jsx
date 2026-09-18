import { useEffect, useState } from "react";
import { api, money } from "./api";
import AccountDetail from "./AccountDetail";

export default function AccountsPage({ viewerEmail }) {
  const [accounts, setAccounts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [initialDeposit, setInitialDeposit] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAccounts();
  }, []);

  async function loadAccounts() {
    try {
      // No customer id needed — the API returns only *your* accounts,
      // based on the token attached to the request.
      const data = await api.listAccounts();
      setAccounts(data.results);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function selectAccount(account) {
    setSelected(account);
    try {
      const data = await api.listTransactions(account.id);
      setTransactions(data.results);
    } catch (err) {
      setError(err.message);
    }
  }

  // Fire all three refreshes at once — sequential awaits left the panel
  // showing a stale balance while each Supabase round-trip completed.
  async function refresh(accountId) {
    const [list, account, txns] = await Promise.all([
      api.listAccounts(),
      api.getAccount(accountId),
      api.listTransactions(accountId),
    ]);
    setAccounts(list.results);
    setSelected(account);
    setTransactions(txns.results);
  }

  async function handleOpenAccount(event) {
    event.preventDefault();
    try {
      await api.openAccount(initialDeposit);
      setInitialDeposit("");
      setError(null);
      await loadAccounts();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleMove(kind, amount, description) {
    try {
      if (kind === "deposit") await api.deposit(selected.id, amount, description);
      else await api.withdraw(selected.id, amount, description);
      setError(null);
      await refresh(selected.id);
    } catch (err) {
      setError(err.message); // e.g. insufficient_funds (409)
    }
  }

  async function handleClose() {
    try {
      await api.closeAccount(selected.id);
      setSelected(null);
      setTransactions([]);
      setError(null);
      await loadAccounts();
    } catch (err) {
      setError(err.message); // e.g. account_not_empty (409)
    }
  }

  return (
    <main className="page">
      <div className="page-head">
        <h1>Accounts</h1>
        <p>Your accounts. Select one to deposit, withdraw, or view its history.</p>
      </div>

      {error && <div className="alert">{error}</div>}

      <div className="card">
        <div className="card-head">Open a new account</div>
        <div className="card-body">
          <form className="row" onSubmit={handleOpenAccount}>
            <div className="field">
              <label htmlFor="initial">Initial deposit</label>
              <input
                id="initial"
                inputMode="decimal"
                value={initialDeposit}
                onChange={(e) => setInitialDeposit(e.target.value)}
                placeholder="0.00"
              />
            </div>
            <button className="btn-primary">Open account</button>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <span>Your accounts</span>
          <span className="pill">{accounts.length}</span>
        </div>
        {accounts.length === 0 ? (
          <div className="empty">No accounts yet — open one above.</div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Balance</th>
                  <th>Opened</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((a) => (
                  <tr
                    key={a.id}
                    className={`selectable ${selected?.id === a.id ? "selected" : ""}`}
                    onClick={() => selectAccount(a)}
                  >
                    <td className="mono">#{a.id}</td>
                    <td className="mono">{money(a.balance)}</td>
                    <td className="muted nowrap">
                      {new Date(a.created_at).toLocaleDateString()}
                    </td>
                    <td className="cell-actions">
                      <button
                        className="btn-secondary btn-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          selectAccount(a);
                        }}
                      >
                        Manage
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selected && (
        <AccountDetail
          account={selected}
          transactions={transactions}
          viewerEmail={viewerEmail}
          onMove={handleMove}
          onClose={handleClose}
          onDismiss={() => {
            setSelected(null);
            setTransactions([]);
          }}
        />
      )}
    </main>
  );
}
