"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Modal } from "@/components/ui/modal";

type Client = { id: string; name: string; contactEmail: string | null; contactPhone: string | null; notes: string | null };

/** I-17: same field set as the New Client form (clients/new/page.tsx), pre-filled with the current values. */
export function EditClientModal({ client }: { client: Client }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(client.name);
  const [contactEmail, setContactEmail] = useState(client.contactEmail ?? "");
  const [contactPhone, setContactPhone] = useState(client.contactPhone ?? "");
  const [notes, setNotes] = useState(client.notes ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setOpen(false);
    setName(client.name);
    setContactEmail(client.contactEmail ?? "");
    setContactPhone(client.contactPhone ?? "");
    setNotes(client.notes ?? "");
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/clients/${client.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        name,
        contact_email: contactEmail || undefined,
        contact_phone: contactPhone || undefined,
        notes: notes || undefined,
      }),
    });

    setSubmitting(false);

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't save this client — retry.");
      return;
    }

    setOpen(false);
    router.refresh();
  }

  if (!open) {
    return (
      <Button variant="secondary" onClick={() => setOpen(true)}>
        Edit
      </Button>
    );
  }

  return (
    <Modal title="Edit Client" onClose={reset} width={480}>
      <form onSubmit={handleSubmit} className="stack-4">
        <div className="field">
          <label className="field-label" htmlFor="edit-name">Name *</label>
          <input id="edit-name" className="input" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
        </div>
        <div className="field">
          <label className="field-label" htmlFor="edit-contactEmail">Contact email</label>
          <input id="edit-contactEmail" className="input" type="email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} />
        </div>
        <div className="field">
          <label className="field-label" htmlFor="edit-contactPhone">Contact phone</label>
          <input id="edit-contactPhone" className="input" type="tel" value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} />
        </div>
        <div className="field">
          <label className="field-label" htmlFor="edit-notes">Notes</label>
          <textarea id="edit-notes" className="textarea" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>

        {error && <ErrorBanner>{error}</ErrorBanner>}

        <div className="row">
          <Button type="submit" loading={submitting} disabled={!name.trim()}>
            {submitting ? "Saving…" : "Save"}
          </Button>
          <Button type="button" variant="ghost" onClick={reset} disabled={submitting}>
            Cancel
          </Button>
        </div>
      </form>
    </Modal>
  );
}
