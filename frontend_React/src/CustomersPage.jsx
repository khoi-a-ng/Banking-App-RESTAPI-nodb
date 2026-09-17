import { useEffect, useState } from "react";
import { api } from "./api";

export default function CustomersPage() {
  const [customers, setCustomers] = useState([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  // Empty dependency array = run once, when the component first mounts.
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

  async function handleCreate(event) {
    event.preventDefault(); // stop the browser's default full-page form submit
    setBusy(true);
    try {
      await api.createCustomer(name, email);
      setName("");
      setEmail("");
      setError(null);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(customerId) {
    try {
      await api.deleteCustomer(customerId);
      setError(null);
      await load();
    } catch (err) {
      // e.g. customer_has_accounts (409) — the backend's own message shows here
      setError(err.message);
    }
  }

  return (
    <main className="page">
      <div className="page-head">
        <h1>Customers</h1>
        <p>Every customer in the bank. A customer must exist before they can hold an account.</p>
      </div>

      {error && <div className="alert">{error}</div>}

      <div className="card">
        <div className="card-head">Add a customer</div>
        <div className="card-body">
          <form className="row" onSubmit={handleCreate}>
            <div className="field">
              <label htmlFor="name">Name</label>
              <input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ada Lovelace"
                required
              />
            </div>
            <div className="field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ada@example.com"
                required
              />
            </div>
            <button className="btn-primary" disabled={busy}>
              {busy ? "Saving…" : "Add customer"}
            </button>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <span>All customers</span>
          <span className="pill">{customers.length}</span>
        </div>
        {customers.length === 0 ? (
          <div className="empty">No customers yet — add one above.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Email</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr key={c.customer_id}>
                  <td className="mono muted">#{c.customer_id}</td>
                  <td>{c.name}</td>
                  <td className="muted">{c.email}</td>
                  <td style={{ textAlign: "right" }}>
                    <button
                      className="btn-danger btn-sm"
                      onClick={() => handleDelete(c.customer_id)}
                    >
                      Delete
                    </button>
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
