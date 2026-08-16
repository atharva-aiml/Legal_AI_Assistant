"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";

function todayISO(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export function NewDeadlineForm({ matterId }: { matterId: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [leadDays, setLeadDays] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const minDate = todayISO();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // BR-009: a Deadline's due date can't be in the past. The date input's
    // min= attribute blocks this in the calendar picker, but a manually
    // typed date bypasses that in some browsers — checked explicitly here
    // too, with the server-side check (Deadline.validateDueDate) as the
    // real backstop either way.
    if (dueDate < minDate) {
      setError("The due date can't be in the past — please pick today or a later date.");
      return;
    }

    setSubmitting(true);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/deadlines`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        title,
        dueDate,
        notificationLeadDays: leadDays.trim() === "" ? null : Number(leadDays),
      }),
    });

    setSubmitting(false);

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't save this deadline — retry.");
      return;
    }

    setTitle("");
    setDueDate("");
    setLeadDays("");
    setOpen(false);
    router.refresh();
  }

  if (!open) {
    return (
      <Button variant="secondary" onClick={() => setOpen(true)}>
        + New Deadline
      </Button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="card stack-4" style={{ width: "100%", flexBasis: "100%" }}>
      <div className="field">
        <label className="field-label" htmlFor="deadline-title">Title *</label>
        <input id="deadline-title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} required autoFocus />
      </div>
      <div className="field">
        <label className="field-label" htmlFor="deadline-due-date">Due date *</label>
        <input id="deadline-due-date" className="input" type="date" value={dueDate} min={minDate} onChange={(e) => setDueDate(e.target.value)} required />
      </div>
      <div className="field">
        <label className="field-label" htmlFor="deadline-lead-days">Notify how many days before? (default 3)</label>
        <input id="deadline-lead-days" className="input" type="number" min={0} value={leadDays} onChange={(e) => setLeadDays(e.target.value)} placeholder="3" />
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      <div className="row">
        <Button type="submit" loading={submitting} disabled={!title.trim() || !dueDate}>
          {submitting ? "Saving…" : "Save"}
        </Button>
        <Button type="button" variant="ghost" onClick={() => setOpen(false)} disabled={submitting}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
