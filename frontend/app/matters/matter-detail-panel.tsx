"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { StatusBadge } from "@/components/status-badge";
import { ErrorBanner } from "@/components/ui/error-banner";
import { DocumentUpload } from "./[id]/document-upload";
import { DocumentsList } from "./[id]/documents-list";
import { ChatPanel } from "./[id]/chat-panel";
import { DeadlinesList } from "./[id]/deadlines-list";
import { NewDeadlineForm } from "./[id]/new-deadline-form";
import { CloseMatterButton } from "./[id]/close-matter-button";
import { ReopenMatterButton } from "./[id]/reopen-matter-button";
import { GenerateDraftModal } from "./[id]/generate-draft-modal";

type Matter = { id: string; title: string; status: "open" | "closed" };
type Client = { id: string; name: string };
type Doc = {
  id: string;
  fileName: string;
  mimeType: string;
  sizeBytes: number;
  status: "uploading" | "processing" | "ready" | "failed";
  isDraft: boolean;
  errorMessage: string | null;
  createdAt: string;
};
type Citation = { id: string; documentId: string | null; fileName: string | null; pageNumber: number | null; excerpt: string | null };
type ChatMsg = { id: string; role: "user" | "assistant"; content: string; createdAt: string; citations: Citation[]; lowConfidence: boolean | null; pinned: boolean };
type Deadline = {
  id: string;
  matterId: string;
  title: string;
  dueDate: string;
  status: "open" | "complete";
  priority: "standard" | "critical";
  notificationLeadDays: number;
};
type ActivityEntry = { type: "document" | "deadline" | "chat"; title: string; timestamp: string };

const ACTIVITY_LABEL: Record<ActivityEntry["type"], string> = { document: "Document", deadline: "Deadline", chat: "Chat" };

function formatActivityTimestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
}

/**
 * Same content as /matters/[id]/page.tsx, minus the Breadcrumb (redundant
 * inline under the list) and the sticky title bar (the page's own header
 * already pins) — fetched client-side so selecting a Matter from the master
 * list never navigates away from /matters. Every mutating child (Close/Reopen,
 * Generate Document, New Deadline, Deadline complete-toggle, Document upload)
 * gets `onUpdated` wired to refetch instead of their default router.refresh().
 */
export function MatterDetailPanel({ matterId }: { matterId: string }) {
  const [matter, setMatter] = useState<Matter | null>(null);
  const [client, setClient] = useState<Client | null>(null);
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");

    async function load() {
      const matterRes = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}`, { credentials: "include" });
      if (cancelled) return;
      if (!matterRes.ok) {
        setStatus("error");
        return;
      }
      const { matter: fetchedMatter, client: fetchedClient }: { matter: Matter; client: Client | null } = await matterRes.json();

      // I-07: Recent Matters is a nice-to-have widget — a failed view-record must never break this panel.
      fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/view`, { method: "POST", credentials: "include" }).catch(() => {});

      const [documentsRes, chatRes, deadlinesRes, activityRes] = await Promise.all([
        fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/documents`, { credentials: "include" }),
        fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/chat`, { credentials: "include" }),
        fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/deadlines`, { credentials: "include" }),
        fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/activity`, { credentials: "include" }),
      ]);
      if (cancelled) return;

      const { documents: fetchedDocuments }: { documents: Doc[] } = documentsRes.ok ? await documentsRes.json() : { documents: [] };
      const { messages: fetchedMessages }: { messages: ChatMsg[] } = chatRes.ok ? await chatRes.json() : { messages: [] };
      const { deadlines: fetchedDeadlines }: { deadlines: Deadline[] } = deadlinesRes.ok ? await deadlinesRes.json() : { deadlines: [] };
      const { entries: fetchedActivity }: { entries: ActivityEntry[] } = activityRes.ok ? await activityRes.json() : { entries: [] };

      if (cancelled) return;
      setMatter(fetchedMatter);
      setClient(fetchedClient);
      setDocuments(fetchedDocuments);
      setMessages(fetchedMessages);
      setDeadlines(fetchedDeadlines);
      setActivity(fetchedActivity);
      setStatus("ok");
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [matterId, refreshTick]);

  function refetch() {
    setRefreshTick((t) => t + 1);
  }

  if (status === "loading") {
    return <div className="card text-secondary">Loading…</div>;
  }
  if (status === "error" || !matter) {
    return <ErrorBanner>Couldn&apos;t load this matter — retry.</ErrorBanner>;
  }

  const hasReadyDocuments = documents.some((d) => d.status === "ready");

  return (
    <div className="matter-detail-panel">
      <div className="row-between">
        <h1 style={{ fontSize: "var(--font-size-2xl)" }}>{matter.title}</h1>
        <StatusBadge status={matter.status} />
      </div>
      {client && (
        <div className="text-tertiary text-sm" style={{ marginTop: "var(--space-2)" }}>
          Client: <Link href={`/clients/${client.id}`}>{client.name}</Link>
        </div>
      )}

      {activity.length > 0 && (
        <section aria-labelledby="panel-activity-heading" style={{ marginTop: "var(--space-4)" }}>
          <h2 id="panel-activity-heading" style={{ fontSize: "var(--font-size-base)", fontWeight: 600, margin: "0 0 var(--space-2)" }}>
            Activity
          </h2>
          <div className="card" style={{ padding: "var(--space-1) var(--space-3)", maxHeight: 200, overflowY: "auto" }}>
            {activity.map((entry, i) => (
              <div
                key={i}
                className="row-between"
                style={{
                  gap: "var(--space-3)",
                  padding: "var(--space-2) 0",
                  borderBottom: i < activity.length - 1 ? "1px solid var(--color-border-default)" : "none",
                }}
              >
                <div className="row" style={{ gap: "var(--space-2)", minWidth: 0 }}>
                  <span className="text-tertiary text-xs" style={{ textTransform: "uppercase", letterSpacing: "0.04em", flexShrink: 0 }}>
                    {ACTIVITY_LABEL[entry.type]}
                  </span>
                  <span className="text-sm" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {entry.title}
                  </span>
                </div>
                <span className="text-tertiary text-xs mono" style={{ flexShrink: 0 }}>{formatActivityTimestamp(entry.timestamp)}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section id="panel-deadlines" aria-labelledby="panel-deadlines-heading" style={{ marginTop: "var(--space-5)" }}>
        <div className="section-header">
          <h2 id="panel-deadlines-heading" style={{ fontSize: "var(--font-size-xl)" }}>Deadlines</h2>
          {matter.status === "open" && <NewDeadlineForm matterId={matter.id} onUpdated={refetch} />}
        </div>
        <DeadlinesList deadlines={deadlines} onUpdated={refetch} />

        <div style={{ marginTop: "var(--space-4)" }}>
          {matter.status === "open" ? (
            <CloseMatterButton matterId={matter.id} onUpdated={refetch} />
          ) : (
            <ReopenMatterButton matterId={matter.id} onUpdated={refetch} />
          )}
        </div>
      </section>

      <section aria-labelledby="panel-documents-heading" style={{ marginTop: "var(--space-5)" }}>
        <div className="section-header">
          <h2 id="panel-documents-heading" style={{ fontSize: "var(--font-size-xl)", marginRight: "auto" }}>Documents</h2>
          {matter.status === "open" && <DocumentUpload matterId={matter.id} onUpdated={refetch} />}
          <GenerateDraftModal matterId={matter.id} matterTitle={matter.title} clientName={client?.name ?? null} onUpdated={refetch} />
        </div>
        <DocumentsList matterId={matter.id} initialDocuments={documents} />
      </section>

      <section aria-labelledby="panel-chat-heading">
        <h2 id="panel-chat-heading" style={{ fontSize: "var(--font-size-xl)", margin: "var(--space-5) 0 var(--space-3)" }}>Chat</h2>
        <ChatPanel matterId={matter.id} initialMessages={messages} hasReadyDocuments={hasReadyDocuments} />
      </section>
    </div>
  );
}
