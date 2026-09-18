
const BASE_URL = "http://127.0.0.1:8000/api";
const ACCESS_KEY = "olivebank.access";
const REFRESH_KEY = "olivebank.refresh";

export const auth = {
  get: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),

  set: ({ access, refresh }) => {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

async function renewAccessToken() {
  const refresh = auth.getRefresh();
  if (!refresh) return false;

  const response = await fetch(`${BASE_URL}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });

  if (!response.ok) {
    auth.clear(); // refresh token expired or blacklisted — truly logged out
    return false;
  }

  auth.set(await response.json());
  return true;
}

async function request(path, options = {}, isRetry = false) {
  const token = auth.get();
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      // `Bearer` header scheme for the access token
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  });


  if (response.status === 401 && !isRetry) {
    if (await renewAccessToken()) {
      return request(path, options, true);
    }
    auth.clear(); // couldn't renew — back to the login screen
  }

  if (response.status === 204) return null;

  const body = await response.json();

  if (!response.ok) {
    const error = new Error(body?.error?.message ?? "Something went wrong.");
    error.code = body?.error?.code;
    error.details = body?.error?.details;
    throw error;
  }

  return body;
}

export const api = {

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

  logout: () =>
    request("/auth/logout/", {
      method: "POST",
      body: JSON.stringify({ refresh: auth.getRefresh() }),
    }),
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
