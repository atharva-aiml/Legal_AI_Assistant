"use client";

import { useEffect, useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";
import { StatusBadge } from "@/components/status-badge";
import { SortDropdown } from "@/components/sort-dropdown";
import { initials } from "@/lib/initials";
import { usePersistedState } from "@/lib/use-persisted-state";

type Matter = { id: string; title: string; status: "open" | "closed"; clientId: string; updatedAt: string };
type Client = { id: string; name: string };
type Deadline = { id: string; matterId: string; dueDate: string; status: "open" | "complete" };
type SortMode = "default" | "nextDeadline" | "recentActivity";
type ViewMode = "list" | "board";

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "default", label: "Default order" },
  { value: "nextDeadline", label: "Next deadline" },
  { value: "recentActivity", label: "Recent activity" },
];

function formatDueDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function StatusFilterIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 5h16M7 12h10M10 19h4" />
    </svg>
  );
}

function ClientFilterIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 20c0-3.6 3.1-6.5 7-6.5s7 2.9 7 6.5" />
    </svg>
  );
}

function SortOrderIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 6v13M7 19l-3-3M7 19l3-3" />
      <path d="M17 18V5M17 5l-3 3M17 5l3 3" />
    </svg>
  );
}

function ListViewIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

function BoardViewIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3.5" y="4.5" width="17" height="15" rx="2" />
      <path d="M10.5 4.5v15M15.5 4.5v15" />
    </svg>
  );
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
      className={`matter-row${selected ? " card-selected" : ""}`}
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
  const [sortMode, setSortMode] = usePersistedState<SortMode>("matters:sortMode", "default");
  const [viewMode, setViewMode] = usePersistedState<ViewMode>("matters:viewMode", "list");

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
    try {
      sessionStorage.setItem("matters:filters", JSON.stringify({ status, clientId }));
    } catch {}
  }

  // A plain "Matters" nav click (no query string at all) should restore
  // whatever status/Client filter was last remembered, rather than always
  // resetting to "all matters" — but a URL that already specifies a filter
  // (including an explicit "clear filters" navigation) must win as-is.
  useEffect(() => {
    if (currentStatus !== "" || currentClientId !== "") return;
    try {
      const raw = sessionStorage.getItem("matters:filters");
      if (!raw) return;
      const remembered = JSON.parse(raw) as { status?: string; clientId?: string };
      const rememberedStatus = remembered.status ?? "";
      const rememberedClientId = remembered.clientId ?? "";
      if (rememberedStatus || rememberedClientId) {
        navigateWithFilters(rememberedStatus, rememberedClientId);
      }
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sortedMatters = useMemo(() => {
    if (sortMode === "nextDeadline") {
      return [...matters].sort((a, b) => {
        const aDate = nextDeadlineByMatter.get(a.id) ?? "9999-12-31";
        const bDate = nextDeadlineByMatter.get(b.id) ?? "9999-12-31";
        return aDate.localeCompare(bDate);
      });
    }
    if (sortMode === "recentActivity") {
      return [...matters].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
    }
    return matters;
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
            icon={<StatusFilterIcon />}
            iconOnly
          />
          <SortDropdown
            value={currentClientId}
            options={clientOptions}
            onChange={(clientId) => navigateWithFilters(currentStatus, clientId)}
            menuLabel="Filter by Client"
            align="left"
            icon={<ClientFilterIcon />}
            iconOnly
          />
          <SortDropdown
            value={sortMode}
            options={SORT_OPTIONS}
            onChange={setSortMode}
            menuLabel="Sort Matters by"
            align="left"
            icon={<SortOrderIcon />}
            iconOnly
          />
        </div>

        {/* I-26: a toggle, not a replacement -- list view stays the default. */}
        <div className="row" role="group" aria-label="View" style={{ gap: 0 }}>
          <button
            type="button"
            className={viewMode === "list" ? "btn btn-secondary btn-sm" : "btn btn-ghost btn-sm"}
            aria-pressed={viewMode === "list"}
            aria-label="List view"
            title="List view"
            onClick={() => setViewMode("list")}
          >
            <ListViewIcon />
          </button>
          <button
            type="button"
            className={viewMode === "board" ? "btn btn-secondary btn-sm" : "btn btn-ghost btn-sm"}
            aria-pressed={viewMode === "board"}
            aria-label="Board view"
            title="Board view"
            onClick={() => setViewMode("board")}
          >
            <BoardViewIcon />
          </button>
        </div>
      </div>

      <div className="master-detail-col-scroll">
        {sortedMatters.length === 0 ? (
          <div className="card text-secondary">No matters match these filters.</div>
        ) : viewMode === "list" ? (
          <div className="stack" style={{ gap: "var(--space-1)" }}>
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
              <div className="stack" style={{ gap: "var(--space-1)" }}>
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
              <div className="stack" style={{ gap: "var(--space-1)" }}>
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
