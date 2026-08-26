"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { EmptyState } from "@/components/ui/empty-state";
import { usePersistedState } from "@/lib/use-persisted-state";
import { NewMatterModal } from "@/app/clients/[id]/new-matter-modal";
import { MattersList } from "./matters-list";
import { MatterDetailPanel } from "./matter-detail-panel";

type Matter = { id: string; title: string; status: "open" | "closed"; clientId: string; updatedAt: string };
type Client = { id: string; name: string };
type Deadline = { id: string; matterId: string; dueDate: string; status: "open" | "complete" };

/**
 * Master-detail layout for /matters, same pattern as /clients: the list
 * stays narrow on the left, and clicking a Matter renders its full detail
 * (same content as /matters/[id], fetched client-side — Documents, Chat,
 * Deadlines, Activity, Draft generation) on the right. The standalone
 * /matters/[id] route is untouched, so direct links/bookmarks still work.
 */
export function MattersMasterDetail({
  matters,
  clients,
  deadlines: initialDeadlines,
  currentStatus,
  currentClientId,
  initialSelectedMatterId,
}: {
  matters: Matter[];
  clients: Client[];
  deadlines: Deadline[];
  currentStatus: string;
  currentClientId: string;
  /** From /matters?selected={id} — links elsewhere in the app (dashboard cards, a Client's Matter list, etc.) land here with a Matter pre-opened instead of the discarded standalone /matters/{id} page. */
  initialSelectedMatterId?: string | null;
}) {
  const router = useRouter();
  const [selectedMatterId, setSelectedMatterId] = usePersistedState<string | null>(
    "matters:selectedMatterId",
    initialSelectedMatterId ?? null
  );
  const panelColRef = useRef<HTMLDivElement>(null);

  // A URL-driven selection (e.g. a dashboard link to /matters?selected={id})
  // must win over whatever was previously remembered, AND become the new
  // remembered selection for the next plain-nav-click return to /matters.
  useEffect(() => {
    if (initialSelectedMatterId) setSelectedMatterId(initialSelectedMatterId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialSelectedMatterId]);

  // The Matter list itself is server-fetched (app/matters/page.tsx), unlike
  // client-detail-panel.tsx's own client-side matters fetch — deleting needs
  // a real router.refresh() for the deleted tile to actually disappear from
  // the left list, not just deselecting the now-gone Matter's panel.
  function handleMatterDeleted() {
    setSelectedMatterId(null);
    router.refresh();
  }

  // Lifted into local state (rather than read straight from the prop) so the
  // detail panel's own deadline-checkbox toggle can patch it in place and
  // have the affected Matter's tile update immediately, without a full page
  // reload. Re-synced whenever the server hands down a fresh array (a status/
  // Client filter change navigates and re-fetches server-side).
  const [deadlines, setDeadlines] = useState(initialDeadlines);
  useEffect(() => {
    setDeadlines(initialDeadlines);
  }, [initialDeadlines]);

  function handleDeadlineChange(updated: Deadline) {
    setDeadlines((prev) => prev.map((d) => (d.id === updated.id ? { ...d, ...updated } : d)));
  }

  // .master-detail-panel-col itself is never remounted (only its child, via
  // `key`, when the selected Matter changes) — its scroll position otherwise
  // carries over from whatever Matter was being viewed before.
  useEffect(() => {
    if (panelColRef.current) panelColRef.current.scrollTop = 0;
  }, [selectedMatterId]);

  return (
    <div className="master-detail-grid">
      <div className="master-detail-list">
        {/* First child of this column, matching MatterDetailPanel's own title
            row exactly (same font-size, zero-margin h1) so the two line up
            with align-items: start on .master-detail-grid. Stays fixed (not
            part of the scrolling tile area below) along with MattersList's
            own filter/sort/view-toggle row. */}
        <div className="row-between master-detail-col-header" style={{ marginBottom: "var(--space-4)" }}>
          <h1 style={{ fontSize: "var(--font-size-2xl)" }}>Matters</h1>
          <NewMatterModal clients={clients} buttonClassName="btn-hold-bg btn-xs" />
        </div>
        <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
          <MattersList
            matters={matters}
            clients={clients}
            deadlines={deadlines}
            currentStatus={currentStatus}
            currentClientId={currentClientId}
            selectedMatterId={selectedMatterId}
            onSelectMatter={setSelectedMatterId}
          />
        </div>
      </div>
      <div className="master-detail-panel-col" ref={panelColRef}>
        {selectedMatterId ? (
          <MatterDetailPanel key={selectedMatterId} matterId={selectedMatterId} onDeadlineChange={handleDeadlineChange} onDeleted={handleMatterDeleted} />
        ) : (
          <EmptyState title="Select a Matter" body="Pick a Matter from the list to see its Documents, Chat, and Deadlines here." />
        )}
      </div>
    </div>
  );
}
