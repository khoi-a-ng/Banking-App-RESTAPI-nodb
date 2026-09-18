import { money } from "./api";

// A list of transactions as a feed rather than a table. Used on the customer's
// home page (their own recent activity) and the admin overview (bank-wide,
// where each row also says whose account it was).
export default function ActivityFeed({
  items = [],
  showCustomer = false,
  emptyText = "Nothing has happened yet.",
}) {
  if (items.length === 0) return <div className="empty">{emptyText}</div>;

  return (
    <ul className="feed">
      {items.map((t) => {
        const isIn = t.type === "deposit";
        return (
          <li key={t.txn_id} className="feed-item">
            <span className={`feed-icon ${isIn ? "in" : "out"}`} aria-hidden="true">
              {isIn ? "+" : "−"}
            </span>
            <div className="feed-main">
              <div className="feed-title">
                {t.description || (isIn ? "Deposit" : "Withdrawal")}
                {t.by_staff && <span className="badge staff">Staff</span>}
              </div>
              <div className="feed-meta">
                {showCustomer && t.customer_name && <span>{t.customer_name} · </span>}
                Account #{t.account_id} · {when(t.created_at)}
              </div>
            </div>
            <span className={`feed-amount mono ${isIn ? "amount-in" : "amount-out"}`}>
              {isIn ? "+" : "−"}
              {money(t.amount)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export function when(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
