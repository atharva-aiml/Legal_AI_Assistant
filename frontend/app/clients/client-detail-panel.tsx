"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { EditClientModal } from "./[id]/edit-client-modal";
import { NewMatterModal } from "./[id]/new-matter-modal";

type Client = { id: string; name: string; contactEmail: string | null; contactPhone: string | null; notes: string | null; createdAt: string };
type ClientSummary = { id: string; name: string };
type Matter = { id: string; title: string; status: "open" | "closed" };
type Deadline = { id: string; matterId: string; dueDate: string; status: "open" | "complete" };

function formatDueDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/**
 * Same content as /clients/[id]/page.tsx, minus the Breadcrumb (redundant
 * inline under the list) — fetched client-side so selecting a client from
 * the master list never navigates away from /clients.
 */
export function ClientDetailPanel({ clientId }: { clientId: string }) {
  const [client, setClient] = useState<Client | null>(null);
  const [matters, setMatters] = useState<Matter[]>([]);
  const [allClients, setAllClients] = useState<ClientSummary[]>([]);
  const [nextDeadlineByMatter, setNextDeadlineByMatter] = useState<Map<string, string>>(new Map());
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");

    async function load() {
      const [clientRes, mattersRes, deadlinesRes, clientsRes] = await Promise.all([
        fetch(`${JAVA_API_URL_PUBLIC}/api/clients/${clientId}`, { credentials: "include" }),
        fetch(`${JAVA_API_URL_PUBLIC}/api/matters?clientId=${clientId}`, { credentials: "include" }),
        fetch(`${JAVA_API_URL_PUBLIC}/api/deadlines/upcoming?days=36500`, { credentials: "include" }),
        // NewMatterModal's Client combobox needs the full list, same as /matters/new.
        fetch(`${JAVA_API_URL_PUBLIC}/api/clients`, { credentials: "include" }),
      ]);
      if (cancelled) return;
      if (!clientRes.ok) {
        setStatus("error");
        return;
      }
      const { client: fetchedClient }: { client: Client } = await clientRes.json();
      const { matters: fetchedMatters }: { matters: Matter[] } = mattersRes.ok ? await mattersRes.json() : { matters: [] };
      const { deadlines }: { deadlines: Deadline[] } = deadlinesRes.ok ? await deadlinesRes.json() : { deadlines: [] };
      const { clients: fetchedClients }: { clients: ClientSummary[] } = clientsRes.ok ? await clientsRes.json() : { clients: [] };

      const matterIds = new Set(fetchedMatters.map((m) => m.id));
      const nextDeadline = new Map<string, string>();
      for (const d of deadlines) {
        if (!matterIds.has(d.matterId)) continue;
        const current = nextDeadline.get(d.matterId);
        if (!current || d.dueDate < current) nextDeadline.set(d.matterId, d.dueDate);
      }

      if (cancelled) return;
      setClient(fetchedClient);
      setMatters(fetchedMatters);
      setAllClients(fetchedClients);
      setNextDeadlineByMatter(nextDeadline);
      setStatus("ok");
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [clientId, refreshTick]);

  if (status === "loading") {
    return <div className="card text-secondary">Loading…</div>;
  }
  if (status === "error" || !client) {
    return <ErrorBanner>Couldn&apos;t load this client — retry.</ErrorBanner>;
  }

  return (
    <div className="client-detail-panel">
      <div className="row-between">
        <h1 style={{ fontSize: "var(--font-size-2xl)" }}>{client.name}</h1>
        <EditClientModal client={client} onSaved={() => setRefreshTick((t) => t + 1)} />
      </div>

      <div className="card" style={{ marginTop: "var(--space-4)" }}>
        <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "var(--space-4)" }}>
          <div>
            <dt className="field-label" style={{ marginBottom: "var(--space-1)" }}>Contact email</dt>
            <dd style={{ margin: 0 }}>{client.contactEmail || "—"}</dd>
          </div>
          <div>
            <dt className="field-label" style={{ marginBottom: "var(--space-1)" }}>Contact phone</dt>
            <dd style={{ margin: 0 }}>{client.contactPhone || "—"}</dd>
          </div>
          <div>
            <dt className="field-label" style={{ marginBottom: "var(--space-1)" }}>Added</dt>
            <dd style={{ margin: 0 }}>{new Date(client.createdAt).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}</dd>
          </div>
          {client.notes && (
            <div style={{ gridColumn: "1 / -1" }}>
              <dt className="field-label" style={{ marginBottom: "var(--space-1)" }}>Notes</dt>
              <dd style={{ margin: 0, whiteSpace: "pre-wrap" }}>{client.notes}</dd>
            </div>
          )}
        </dl>
      </div>

      <div className="section-header">
        <h2 style={{ fontSize: "var(--font-size-xl)" }}>Matters</h2>
        <NewMatterModal clientId={client.id} clients={allClients} />
      </div>

      {matters.length === 0 ? (
        <EmptyState title="No matters yet" body="Open the first Matter for this client to start uploading documents." action={<NewMatterModal clientId={client.id} clients={allClients} />} />
      ) : (
        <div className="stack">
          {matters.map((matter) => {
            const nextDeadline = nextDeadlineByMatter.get(matter.id);
            return (
              <Link key={matter.id} href={`/matters/${matter.id}`} className="card">
                <div className="row-between">
                  <div style={{ fontWeight: 500 }}>{matter.title}</div>
                  <div className="row" style={{ gap: "var(--space-3)" }}>
                    {nextDeadline && <span className="text-tertiary text-sm mono">Due {formatDueDate(nextDeadline)}</span>}
                    <StatusBadge status={matter.status} />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
