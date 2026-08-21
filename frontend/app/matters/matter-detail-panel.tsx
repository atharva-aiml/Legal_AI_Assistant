"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { StatusBadge } from "@/components/status-badge";
import { ErrorBanner } from "@/components/ui/error-banner";
import { ChatPanel } from "./[id]/chat-panel";
import { NewDeadlineForm } from "./[id]/new-deadline-form";
import { CloseMatterButton } from "./[id]/close-matter-button";
import { ReopenMatterButton } from "./[id]/reopen-matter-button";

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
type Citation = { id: string; documentId: string | null; fileName: string | null; pageNumber: number | null; section: string | null; excerpt: string | null };
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

function todayISO(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
function formatDueDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/**
 * Text-row deadlines list for this panel — no cards, just a checkbox + title
 * + due date per line. The checkbox toggle updates only this list's own row
 * (via `onToggle`, a local state patch one level up) instead of the heavier
 * `onUpdated`/refetch every other mutation in this panel uses — checking a
 * box shouldn't reload Documents/Chat/the Matter itself.
 */
function PanelDeadlinesList({ deadlines, onToggle }: { deadlines: Deadline[]; onToggle: (id: string, newStatus: "open" | "complete") => void }) {
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const today = todayISO();

  async function toggleComplete(d: Deadline) {
    const newStatus = d.status === "open" ? "complete" : "open";
    setUpdatingId(d.id);
    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/deadlines/${d.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ status: newStatus }),
    });
    setUpdatingId(null);
    if (res.ok) onToggle(d.id, newStatus);
    else alert("Couldn't update this deadline — retry.");
  }

  if (deadlines.length === 0) {
    return <div className="text-tertiary text-sm">No deadlines yet.</div>;
  }

  const sorted = [...deadlines].sort((a, b) => a.dueDate.localeCompare(b.dueDate));

  return (
    <div className="stack" style={{ gap: 0 }}>
      {sorted.map((d) => {
        const isOverdue = d.status === "open" && d.dueDate < today;
        return (
          <label key={d.id} className="panel-list-row">
            <input type="checkbox" checked={d.status === "complete"} disabled={updatingId === d.id} onChange={() => toggleComplete(d)} />
            <span className="panel-list-row-text" style={{ textDecoration: d.status === "complete" ? "line-through" : "none" }}>
              {d.title}
              {d.priority === "critical" && <span style={{ color: "var(--color-warning-text)" }}> · Critical</span>}
            </span>
            <span className="text-xs mono" style={{ color: isOverdue ? "var(--color-error-text)" : "var(--color-text-tertiary)", flexShrink: 0 }}>
              {formatDueDate(d.dueDate)}
            </span>
          </label>
        );
      })}
    </div>
  );
}

/** Compact "+" trigger replacing DocumentUpload's button+dropzone — same upload call, minimal chrome. */
function PanelDocumentAddButton({ matterId, onUpdated }: { matterId: string; onUpdated: () => void }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    Promise.all(
      Array.from(files).map((file) => {
        const formData = new FormData();
        formData.append("file", file);
        return fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/documents`, { method: "POST", credentials: "include", body: formData });
      })
    )
      .then(() => onUpdated())
      .catch(() => alert("Couldn't upload one or more files — retry."))
      .finally(() => setUploading(false));
    e.target.value = "";
  }

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,image/png,image/jpeg,image/tiff,image/webp"
        onChange={handleFileChange}
        style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}
        tabIndex={-1}
        aria-hidden="true"
      />
      <button
        type="button"
        className="panel-add-btn"
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
        aria-label="Add document"
        title="Add document"
      >
        {uploading ? "…" : "+"}
      </button>
    </>
  );
}

/** Text-row documents list for this panel — just the file name (a download link) and, while not yet ready, its status. */
function FileIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="panel-file-icon">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 2v6h6" />
    </svg>
  );
}

function PanelDocumentsList({ documents }: { documents: Doc[] }) {
  if (documents.length === 0) {
    return <div className="text-tertiary text-sm">No documents yet.</div>;
  }
  return (
    <div className="stack" style={{ gap: 0 }}>
      {documents.map((d) => (
        <a key={d.id} href={`${JAVA_API_URL_PUBLIC}/api/documents/${d.id}/download`} className="panel-list-row">
          <FileIcon />
          <span className="panel-list-row-text">{d.fileName}</span>
          {d.status !== "ready" && <span className="text-tertiary text-xs">{d.status}</span>}
        </a>
      ))}
    </div>
  );
}

/**
 * Chrome-tab-style row of document names, shown beside the Matter title
 * instead of the full Documents section while AI Chat mode is open — each
 * tab shares the strip's width equally via flex-basis, so they compress as
 * more documents are added rather than wrapping or overflowing individually.
 */
function DocTabsStrip({
  documents,
  matterId,
  matterOpen,
  onUpdated,
  chatModeOpen,
  onToggleChat,
}: {
  documents: Doc[];
  matterId: string;
  matterOpen: boolean;
  onUpdated: () => void;
  chatModeOpen: boolean;
  onToggleChat: () => void;
}) {
  return (
    <div className="doc-tabs-strip">
      {documents.length === 0 ? (
        <span className="text-tertiary text-xs">No documents</span>
      ) : (
        documents.map((d) => (
          <a key={d.id} href={`${JAVA_API_URL_PUBLIC}/api/documents/${d.id}/download`} className="doc-tab" title={d.fileName}>
            <FileIcon />
            <span className="doc-tab-name">{d.fileName}</span>
          </a>
        ))
      )}
      {/* Same toggle as the (non-chat-mode) Documents header — kept reachable
          here too, since this strip replaces that header while chat is open
          and closing the chat needs to stay possible from the same spot. */}
      <button
        type="button"
        className="chat-toggle-btn"
        onClick={onToggleChat}
        aria-pressed={chatModeOpen}
        aria-label={chatModeOpen ? "Close AI Chat" : "Open AI Chat"}
        title={chatModeOpen ? "Close AI Chat" : "Open AI Chat"}
      >
        <AiSparkleIcon />
      </button>
      {matterOpen && <PanelDocumentAddButton matterId={matterId} onUpdated={onUpdated} />}
    </div>
  );
}

/** Title + status + client line — shared between the normal header and the (narrower) chat-mode header. */
function MatterTitleBlock({ matter, client }: { matter: Matter; client: Client | null }) {
  return (
    <>
      <div className="row-between">
        <h1 style={{ fontSize: "var(--font-size-2xl)" }}>{matter.title}</h1>
        <StatusBadge status={matter.status} />
      </div>
      {client && (
        <div className="text-tertiary text-sm" style={{ marginTop: "var(--space-2)" }}>
          Client: <Link href={`/clients/${client.id}`}>{client.name}</Link>
        </div>
      )}
    </>
  );
}

/** Same sparkle glyph ChatPanel uses for its AI avatar — reused here as the header toggle icon. */
function AiSparkleIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2.5c.4 2.9 1.1 4.9 2.1 5.9s3 1.7 5.9 2.1c-2.9.4-4.9 1.1-5.9 2.1s-1.7 3-2.1 5.9c-.4-2.9-1.1-4.9-2.1-5.9S6.9 11 4 10.6c2.9-.4 4.9-1.1 5.9-2.1S11.6 5.4 12 2.5Z" />
    </svg>
  );
}

/**
 * Same content as /matters/[id]/page.tsx, minus the Breadcrumb (redundant
 * inline under the list), the sticky title bar (the page's own header
 * already pins), and the Activity section (dropped from this panel by
 * request — still shown on the standalone page) — fetched client-side so
 * selecting a Matter from the master list never navigates away from
 * /matters. Every mutating child (Close/Reopen, Generate Document, New
 * Deadline, Deadline complete-toggle, Document upload) gets `onUpdated`
 * wired to refetch instead of their default router.refresh().
 *
 * Deadlines and Documents render as plain text rows here (PanelDeadlinesList /
 * PanelDocumentsList above), not the card-tile DeadlinesList/DocumentsList/
 * DocumentUpload the standalone page uses — by request, side by side instead
 * of stacked, and Documents reduced to file names + a single "+" to add one.
 */
export function MatterDetailPanel({
  matterId,
  onDeadlineChange,
}: {
  matterId: string;
  /** Notified (not required by the standalone page) whenever a deadline's status changes here, so the Matter list's tile can update its "Due X" text live without a full refetch. */
  onDeadlineChange?: (deadline: Deadline) => void;
}) {
  const [matter, setMatter] = useState<Matter | null>(null);
  const [client, setClient] = useState<Client | null>(null);
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [refreshTick, setRefreshTick] = useState(0);
  const [chatModeOpen, setChatModeOpen] = useState(false);

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

      const [documentsRes, chatRes, deadlinesRes] = await Promise.all([
        fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/documents`, { credentials: "include" }),
        fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/chat`, { credentials: "include" }),
        fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/deadlines`, { credentials: "include" }),
      ]);
      if (cancelled) return;

      const { documents: fetchedDocuments }: { documents: Doc[] } = documentsRes.ok ? await documentsRes.json() : { documents: [] };
      const { messages: fetchedMessages }: { messages: ChatMsg[] } = chatRes.ok ? await chatRes.json() : { messages: [] };
      const { deadlines: fetchedDeadlines }: { deadlines: Deadline[] } = deadlinesRes.ok ? await deadlinesRes.json() : { deadlines: [] };

      if (cancelled) return;
      setMatter(fetchedMatter);
      setClient(fetchedClient);
      setDocuments(fetchedDocuments);
      setMessages(fetchedMessages);
      setDeadlines(fetchedDeadlines);
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

  function handleDeadlineToggle(id: string, newStatus: "open" | "complete") {
    // Deliberately not computed inside the setDeadlines updater — React can
    // invoke that updater during another component's render (e.g. Strict
    // Mode's double-invoke), and calling onDeadlineChange (a parent setState)
    // from in there trips "Cannot update a component while rendering a
    // different component." Compute the updated deadline plainly instead.
    const updated = deadlines.find((d) => d.id === id);
    if (!updated) return;
    const next = { ...updated, status: newStatus };
    setDeadlines((prev) => prev.map((d) => (d.id === id ? next : d)));
    onDeadlineChange?.(next);
  }

  if (status === "loading") {
    return <div className="card text-secondary">Loading…</div>;
  }
  if (status === "error" || !matter) {
    return <ErrorBanner>Couldn&apos;t load this matter — retry.</ErrorBanner>;
  }

  const hasReadyDocuments = documents.some((d) => d.status === "ready");

  return (
    <div className="matter-detail-panel" style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <div className="master-detail-col-header">
        {chatModeOpen ? (
          <div className="chat-mode-header-row">
            <div className="chat-mode-title-block">
              <MatterTitleBlock matter={matter} client={client} />
            </div>
            <DocTabsStrip
              documents={documents}
              matterId={matter.id}
              matterOpen={matter.status === "open"}
              onUpdated={refetch}
              chatModeOpen={chatModeOpen}
              onToggleChat={() => setChatModeOpen((o) => !o)}
            />
          </div>
        ) : (
          <MatterTitleBlock matter={matter} client={client} />
        )}
      </div>

      {chatModeOpen ? (
        <div className="chat-fullpanel">
          <ChatPanel matterId={matter.id} initialMessages={messages} hasReadyDocuments={hasReadyDocuments} fullHeight />
        </div>
      ) : (
        <div className="master-detail-col-scroll">
          <div className="row" style={{ alignItems: "flex-start", flexWrap: "wrap", gap: "var(--space-5)", marginTop: "var(--space-1)" }}>
            <section id="panel-deadlines" aria-labelledby="panel-deadlines-heading" style={{ flex: "1 1 260px", minWidth: 0 }}>
              <div className="section-header">
                <h2 id="panel-deadlines-heading" style={{ fontSize: "var(--font-size-lg)" }}>Deadlines</h2>
                {matter.status === "open" && <NewDeadlineForm matterId={matter.id} onUpdated={refetch} />}
              </div>
              <PanelDeadlinesList deadlines={deadlines} onToggle={handleDeadlineToggle} />

              <div style={{ marginTop: "var(--space-4)" }}>
                {matter.status === "open" ? (
                  <CloseMatterButton matterId={matter.id} onUpdated={refetch} />
                ) : (
                  <ReopenMatterButton matterId={matter.id} onUpdated={refetch} />
                )}
              </div>
            </section>

            <section aria-labelledby="panel-documents-heading" style={{ flex: "1 1 260px", minWidth: 0 }}>
              <div className="section-header">
                <h2 id="panel-documents-heading" style={{ fontSize: "var(--font-size-lg)" }}>Documents</h2>
                <div className="row" style={{ gap: "var(--space-2)" }}>
                  <button
                    type="button"
                    className="chat-toggle-btn"
                    onClick={() => setChatModeOpen((o) => !o)}
                    aria-pressed={chatModeOpen}
                    aria-label={chatModeOpen ? "Close AI Chat" : "Open AI Chat"}
                    title={chatModeOpen ? "Close AI Chat" : "Open AI Chat"}
                  >
                    <AiSparkleIcon />
                  </button>
                  {matter.status === "open" && <PanelDocumentAddButton matterId={matter.id} onUpdated={refetch} />}
                </div>
              </div>
              <PanelDocumentsList documents={documents} />
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
