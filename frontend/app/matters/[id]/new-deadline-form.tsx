"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Modal } from "@/components/ui/modal";
import { useToast } from "@/components/toast-context";

function todayISO(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function dateISO(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// I-39: relative quick-picks, computed from today at click time — each just
// populates the same field the lawyer could type into directly, nothing more.
const QUICK_PICKS: { label: string; compute: () => string }[] = [
  { label: "In 1 week", compute: () => dateISO(new Date(new Date().setDate(new Date().getDate() + 7))) },
  { label: "In 2 weeks", compute: () => dateISO(new Date(new Date().setDate(new Date().getDate() + 14))) },
  { label: "In 1 month", compute: () => dateISO(new Date(new Date().setMonth(new Date().getMonth() + 1))) },
];

type Priority = "standard" | "critical";

/** Opens as a modal, mirroring NewMatterModal/EditClientModal, instead of expanding inline into the Deadlines section. */
export function NewDeadlineForm({ matterId, onUpdated }: { matterId: string; onUpdated?: () => void }) {
  const router = useRouter();
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [priority, setPriority] = useState<Priority>("standard");
  const [leadDays, setLeadDays] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const minDate = todayISO();

  function close() {
    setOpen(false);
    setTitle("");
    setDueDate("");
    setPriority("standard");
    setLeadDays("");
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

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
        priority,
        notificationLeadDays: leadDays.trim() === "" ? null : Number(leadDays),
      }),
    });

    setSubmitting(false);

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't save this deadline — retry.");
      return;
    }

    close();
    showToast("Deadline created");
    if (onUpdated) onUpdated();
    else router.refresh();
  }

  if (!open) {
    return (
      <Button variant="secondary" className="btn-hold-bg" onClick={() => setOpen(true)}>
        <span className="btn-plus-icon">+</span> New Deadline
      </Button>
    );
  }

  return (
    <Modal title="New Deadline" onClose={close} width={480}>
      <form onSubmit={handleSubmit} className="stack-4">
        <div className="field">
          <label className="field-label" htmlFor="deadline-title">Title *</label>
          <input id="deadline-title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} required autoFocus />
        </div>
        <div className="field">
          <label className="field-label" htmlFor="deadline-due-date">Due date *</label>
          <div className="row" style={{ gap: "var(--space-2)", marginBottom: "var(--space-2)", flexWrap: "wrap" }}>
            {QUICK_PICKS.map((pick) => (
              <button
                key={pick.label}
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setDueDate(pick.compute())}
              >
                {pick.label}
              </button>
            ))}
          </div>
          <input id="deadline-due-date" className="input" type="date" value={dueDate} min={minDate} onChange={(e) => setDueDate(e.target.value)} required />
        </div>
        <div className="field">
          <label className="field-label" htmlFor="deadline-priority">Priority</label>
          <select id="deadline-priority" className="select" value={priority} onChange={(e) => setPriority(e.target.value as Priority)}>
            <option value="standard">Standard</option>
            <option value="critical">Critical</option>
          </select>
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
          <Button type="button" variant="ghost" onClick={close} disabled={submitting}>
            Cancel
          </Button>
        </div>
      </form>
    </Modal>
  );
}
