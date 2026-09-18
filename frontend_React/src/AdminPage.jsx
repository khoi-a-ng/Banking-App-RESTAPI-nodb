import { useEffect, useState } from "react";
import { api, money } from "./api";
import AccountDetail from "./AccountDetail";
import ActivityFeed from "./ActivityFeed";


export default function AdminPage({ email }) {
  const [overview, setOverview] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [query, setQuery] = useState("");
  const [customer, setCustomer] = useState(null); // the one selected
  const [accounts, setAccounts] = useState([]);
  const [account, setAccount] = useState(null); // the one selected
  const [transactions, setTransactions] = useState([]);
  const [openDeposit, setOpenDeposit] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    loadTop();
  }, []);

  // The two things the page needs on arrival, fetched together.
  async function loadTop() {
    try {
      const [o, c] = await Promise.all([api.adminOverview(), api.listCustomers()]);
      setOverview(o);
      setCustomers(c.results);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function selectCustomer(c) {
    setCustomer(c);
    setAccounts([]);
    setAccount(null);
    setTransactions([]);
    try {
      const data = await api.customerAccounts(c.customer_id);
      setAccounts(data.results);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function selectAccount(a) {
    setAccount(a);
    try {
      const data = await api.listTransactions(a.id);
      setTransactions(data.results);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }


  async function refresh() {
    const [o, accts] = await Promise.all([
      api.adminOverview(),
      api.customerAccounts(customer.customer_id),
    ]);
    setOverview(o);
    setAccounts(accts.results);
    if (account) {
      const still = accts.results.find((a) => a.id === account.id);
      if (still) {
        setAccount(still);
        setTransactions((await api.listTransactions(still.id)).results);
      } else {
        // It was just closed.
        setAccount(null);
        setTransactions([]);
      }
    }
  }

  async function handleMove(kind, amount, description) {
    try {
      if (kind === "deposit") await api.deposit(account.id, amount, description);
      else await api.withdraw(account.id, amount, description);
      setError(null);
      await refresh();
    } catch (err) {
      setError(err.message); 
    }
  }

  async function handleCloseAccount() {
    const balance = Number(account.balance);
    const message =
      balance > 0
        ? `Account #${account.id} holds ${money(balance)}. Closing it will record a withdrawal of the full balance in your name, then close the account. Continue?`
        : `Close account #${account.id}?`;
    if (!window.confirm(message)) return;
    try {
      await api.closeAccount(account.id);
      setError(null);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleOpenAccount(event) {
    event.preventDefault();
    try {
      await api.openAccountFor(customer.customer_id, openDeposit);
      setOpenDeposit("");
      setError(null);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeactivate(c) {
    const ok = window.confirm(
      `Deactivate ${c.name}? They will no longer be able to sign in. Their records are kept.`
    );
    if (!ok) return;
    try {
      await api.deleteCustomer(c.customer_id);
      if (customer?.customer_id === c.customer_id) {
        setCustomer(null);
        setAccounts([]);
        setAccount(null);
        setTransactions([]);
      }
      setError(null);
      await loadTop();
    } catch (err) {
      setError(err.message);
    }
  }

  const q = query.trim().toLowerCase();
  const visible = q
    ? customers.filter(
        (c) => c.name.toLowerCase().includes(q) || c.email.toLowerCase().includes(q)
      )
    : customers;

  return (
    <main className="page">
      <div className="page-head">
        <h1>Overview</h1>
        <p>
          Signed in as <strong>{email}</strong>. Everything in the bank, and the
          people who hold it.
        </p>
      </div>

      {error && <div className="alert">{error}</div>}

      <div className="summary-grid">
        <div className="card stat">
          <div className="stat-label">Customers</div>
          <div className="stat-value">{overview ? overview.customers : "—"}</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Open accounts</div>
          <div className="stat-value">{overview ? overview.accounts : "—"}</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Total held</div>
          <div className="stat-value">
            {overview ? money(overview.total_balance) : "—"}
          </div>
        </div>
      </div>

      <div className="two-col wide-left">
        <div className="card">
          <div className="card-head">
            <span>Customers</span>
            <span className="pill">{visible.length}</span>
          </div>
          <div className="card-body tight">
            <input
              id="customer-search"
              className="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name or email"
            />
          </div>
          {visible.length === 0 ? (
            <div className="empty">
              {customers.length === 0 ? "No customers have signed up yet." : "No matches."}
            </div>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Customer</th>
                    <th>Joined</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((c) => (
                    <tr
                      key={c.customer_id}
                      className={`selectable ${
                        customer?.customer_id === c.customer_id ? "selected" : ""
                      }`}
                      onClick={() => selectCustomer(c)}
                    >
                      <td>
                        <div className="cell-stack">
                          <span>{c.name}</span>
                          <span className="muted small">{c.email}</span>
                        </div>
                      </td>
                      <td className="muted nowrap">
                        {new Date(c.created_at).toLocaleDateString()}
                      </td>
                      <td className="cell-actions">
                        <div className="btn-group">
                          <button
                            className="btn-secondary btn-sm"
                            onClick={(e) => {
                              // Without this, the click also hits the row's
                              // own onClick and both handlers fire.
                              e.stopPropagation();
                              selectCustomer(c);
                            }}
                          >
                            View
                          </button>
                          <button
                            className="btn-danger btn-sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeactivate(c);
                            }}
                          >
                            Deactivate
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-head">Recent activity</div>
          <ActivityFeed
            items={overview?.recent_transactions}
            showCustomer
            emptyText="No transactions anywhere yet."
          />
        </div>
      </div>

      {customer && (
        <div className="card">
          <div className="card-head">
            <div className="card-title">
              <span>{customer.name}</span>
              <span className="card-sub">
                {customer.email} · #{customer.customer_id}
              </span>
            </div>
            <button
              className="btn-ghost btn-sm"
              onClick={() => {
                setCustomer(null);
                setAccounts([]);
                setAccount(null);
                setTransactions([]);
              }}
            >
              Dismiss
            </button>
          </div>

          <div className="card-body">
            <form className="row" onSubmit={handleOpenAccount}>
              <div className="field">
                <label htmlFor="open-deposit">Open an account for {customer.name.split(" ")[0]}</label>
                <input
                  id="open-deposit"
                  inputMode="decimal"
                  value={openDeposit}
                  onChange={(e) => setOpenDeposit(e.target.value)}
                  placeholder="Initial deposit, e.g. 100.00"
                />
              </div>
              <button className="btn-primary">Open account</button>
            </form>
          </div>

          {accounts.length === 0 ? (
            <div className="empty">
              {customer.name} holds no open accounts — so this customer can be deactivated.
            </div>
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
                      className={`selectable ${account?.id === a.id ? "selected" : ""}`}
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
      )}

      {account && (
        <AccountDetail
          account={account}
          transactions={transactions}
          viewerEmail={email}
          canDisburse
          onMove={handleMove}
          onClose={handleCloseAccount}
          onDismiss={() => {
            setAccount(null);
            setTransactions([]);
          }}
        />
      )}
    </main>
  );
}
