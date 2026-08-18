"use client";

import { useState } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import { MattersList } from "./matters-list";
import { MatterDetailPanel } from "./matter-detail-panel";

type Matter = { id: string; title: string; status: "open" | "closed"; clientId: string };
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
  deadlines,
  currentStatus,
  currentClientId,
}: {
  matters: Matter[];
  clients: Client[];
  deadlines: Deadline[];
  currentStatus: string;
  currentClientId: string;
}) {
  const [selectedMatterId, setSelectedMatterId] = useState<string | null>(null);

  return (
    <div className="master-detail-grid">
      <div className="master-detail-list">
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
      <div className="master-detail-panel-col">
        {selectedMatterId ? (
          <MatterDetailPanel key={selectedMatterId} matterId={selectedMatterId} />
        ) : (
          <EmptyState title="Select a Matter" body="Pick a Matter from the list to see its Documents, Chat, and Deadlines here." />
        )}
      </div>
    </div>
  );
}
