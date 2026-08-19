"use client";

import { useMemo, useState } from "react";
import { useListSearch } from "@/components/list-search-context";
import { SortDropdown } from "@/components/sort-dropdown";
import { initials } from "@/lib/initials";

type Client = { id: string; name: string; contactEmail: string | null };
type Matter = { id: string; clientId: string; status: "open" | "closed"; updatedAt: string };
type SortMode = "name" | "recent" | "openMatters";

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "name", label: "Name (A–Z)" },
  { value: "recent", label: "Most recent activity" },
  { value: "openMatters", label: "Most open Matters" },
];

/**
 * I-13/I-14: pure client-side filter + sort over the already-fetched list —
 * no network call, no page reload. The filter query itself now comes from
 * the topbar search bar (NavBar, in its in-list-filter mode on this route)
 * via ListSearchContext, not a separate input on this page.
 */
export function ClientsList({
  clients,
  matters,
  selectedClientId,
  onSelectClient,
}: {
  clients: Client[];
  matters: Matter[];
  selectedClientId: string | null;
  onSelectClient: (id: string) => void;
}) {
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
      <div className="row master-detail-col-header" style={{ gap: "var(--space-3)", marginBottom: "var(--space-4)", flexWrap: "wrap" }}>
        <SortDropdown value={sortMode} options={SORT_OPTIONS} onChange={setSortMode} menuLabel="Sort clients by" align="left" />
      </div>

      <div className="master-detail-col-scroll">
        {sortedClients.length === 0 ? (
          <div key={query} className="card text-secondary client-empty-fade">No clients match &quot;{query.trim()}&quot;.</div>
        ) : (
          <div className="stack">
            {sortedClients.map((c) => {
              const counts = matterCounts.get(c.id) ?? { open: 0, closed: 0 };
              const selected = c.id === selectedClientId;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => onSelectClient(c.id)}
                  aria-current={selected ? "true" : undefined}
                  className={`card client-row${selected ? " card-selected" : ""}`}
                >
                  <div className="row-between">
                    <div className="row" style={{ gap: "var(--space-3)" }}>
                      <span className="matter-avatar client-row-avatar">{initials(c.name)}</span>
                      <div>
                        <div className="client-row-name" style={{ fontWeight: 500 }}>{c.name}</div>
                        {c.contactEmail && <div className="text-tertiary text-sm">{c.contactEmail}</div>}
                      </div>
                    </div>
                    <div className="text-tertiary text-sm">
                      {counts.open + counts.closed === 0
                        ? "No matters"
                        : `${counts.open} open · ${counts.closed} closed`}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
