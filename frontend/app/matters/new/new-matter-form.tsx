"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { useToast } from "@/components/toast-context";
import { ClientCombobox } from "./client-combobox";

type Client = { id: string; name: string };

function todayISO(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export function NewMatterForm({ clients, initialClientId }: { clients: Client[]; initialClientId?: string }) {
  const router = useRouter();
  const { showToast } = useToast();
  const [clientId, setClientId] = useState(initialClientId ?? clients[0]?.id ?? "");
  const [title, setTitle] = useState("");

  // I-28: optional, collapsed "Add a deadline" section.
  const [deadlineOpen, setDeadlineOpen] = useState(false);
  const [deadlineTitle, setDeadlineTitle] = useState("");
  const [deadlineDueDate, setDeadlineDueDate] = useState("");
  const [deadlineLeadDays, setDeadlineLeadDays] = useState("");
  const minDate = todayISO();

  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // Same BR-009 check new-deadline-form.tsx does — only relevant if a deadline was actually filled in.
    if (deadlineOpen && deadlineDueDate) {
      if (deadlineDueDate < minDate) {
        setError("The deadline's due date can't be in the past — please pick today or a later date.");
        return;
      }
      if (!deadlineTitle.trim()) {
        setError("The deadline needs a title, or clear its due date to skip adding one.");
        return;
      }
    }

    setSubmitting(true);

    const matterRes = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ client_id: clientId, title }),
    });

    if (!matterRes.ok) {
      setSubmitting(false);
      const body = await matterRes.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't save this matter — retry.");
      return;
    }

    const created = await matterRes.json();

    // I-28: two existing calls chained client-side — no new API.
    if (deadlineOpen && deadlineDueDate) {
      const deadlineRes = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${created.id}/deadlines`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          title: deadlineTitle,
          dueDate: deadlineDueDate,
          notificationLeadDays: deadlineLeadDays.trim() === "" ? null : Number(deadlineLeadDays),
        }),
      });
      if (!deadlineRes.ok) {
        // The Matter itself was created successfully — don't lose that on a deadline-only failure.
        // Land on the Matter's own page, where the lawyer can add the Deadline directly instead.
        showToast("Matter created");
        router.push(`/matters/${created.id}`);
        router.refresh();
        return;
      }
    }

    showToast("Matter created");
    router.push(`/matters/${created.id}`);
    router.refresh();
  }

  if (clients.length === 0) {
    return (
      <EmptyState
        title="No clients yet"
        body="A Matter always belongs to a Client — create one first."
        action={<Button href="/clients/new" className="btn-hold-bg"><span className="btn-plus-icon">+</span> New Client</Button>}
      />
    );
  }

  return (
    <form onSubmit={handleSubmit} className="card stack-4">
      <ClientCombobox clients={clients} clientId={clientId} onChange={setClientId} />
      <div className="field">
        <label className="field-label" htmlFor="title">Matter title *</label>
        <input id="title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} required autoFocus />
      </div>

      {!deadlineOpen ? (
        <Button type="button" variant="secondary" className="btn-hold-bg" onClick={() => setDeadlineOpen(true)} style={{ alignSelf: "flex-start" }}>
          <span className="btn-plus-icon">+</span> Add a deadline
        </Button>
      ) : (
        <div className="card" style={{ background: "var(--color-bg-surface-hover)" }}>
          <div className="row-between" style={{ marginBottom: "var(--space-3)" }}>
            <span className="field-label" style={{ margin: 0 }}>Deadline (optional)</span>
            <button
              type="button"
              className="btn-link"
              onClick={() => {
                setDeadlineOpen(false);
                setDeadlineTitle("");
                setDeadlineDueDate("");
                setDeadlineLeadDays("");
              }}
            >
              Remove
            </button>
          </div>
          <div className="stack-4">
            <div className="field">
              <label className="field-label" htmlFor="deadline-title">Deadline title</label>
              <input id="deadline-title" className="input" value={deadlineTitle} onChange={(e) => setDeadlineTitle(e.target.value)} />
            </div>
            <div className="field">
              <label className="field-label" htmlFor="deadline-due-date">Due date</label>
              <input
                id="deadline-due-date"
                className="input"
                type="date"
                value={deadlineDueDate}
                min={minDate}
                onChange={(e) => setDeadlineDueDate(e.target.value)}
              />
            </div>
            <div className="field" style={{ marginBottom: 0 }}>
              <label className="field-label" htmlFor="deadline-lead-days">Notify how many days before? (default 3)</label>
              <input
                id="deadline-lead-days"
                className="input"
                type="number"
                min={0}
                value={deadlineLeadDays}
                onChange={(e) => setDeadlineLeadDays(e.target.value)}
                placeholder="3"
              />
            </div>
          </div>
        </div>
      )}

      {error && <ErrorBanner>{error}</ErrorBanner>}

      <Button type="submit" loading={submitting} disabled={!title.trim() || !clientId}>
        {submitting ? "Saving…" : "Save"}
      </Button>
    </form>
  );
}
