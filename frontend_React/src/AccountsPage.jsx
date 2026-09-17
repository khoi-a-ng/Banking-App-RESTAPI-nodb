import { useEffect, useState } from "react";
import { api, money } from "./api";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [initialDeposit, setInitialDeposit] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
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

  async function handleMove(kind) {
    try {
      if (kind === "deposit") {
        await api.deposit(selected.id, amount, description);
      } else {
        await api.withdraw(selected.id, amount, description);
      }
      setAmount("");
      setDescription("");
      setError(null);
      await refresh(selected.id);
    } catch (err) {
      setError(err.message); // e.g. insufficient_funds (409)
    }
  }

  async function handleClose(accountId) {
    try {
      await api.closeAccount(accountId);
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
                  <td className="muted">
                    {new Date(a.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <div className="btn-group" style={{ justifyContent: "flex-end" }}>
                      <button
                        className="btn-secondary btn-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          selectAccount(a);
                        }}
                      >
                        Manage
                      </button>
                      <button
                        className="btn-danger btn-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleClose(a.id);
                        }}
                      >
                        Close
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <div className="card">
          <div className="card-head">
            <span>Account #{selected.id}</span>
            <span className="balance">{money(selected.balance)}</span>
          </div>
          <div className="card-body">
            <div className="row">
              <div className="field">
                <label htmlFor="amount">Amount</label>
                <input
                  id="amount"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="25.00"
                />
              </div>
              <div className="field">
                <label htmlFor="description">Description</label>
                <input
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Paycheck"
                />
              </div>
              <button
                className="btn-primary"
                disabled={!amount}
                onClick={() => handleMove("deposit")}
              >
                Deposit
              </button>
              <button
                className="btn-secondary"
                disabled={!amount}
                onClick={() => handleMove("withdraw")}
              >
                Withdraw
              </button>
            </div>
          </div>

          {transactions.length === 0 ? (
            <div className="empty">No transactions on this account yet.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Txn</th>
                  <th>Type</th>
                  <th>Amount</th>
                  <th>Balance after</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t) => (
                  <tr key={t.txn_id}>
                    <td className="mono muted">#{t.txn_id}</td>
                    <td>{t.type}</td>
                    <td
                      className={`mono ${
                        t.type === "deposit" ? "amount-in" : "amount-out"
                      }`}
                    >
                      {t.type === "deposit" ? "+" : "−"}
                      {money(t.amount)}
                    </td>
                    <td className="mono">{money(t.balance_after)}</td>
                    <td className="muted">{t.description || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </main>
  );
}
