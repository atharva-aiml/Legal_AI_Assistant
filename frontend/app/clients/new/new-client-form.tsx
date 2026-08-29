"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import { useToast } from "@/components/toast-context";

/** Same form /clients/new has always used — extracted so NewClientModal can render it inside a popup instead of only as a standalone page. */
export function NewClientForm({
  onCreated,
}: {
  /** Called right before navigating away on success — lets a modal-wrapped
   * instance (NewClientModal) close itself. A push to the same route the
   * modal is already open on doesn't remount/reset the modal's own `open`
   * state, so without this the modal was left stuck open on top of the
   * now-refreshed page underneath it. */
  onCreated?: () => void;
} = {}) {
  const router = useRouter();
  const { showToast } = useToast();
  const [name, setName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/clients`, {
      method: "POST",
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

    onCreated?.();
    showToast("Client created successfully");
    router.push("/clients");
    router.refresh();
  }

  return (
    <form onSubmit={handleSubmit} className="card stack-4">
      <div className="field">
        <label className="field-label" htmlFor="name">Name *</label>
        <input id="name" className="input" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
      </div>
      <div className="field">
        <label className="field-label" htmlFor="contactEmail">Contact email</label>
        <input id="contactEmail" className="input" type="email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} />
      </div>
      <div className="field">
        <label className="field-label" htmlFor="contactPhone">Contact phone</label>
        <input id="contactPhone" className="input" type="tel" value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} />
      </div>
      <div className="field">
        <label className="field-label" htmlFor="notes">Notes</label>
        <textarea id="notes" className="textarea" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      <Button type="submit" loading={submitting} disabled={!name.trim()}>
        {submitting ? "Saving…" : "Save"}
      </Button>
    </form>
  );
}
