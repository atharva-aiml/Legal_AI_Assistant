"use client";

import { useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { StatusBadge } from "@/components/status-badge";
import { SortDropdown } from "@/components/sort-dropdown";
import { initials } from "@/lib/initials";

type Matter = { id: string; title: string; status: "open" | "closed"; clientId: string };
type Client = { id: string; name: string };
type Deadline = { id: string; matterId: string; dueDate: string; status: "open" | "complete" };
type SortMode = "default" | "nextDeadline";
type ViewMode = "list" | "board";

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "default", label: "Default order" },
  { value: "nextDeadline", label: "Next deadline" },
];

function formatDueDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function MatterRow({
  matter,
  clientName,
  nextDeadline,
  selected,
  onSelect,
}: {
  matter: Matter;
  clientName: string | undefined;
  nextDeadline: string | undefined;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(matter.id)}
      aria-current={selected ? "true" : undefined}
      className={`card matter-row${selected ? " card-selected" : ""}`}
    >
      <div className="row-between">
        <div className="row" style={{ gap: "var(--space-3)" }}>
          <span className="matter-avatar matter-row-avatar">{initials(matter.title)}</span>
          <div>
            <div className="matter-row-name" style={{ fontWeight: 500 }}>{matter.title}</div>
            <div className="text-tertiary text-sm">{clientName}</div>
          </div>
        </div>
        <div className="row" style={{ gap: "var(--space-3)" }}>
          {/* I-25: always shown, not just while sorted by it. */}
          <span className="text-tertiary text-sm mono">{nextDeadline ? `Due ${formatDueDate(nextDeadline)}` : "No deadlines"}</span>
          <StatusBadge status={matter.status} />
        </div>
      </div>
    </button>
  );
}

/**
 * I-23: status/Client filters are server-driven (via the URL's query string,
 * so the Java backend does the actual filtering) — this component just
 * renders whatever `matters` it's handed and updates the URL on change.
 * I-24: "sort by next deadline" is a pure client-side re-order of that
 * already-filtered list, no extra round trip.
 * I-25: every row shows its next-deadline date (or "No deadlines"), always.
 * I-26: a List/Board view toggle over the same already-filtered/sorted data.
 */
export function MattersList({
  matters,
  clients,
  deadlines,
  currentStatus,
  currentClientId,
  selectedMatterId,
  onSelectMatter,
}: {
  matters: Matter[];
  clients: Client[];
  deadlines: Deadline[];
  currentStatus: string;
  currentClientId: string;
  selectedMatterId: string | null;
  onSelectMatter: (id: string) => void;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [sortMode, setSortMode] = useState<SortMode>("default");
  const [viewMode, setViewMode] = useState<ViewMode>("list");

  const clientNameById = useMemo(() => new Map(clients.map((c) => [c.id, c.name])), [clients]);

  // /api/deadlines/upcoming initially returns only status=open ones, but this
  // list is now kept live from the detail panel's own complete-toggle too
  // (see MattersMasterDetail), so a completed deadline can show up here in
  // the same array — filter explicitly rather than relying on the fetch scope.
  const nextDeadlineByMatter = useMemo(() => {
    const map = new Map<string, string>();
    for (const d of deadlines) {
      if (d.status !== "open") continue;
      const current = map.get(d.matterId);
      if (!current || d.dueDate < current) map.set(d.matterId, d.dueDate);
    }
    return map;
  }, [deadlines]);

  function navigateWithFilters(status: string, clientId: string) {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (clientId) params.set("clientId", clientId);
    router.push(params.toString() ? `${pathname}?${params}` : pathname);
  }

  const sortedMatters = useMemo(() => {
    if (sortMode !== "nextDeadline") return matters;
    return [...matters].sort((a, b) => {
      const aDate = nextDeadlineByMatter.get(a.id) ?? "9999-12-31";
      const bDate = nextDeadlineByMatter.get(b.id) ?? "9999-12-31";
      return aDate.localeCompare(bDate);
    });
  }, [matters, sortMode, nextDeadlineByMatter]);

  const openMatters = useMemo(() => sortedMatters.filter((m) => m.status === "open"), [sortedMatters]);
  const closedMatters = useMemo(() => sortedMatters.filter((m) => m.status === "closed"), [sortedMatters]);

  const statusOptions = [
    { value: "", label: "All statuses" },
    { value: "open", label: "Open" },
    { value: "closed", label: "Closed" },
  ];
  const clientOptions = [{ value: "", label: "All clients" }, ...clients.map((c) => ({ value: c.id, label: c.name }))];

  return (
    <>
      <div className="row-between master-detail-col-header" style={{ marginBottom: "var(--space-4)", flexWrap: "wrap", gap: "var(--space-3)" }}>
        <div className="row" style={{ gap: "var(--space-3)", flexWrap: "wrap" }}>
          <SortDropdown
            value={currentStatus}
            options={statusOptions}
            onChange={(status) => navigateWithFilters(status, currentClientId)}
            menuLabel="Filter by status"
            align="left"
          />
          <SortDropdown
            value={currentClientId}
            options={clientOptions}
            onChange={(clientId) => navigateWithFilters(currentStatus, clientId)}
            menuLabel="Filter by Client"
            align="left"
          />
          <SortDropdown value={sortMode} options={SORT_OPTIONS} onChange={setSortMode} menuLabel="Sort Matters by" align="left" />
        </div>

        {/* I-26: a toggle, not a replacement -- list view stays the default. */}
        <div className="row" role="group" aria-label="View" style={{ gap: 0 }}>
          <button
            type="button"
            className={viewMode === "list" ? "btn btn-secondary btn-sm" : "btn btn-ghost btn-sm"}
            aria-pressed={viewMode === "list"}
            onClick={() => setViewMode("list")}
          >
            List
          </button>
          <button
            type="button"
            className={viewMode === "board" ? "btn btn-secondary btn-sm" : "btn btn-ghost btn-sm"}
            aria-pressed={viewMode === "board"}
            onClick={() => setViewMode("board")}
          >
            Board
          </button>
        </div>
      </div>

      <div className="master-detail-col-scroll">
        {sortedMatters.length === 0 ? (
          <div className="card text-secondary">No matters match these filters.</div>
        ) : viewMode === "list" ? (
          <div className="stack">
            {sortedMatters.map((matter) => (
              <MatterRow
                key={matter.id}
                matter={matter}
                clientName={clientNameById.get(matter.clientId)}
                nextDeadline={nextDeadlineByMatter.get(matter.id)}
                selected={matter.id === selectedMatterId}
                onSelect={onSelectMatter}
              />
            ))}
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "var(--space-4)", alignItems: "start" }}>
            <div>
              <h2 style={{ fontSize: "var(--font-size-lg)", margin: "0 0 var(--space-3)" }}>Open ({openMatters.length})</h2>
              <div className="stack">
                {openMatters.length === 0 ? (
                  <div className="card text-secondary">No open Matters.</div>
                ) : (
                  openMatters.map((matter) => (
                    <MatterRow
                      key={matter.id}
                      matter={matter}
                      clientName={clientNameById.get(matter.clientId)}
                      nextDeadline={nextDeadlineByMatter.get(matter.id)}
                      selected={matter.id === selectedMatterId}
                      onSelect={onSelectMatter}
                    />
                  ))
                )}
              </div>
            </div>
            <div>
              <h2 style={{ fontSize: "var(--font-size-lg)", margin: "0 0 var(--space-3)" }}>Closed ({closedMatters.length})</h2>
              <div className="stack">
                {closedMatters.length === 0 ? (
                  <div className="card text-secondary">No closed Matters.</div>
                ) : (
                  closedMatters.map((matter) => (
                    <MatterRow
                      key={matter.id}
                      matter={matter}
                      clientName={clientNameById.get(matter.clientId)}
                      nextDeadline={nextDeadlineByMatter.get(matter.id)}
                      selected={matter.id === selectedMatterId}
                      onSelect={onSelectMatter}
                    />
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
