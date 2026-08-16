"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";

type Client = { id: string; name: string };

export function NewMatterForm({ clients, initialClientId }: { clients: Client[]; initialClientId?: string }) {
  const router = useRouter();
  const [clientId, setClientId] = useState(initialClientId ?? clients[0]?.id ?? "");
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ client_id: clientId, title }),
    });

    if (!res.ok) {
      setSubmitting(false);
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't save this matter — retry.");
      return;
    }

    const created = await res.json();
    router.push(`/matters/${created.id}`);
    router.refresh();
  }

  if (clients.length === 0) {
    return (
      <EmptyState
        title="No clients yet"
        body="A Matter always belongs to a Client — create one first."
        action={<Button href="/clients/new">+ New Client</Button>}
      />
    );
  }

  return (
    <form onSubmit={handleSubmit} className="card stack-4">
      <div className="field">
        <label className="field-label" htmlFor="clientId">Client *</label>
        <select id="clientId" className="select" value={clientId} onChange={(e) => setClientId(e.target.value)} required>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label className="field-label" htmlFor="title">Matter title *</label>
        <input id="title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} required autoFocus />
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      <Button type="submit" loading={submitting} disabled={!title.trim() || !clientId}>
        {submitting ? "Saving…" : "Save"}
      </Button>
    </form>
  );
}
