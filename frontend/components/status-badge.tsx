export function StatusBadge({ status }: { status: "open" | "closed" }) {
  return (
    <span className="status-dot-badge">
      <span className={`status-dot ${status === "open" ? "status-dot-open" : "status-dot-closed"}`} aria-hidden="true" />
      {status === "open" ? "Open" : "Closed"}
    </span>
  );
}
