import { useEffect, useState } from "react";
import { api, money } from "./api";


export default function AdminPage({ email }) {
  const [customers, setCustomers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const data = await api.listCustomers();
      setCustomers(data.results);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }


  async function selectCustomer(customer) {
    setSelected(customer);
    setLoadingAccounts(true);
    setAccounts([]);
    try {
      const data = await api.customerAccounts(customer.customer_id);
      setAccounts(data.results);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingAccounts(false);
    }
  }

  async function handleDelete(customer) {
    try {
      await api.deleteCustomer(customer.customer_id);

      if (selected?.customer_id === customer.customer_id) {
        setSelected(null);
        setAccounts([]);
      }
      setError(null);
      await load();
    } catch (err) {

      setError(err.message);
    }
  }

  const totalBalance = accounts.reduce((sum, a) => sum + Number(a.balance), 0);

  return (
    <main className="page">
      <div className="page-head">
        <h1>Customers</h1>
        <p>
          Signed in as <strong>{email}</strong> — every customer in the bank,
          and the accounts they hold.
        </p>
      </div>

      {error && <div className="alert">{error}</div>}

      <div className="card">
        <div className="card-head">
          <span>All customers</span>
          <span className="pill">{customers.length}</span>
        </div>
        {customers.length === 0 ? (
          <div className="empty">No customers have signed up yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Joined</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr
                  key={c.customer_id}
                  className={`selectable ${
                    selected?.customer_id === c.customer_id ? "selected" : ""
                  }`}
                  onClick={() => selectCustomer(c)}
                >
                  <td className="mono muted">#{c.customer_id}</td>
                  <td>{c.name}</td>
                  <td className="muted">{c.email}</td>
                  <td className="muted">
                    {new Date(c.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <div className="btn-group" style={{ justifyContent: "flex-end" }}>
                      <button
                        className="btn-secondary btn-sm"
                        onClick={(e) => {
                          // Without this, the click also hits the row's own onClick and both handlers fire.
                          e.stopPropagation();
                          selectCustomer(c);
                        }}
                      >
                        Accounts
                      </button>
                      <button
                        className="btn-danger btn-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(c);
                        }}
                      >
                        Delete
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
            <span>
              {selected.name}'s accounts
            </span>
            <button
              className="btn-secondary btn-sm"
              onClick={() => {
                setSelected(null);
                setAccounts([]);
              }}
            >
              Close
            </button>
          </div>

          {loadingAccounts ? (
            <div className="empty">Loading…</div>
          ) : accounts.length === 0 ? (
            <div className="empty">
              {selected.name} holds no accounts — so this customer can be deleted.
            </div>
          ) : (
            <>
              <table>
                <thead>
                  <tr>
                    <th>Account</th>
                    <th>Balance</th>
                    <th>Opened</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.map((a) => (
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
              <div className="card-body">
                <span className="muted">
                  {accounts.length} account{accounts.length === 1 ? "" : "s"} ·{" "}
                  {money(totalBalance)} held
                </span>
              </div>
            </>
          )}
        </div>
      )}
    </main>
  );
}
