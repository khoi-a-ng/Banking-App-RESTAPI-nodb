// Thin wrapper around the Django API.
//
// Everything goes through request() so the error envelope your backend
// returns — {"error": {"code", "message", "details"}} — gets unpacked in one
// place instead of at every call site.

const BASE_URL = "http://127.0.0.1:8000/api";
const TOKEN_KEY = "olivebank.token";

// The token lives in localStorage so a page refresh doesn't log you out.
export const auth = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function request(path, options = {}) {
  const token = auth.get();
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      // This header is what DRF's TokenAuthentication reads to identify you.
      ...(token ? { Authorization: `Token ${token}` } : {}),
    },
    ...options,
  });

  // Token expired/deleted server-side (e.g. you logged out elsewhere) —
  // clear the stale copy so the app returns to the login screen.
  if (response.status === 401) {
    auth.clear();
  }

  // 204 No Content (what close/delete return) has an empty body, so calling
  // .json() on it would throw.
  if (response.status === 204) return null;

  const body = await response.json();

  if (!response.ok) {
    // Surface the backend's own message, e.g. "The account does not hold
    // enough funds for this operation."
    const error = new Error(body?.error?.message ?? "Something went wrong.");
    error.code = body?.error?.code;
    error.details = body?.error?.details;
    throw error;
  }

  return body;
}

export const api = {
  // --- Auth ---
  signup: (name, email, password) =>
    request("/auth/signup/", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    }),
  login: (email, password) =>
    request("/auth/login/", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request("/auth/logout/", { method: "POST" }),
  me: () => request("/auth/me/"),

  // --- Accounts (all scoped to the logged-in customer by the token) ---
  listAccounts: () => request("/accounts/"),
  openAccount: (initialDeposit) =>
    request("/accounts/", {
      method: "POST",
      body: JSON.stringify({ initial_deposit: initialDeposit || "0" }),
    }),
  getAccount: (accountId) => request(`/accounts/${accountId}/`),
  closeAccount: (accountId) =>
    request(`/accounts/${accountId}/`, { method: "DELETE" }),

  deposit: (accountId, amount, description) =>
    request(`/accounts/${accountId}/deposit/`, {
      method: "POST",
      body: JSON.stringify({ amount, description }),
    }),
  withdraw: (accountId, amount, description) =>
    request(`/accounts/${accountId}/withdraw/`, {
      method: "POST",
      body: JSON.stringify({ amount, description }),
    }),

  listTransactions: (accountId) => request(`/accounts/${accountId}/transactions/`),
};

export const money = (value) =>
  `$${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
