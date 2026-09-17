import { useEffect, useState } from "react";
import { api, auth } from "./api";
import LoginPage from "./LoginPage";
import HomePage from "./HomePage";
import AccountsPage from "./AccountsPage";

export default function App() {
  const [customer, setCustomer] = useState(null);
  const [page, setPage] = useState("home");
  const [menuOpen, setMenuOpen] = useState(false);
  const [checking, setChecking] = useState(true);

  // On first load, if a token is already in localStorage, use it to fetch the
  // current user. That's what keeps you logged in across a page refresh.
  useEffect(() => {
    if (!auth.get()) {
      setChecking(false);
      return;
    }
    api
      .me()
      .then((data) => setCustomer(data.customer))
      .catch(() => auth.clear()) // stale/invalid token
      .finally(() => setChecking(false));
  }, []);

  async function handleLogout() {
    try {
      await api.logout(); // deletes the token server-side too
    } catch {
      // Even if the call fails, clear locally — the user asked to leave.
    }
    auth.clear();
    setCustomer(null);
    setMenuOpen(false);
    setPage("home");
  }

  if (checking) return <div className="boot">Loading…</div>;
  if (!customer) return <LoginPage onAuthenticated={setCustomer} />;

  const initials = customer.name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <>
      <nav className="nav">
        <div className="nav-brand">
          <span className="nav-mark">₿</span>
          Olive Bank
        </div>

        <div className="nav-tabs">
          <button
            className={`nav-tab ${page === "home" ? "active" : ""}`}
            onClick={() => setPage("home")}
          >
            Home
          </button>
          <button
            className={`nav-tab ${page === "accounts" ? "active" : ""}`}
            onClick={() => setPage("accounts")}
          >
            Accounts
          </button>
        </div>

        {/* Account menu, pinned to the right */}
        <div className="nav-account">
          <button
            className="avatar-button"
            onClick={() => setMenuOpen((open) => !open)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
          >
            <span className="avatar">{initials}</span>
            <span className="avatar-name">{customer.name}</span>
            <span className="caret">▾</span>
          </button>

          {menuOpen && (
            <>
              {/* Invisible full-screen layer: clicking anywhere closes the menu */}
              <div className="menu-backdrop" onClick={() => setMenuOpen(false)} />
              <div className="menu" role="menu">
                <div className="menu-head">
                  <div className="menu-name">{customer.name}</div>
                  <div className="menu-email">{customer.email}</div>
                </div>
                <button
                  className="menu-item"
                  onClick={() => {
                    setPage("home");
                    setMenuOpen(false);
                  }}
                >
                  My account
                </button>
                <button className="menu-item danger" onClick={handleLogout}>
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </nav>

      {page === "home" ? (
        <HomePage customer={customer} onGoToAccounts={() => setPage("accounts")} />
      ) : (
        <AccountsPage />
      )}
    </>
  );
}
