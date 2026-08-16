"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";

export default function NewClientPage() {
  const router = useRouter();
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

    router.push("/clients");
    router.refresh();
  }

  return (
    <main className="page" style={{ maxWidth: 480 }}>
      <Link href="/clients" className="text-sm">
        ← Clients
      </Link>
      <h1 style={{ fontSize: "var(--font-size-2xl)", margin: "var(--space-3) 0 var(--space-4)" }}>New Client</h1>
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
    </main>
  );
}
