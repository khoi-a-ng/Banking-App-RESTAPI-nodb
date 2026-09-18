import { useState } from "react";
import { money } from "./api";
import { when } from "./ActivityFeed";

// The account panel: balance, move money, close, and full history.
//
// Shared by the customer's Accounts page and the admin view so the two can't
// drift apart. The parent decides what's *allowed* (canDisburse) and what
// *happens* (onMove / onClose) — this component only renders and collects
// input. It never calls the API itself.
export default function AccountDetail({
  account,
  transactions,
  viewerEmail,
  canDisburse = false,
  onMove,
  onClose,
  onDismiss,
}) {
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  async function move(kind) {
    setBusy(true);
    try {
      await onMove(kind, amount, description);
      setAmount("");
      setDescription("");
    } finally {
      setBusy(false);
    }
  }

  const hasMoney = Number(account.balance) > 0;
  // A customer can't close an account with money in it; staff can, and the
  // balance is paid out as a recorded withdrawal first.
  const closeBlocked = hasMoney && !canDisburse;

  return (
    <div className="card">
      <div className="card-head">
        <div className="card-title">
          <span>Account #{account.id}</span>
          <span className="card-sub">
            Opened {new Date(account.created_at).toLocaleDateString()}
          </span>
        </div>
        <div className="card-head-right">
          <span className="balance">{money(account.balance)}</span>
          {onDismiss && (
            <button className="btn-ghost btn-sm" onClick={onDismiss}>
              Dismiss
            </button>
          )}
        </div>
      </div>

      <div className="card-body">
        <div className="row">
          <div className="field">
            <label htmlFor={`amount-${account.id}`}>Amount</label>
            <input
              id={`amount-${account.id}`}
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="25.00"
            />
          </div>
          <div className="field grow">
            <label htmlFor={`desc-${account.id}`}>Description</label>
            <input
              id={`desc-${account.id}`}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Paycheck"
            />
          </div>
          <div className="btn-group">
            <button
              className="btn-primary"
              disabled={!amount || busy}
              onClick={() => move("deposit")}
            >
              Deposit
            </button>
            <button
              className="btn-secondary"
              disabled={!amount || busy}
              onClick={() => move("withdraw")}
            >
              Withdraw
            </button>
          </div>
        </div>

        <div className="panel-footer">
          <button
            className="btn-danger btn-sm"
            disabled={busy || closeBlocked}
            onClick={onClose}
          >
            {hasMoney && canDisburse ? "Close & disburse balance" : "Close account"}
          </button>
          {closeBlocked && (
            <span className="hint">Withdraw the balance first — an account must be empty to close.</span>
          )}
        </div>
      </div>

      {transactions.length === 0 ? (
        <div className="empty">No transactions on this account yet.</div>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Type</th>
                <th>Amount</th>
                <th>Balance after</th>
                <th>Description</th>
                <th>By</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.txn_id}>
                  <td className="muted nowrap">{when(t.created_at)}</td>
                  <td className="cap">{t.type}</td>
                  <td className={`mono ${t.type === "deposit" ? "amount-in" : "amount-out"}`}>
                    {t.type === "deposit" ? "+" : "−"}
                    {money(t.amount)}
                  </td>
                  <td className="mono">{money(t.balance_after)}</td>
                  <td className="muted">{t.description || "—"}</td>
                  <td>{byLabel(t, viewerEmail)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// The audit column. "Staff" is the one that matters — it means an admin, not
// the account holder, moved this money.
function byLabel(t, viewerEmail) {
  if (t.by_staff) return <span className="badge staff">Staff</span>;
  if (!t.performed_by) return <span className="muted">—</span>;
  if (t.performed_by === viewerEmail) return <span className="muted">You</span>;
  return <span className="muted">Customer</span>;
}
