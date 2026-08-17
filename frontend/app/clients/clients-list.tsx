"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useListSearch } from "@/components/list-search-context";

type Client = { id: string; name: string; contactEmail: string | null };
type Matter = { id: string; clientId: string; status: "open" | "closed"; updatedAt: string };
type SortMode = "name" | "recent" | "openMatters";

/**
 * I-13/I-14: pure client-side filter + sort over the already-fetched list —
 * no network call, no page reload. The filter query itself now comes from
 * the topbar search bar (NavBar, in its in-list-filter mode on this route)
 * via ListSearchContext, not a separate input on this page.
 */
export function ClientsList({ clients, matters }: { clients: Client[]; matters: Matter[] }) {
  const { query } = useListSearch();
  const [sortMode, setSortMode] = useState<SortMode>("name");

  const matterCounts = useMemo(() => {
    const counts = new Map<string, { open: number; closed: number }>();
    for (const m of matters) {
      const entry = counts.get(m.clientId) ?? { open: 0, closed: 0 };
      if (m.status === "open") entry.open++;
      else entry.closed++;
      counts.set(m.clientId, entry);
    }
    return counts;
  }, [matters]);

  // I-14's "most recent activity" reuses I-16's definition: max(matter.updatedAt)
  // across a Client's Matters. ISO 8601 timestamps compare correctly as plain
  // strings, so no Date parsing is needed. A Client with no Matters has no
  // activity and sorts last, not first.
  const lastActivityByClient = useMemo(() => {
    const latest = new Map<string, string>();
    for (const m of matters) {
      const current = latest.get(m.clientId);
      if (!current || m.updatedAt > current) latest.set(m.clientId, m.updatedAt);
    }
    return latest;
  }, [matters]);

  const filteredClients = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) return clients;
    return clients.filter((c) => c.name.toLowerCase().includes(trimmed));
  }, [clients, query]);

  const sortedClients = useMemo(() => {
    return [...filteredClients].sort((a, b) => {
      if (sortMode === "recent") {
        const aActivity = lastActivityByClient.get(a.id) ?? "";
        const bActivity = lastActivityByClient.get(b.id) ?? "";
        if (aActivity !== bActivity) return bActivity.localeCompare(aActivity);
      } else if (sortMode === "openMatters") {
        const aOpen = matterCounts.get(a.id)?.open ?? 0;
        const bOpen = matterCounts.get(b.id)?.open ?? 0;
        if (aOpen !== bOpen) return bOpen - aOpen;
      }
      return a.name.localeCompare(b.name); // default order, and the tiebreak for the other two modes
    });
  }, [filteredClients, sortMode, lastActivityByClient, matterCounts]);

  return (
    <>
      <div className="row" style={{ gap: "var(--space-3)", marginBottom: "var(--space-4)", flexWrap: "wrap" }}>
        <div className="field" style={{ maxWidth: 220, marginBottom: 0 }}>
          <label className="field-label" htmlFor="client-sort" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
            Sort clients by
          </label>
          <select id="client-sort" className="select" value={sortMode} onChange={(e) => setSortMode(e.target.value as SortMode)}>
            <option value="name">Name (A–Z)</option>
            <option value="recent">Most recent activity</option>
            <option value="openMatters">Most open Matters</option>
          </select>
        </div>
      </div>

      {sortedClients.length === 0 ? (
        <div className="card text-secondary">No clients match &quot;{query.trim()}&quot;.</div>
      ) : (
        <div className="stack">
          {sortedClients.map((c) => {
            const counts = matterCounts.get(c.id) ?? { open: 0, closed: 0 };
            return (
              <Link key={c.id} href={`/clients/${c.id}`} className="card">
                <div className="row-between">
                  <div>
                    <div style={{ fontWeight: 500 }}>{c.name}</div>
                    {c.contactEmail && <div className="text-tertiary text-sm">{c.contactEmail}</div>}
                  </div>
                  <div className="text-tertiary text-sm">
                    {counts.open + counts.closed === 0
                      ? "No matters"
                      : `${counts.open} open · ${counts.closed} closed`}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </>
  );
}
