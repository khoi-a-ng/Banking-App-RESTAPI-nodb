import { useEffect, useState } from "react";
import { api, auth } from "./api";
import LoginPage from "./LoginPage";
import HomePage from "./HomePage";
import AccountsPage from "./AccountsPage";
import AdminPage from "./AdminPage";

export default function App() {

  const [session, setSession] = useState(null);
  const [page, setPage] = useState("home");
  const [menuOpen, setMenuOpen] = useState(false);
  const [checking, setChecking] = useState(true);


  function toSession(data) {
    return {
      customer: data.customer, // null for admins
      isAdmin: data.is_admin,
      email: data.email,
    };
  }


  useEffect(() => {
    if (!auth.get()) {
      setChecking(false);
      return;
    }
    api
      .me()
      .then((data) => setSession(toSession(data)))
      .catch(() => auth.clear()) // stale/invalid token
      .finally(() => setChecking(false));
  }, []);

  async function handleLogout() {
    try {
      await api.logout(); // deletes the token server-side too
    } catch {

    }
    auth.clear();
    setSession(null);
    setMenuOpen(false);
    setPage("home");
  }

  if (checking) return <div className="boot">Loading…</div>;

  if (!session) {
    return <LoginPage onAuthenticated={(data) => setSession(toSession(data))} />;
  }

  const { customer, isAdmin, email } = session;

  const displayName = customer ? customer.name : "Admin";
  const initials = (customer ? customer.name : email || "A")
    .split(/[\s@.]+/)
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
          {isAdmin ? (
            <button className="nav-tab active">Customers</button>
          ) : (
            <>
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
            </>
          )}
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
            <span className="avatar-name">{displayName}</span>
            <span className="caret">▾</span>
          </button>

          {menuOpen && (
            <>

              <div className="menu-backdrop" onClick={() => setMenuOpen(false)} />
              <div className="menu" role="menu">
                <div className="menu-head">
                  <div className="menu-name">{displayName}</div>
                  <div className="menu-email">{customer ? customer.email : email}</div>
                </div>

                {!isAdmin && (
                  <button
                    className="menu-item"
                    onClick={() => {
                      setPage("home");
                      setMenuOpen(false);
                    }}
                  >
                    My account
                  </button>
                )}
                <button className="menu-item danger" onClick={handleLogout}>
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </nav>

      {isAdmin ? (
        <AdminPage email={email} />
      ) : page === "home" ? (
        <HomePage customer={customer} onGoToAccounts={() => setPage("accounts")} />
      ) : (
        <AccountsPage viewerEmail={email} />
      )}
    </>
  );
}
