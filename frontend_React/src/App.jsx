import { useEffect, useState } from "react";
import { api, auth } from "./api";
import LoginPage from "./LoginPage";
import HomePage from "./HomePage";
import AccountsPage from "./AccountsPage";
import AdminPage from "./AdminPage";

export default function App() {
  // One object for "who is signed in", rather than just the customer.
  // An admin has no customer record at all, so tracking only `customer`
  // made a logged-in admin look logged out.
  const [session, setSession] = useState(null);
  const [page, setPage] = useState("home");
  const [menuOpen, setMenuOpen] = useState(false);
  const [checking, setChecking] = useState(true);

  // Both /auth/login/ and /auth/me/ return the same three fields, so one
  // function maps either into a session.
  function toSession(data) {
    return {
      customer: data.customer, // null for admins
      isAdmin: data.is_admin,
      email: data.email,
    };
  }

  // On first load, if a token is already in localStorage, use it to fetch the
  // current user. That's what keeps you logged in across a page refresh.
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
      // Even if the call fails, clear locally — the user asked to leave.
    }
    auth.clear();
    setSession(null);
    setMenuOpen(false);
    setPage("home");
  }

  if (checking) return <div className="boot">Loading…</div>;
  // Signed out is `session === null`. Previously this checked `customer`,
  // which is null for a perfectly valid admin — so admins were sent straight
  // back here after logging in successfully.
  if (!session) {
    return <LoginPage onAuthenticated={(data) => setSession(toSession(data))} />;
  }

  const { customer, isAdmin, email } = session;
  // Admins have no name on record, so fall back to their email for both the
  // label and the avatar initials.
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
          {/* An admin owns no accounts of their own, so Home and Accounts
              would both be empty for them — they get the customer list
              instead. */}
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
              {/* Invisible full-screen layer: clicking anywhere closes the menu */}
              <div className="menu-backdrop" onClick={() => setMenuOpen(false)} />
              <div className="menu" role="menu">
                <div className="menu-head">
                  <div className="menu-name">{displayName}</div>
                  <div className="menu-email">{customer ? customer.email : email}</div>
                </div>
                {/* "My account" goes nowhere for an admin — they don't have
                    one — so it's only offered to customers. */}
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
        <AccountsPage />
      )}
    </>
  );
}
