"use client";

import { useEffect, useRef } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import { usePersistedState } from "@/lib/use-persisted-state";
import { ClientsList } from "./clients-list";
import { ClientDetailPanel } from "./client-detail-panel";

type Client = { id: string; name: string; contactEmail: string | null };
type Matter = { id: string; clientId: string; status: "open" | "closed"; updatedAt: string };

/**
 * Master-detail layout for /clients: the list stays narrow on the left,
 * and clicking a client renders its full detail (same content as
 * /clients/[id], fetched client-side) on the right — no navigation, no
 * losing your place in the list. The standalone /clients/[id] route is
 * untouched, so direct links/bookmarks to a client still work.
 */
export function ClientsMasterDetail({ clients, matters }: { clients: Client[]; matters: Matter[] }) {
  const [selectedClientId, setSelectedClientId] = usePersistedState<string | null>("clients:selectedClientId", null);
  const panelColRef = useRef<HTMLDivElement>(null);

  // .master-detail-panel-col itself is never remounted (only its child, via
  // `key`, when the selected client changes) — its scroll position otherwise
  // carries over from whatever client was being viewed before.
  useEffect(() => {
    if (panelColRef.current) panelColRef.current.scrollTop = 0;
  }, [selectedClientId]);

  return (
    <div className="master-detail-grid">
      <div className="master-detail-list">
        <ClientsList clients={clients} matters={matters} selectedClientId={selectedClientId} onSelectClient={setSelectedClientId} />
      </div>
      <div className="master-detail-panel-col" ref={panelColRef}>
        {selectedClientId ? (
          <ClientDetailPanel key={selectedClientId} clientId={selectedClientId} onDeleted={() => setSelectedClientId(null)} />
        ) : (
          <EmptyState title="Select a client" body="Pick a client from the list to see their details, contact info, and Matters here." />
        )}
      </div>
    </div>
  );
}
