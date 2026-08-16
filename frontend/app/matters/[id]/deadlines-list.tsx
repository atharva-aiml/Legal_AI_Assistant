"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";

type Deadline = {
  id: string;
  matterId: string;
  title: string;
  dueDate: string;
  status: "open" | "complete";
  notificationLeadDays: number;
};

function formatDueDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function todayISO(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export function DeadlinesList({ deadlines }: { deadlines: Deadline[] }) {
  const router = useRouter();
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const today = todayISO();

  async function toggleComplete(deadline: Deadline) {
    setUpdatingId(deadline.id);
    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/deadlines/${deadline.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ status: deadline.status === "open" ? "complete" : "open" }),
    });
    setUpdatingId(null);

    if (res.ok) {
      router.refresh();
    } else {
      alert("Couldn't update this deadline — retry.");
    }
  }

  if (deadlines.length === 0) {
    return <EmptyState title="No deadlines yet" body="Add one to start tracking dates for this Matter." />;
  }

  const sorted = [...deadlines].sort((a, b) => a.dueDate.localeCompare(b.dueDate));

  return (
    <div className="stack">
      {sorted.map((d) => {
        const isOverdue = d.status === "open" && d.dueDate < today;
        return (
          <div key={d.id} className="card">
            <div className="row-between">
              <div>
                <div className="row" style={{ gap: "var(--space-2)" }}>
                  <span style={{ fontWeight: 500, textDecoration: d.status === "complete" ? "line-through" : "none" }}>
                    {d.title}
                  </span>
                  {d.status === "complete" ? (
                    <Badge variant="success">Complete</Badge>
                  ) : isOverdue ? (
                    <Badge variant="error">Overdue</Badge>
                  ) : (
                    <Badge variant="info">Upcoming</Badge>
                  )}
                </div>
                <div className="text-tertiary text-sm">Due {formatDueDate(d.dueDate)}</div>
              </div>
              <label className="checkbox-row">
                <input type="checkbox" checked={d.status === "complete"} disabled={updatingId === d.id} onChange={() => toggleComplete(d)} />
                Complete
              </label>
            </div>
          </div>
        );
      })}
    </div>
  );
}
