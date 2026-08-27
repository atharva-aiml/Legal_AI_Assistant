"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { usePersistedState } from "@/lib/use-persisted-state";
import { TooltipBubble } from "@/components/ui/tooltip-bubble";
import { PlusIcon } from "@/components/ui/plus-icon";
import { StatusBadge } from "@/components/status-badge";
import { ErrorBanner } from "@/components/ui/error-banner";
import { ChatPanel } from "./[id]/chat-panel";
import { NewDeadlineForm } from "./[id]/new-deadline-form";
import { CloseMatterButton } from "./[id]/close-matter-button";
import { ReopenMatterButton } from "./[id]/reopen-matter-button";
import { DeleteMatterModal } from "./[id]/delete-matter-modal";

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
type ChatMsg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  citations: Citation[];
  lowConfidence: boolean | null;
  fullContext: boolean | null;
  pinned: boolean;
  parentId: string | null;
  siblingIds: string[];
};
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

/** Compact "+" trigger replacing DocumentUpload's button+dropzone — same upload call, minimal chrome.
 * `attention` (used from the AI Chat header when the Matter has no ready
 * Document yet) turns it red and pulses it a few times to point the lawyer
 * at the one thing they need to do before they can ask anything. */
function PanelDocumentAddButton({ matterId, onUpdated, attention, tooltipBelow }: { matterId: string; onUpdated: () => void; attention?: boolean; tooltipBelow?: boolean }) {
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
        className={`panel-add-btn${attention ? " panel-add-btn-attention" : ""}`}
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
        aria-label="Add document"
      >
        {uploading ? "…" : <PlusIcon />}
        <TooltipBubble label="Add document" below={tooltipBelow} />
      </button>
    </>
  );
}

function UploadCloudIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 14.9A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 2.5 8.2" />
      <path d="M12 12v9" />
      <path d="m16 16-4-4-4 4" />
    </svg>
  );
}

/**
 * Drag-and-drop upload surface, sits beside PanelDocumentsList so uploading
 * doesn't require hunting for the small "+" in the section header. Same
 * upload call as PanelDocumentAddButton (POST per file, Promise.all) — no
 * fake progress bar, since there's nothing here to fake it from; fetch
 * doesn't expose upload progress and this app doesn't stand up an XHR just
 * to get one.
 */
function PanelDocumentDropzone({ matterId, onUpdated }: { matterId: string; onUpdated: () => void }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const errorTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (errorTimeoutRef.current) clearTimeout(errorTimeoutRef.current);
    };
  }, []);

  function showError(message: string) {
    setError(message);
    if (errorTimeoutRef.current) clearTimeout(errorTimeoutRef.current);
    errorTimeoutRef.current = setTimeout(() => setError(null), 3000);
  }

  function uploadFiles(files: FileList | File[]) {
    const list = Array.from(files);
    if (list.length === 0) return;
    setUploading(true);
    Promise.all(
      list.map((file) => {
        const formData = new FormData();
        formData.append("file", file);
        return fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/documents`, { method: "POST", credentials: "include", body: formData });
      })
    )
      .then((responses) => {
        if (responses.some((r) => !r.ok)) showError("Couldn't upload one or more files — retry.");
        onUpdated();
      })
      .catch(() => showError("Couldn't upload one or more files — retry."))
      .finally(() => setUploading(false));
  }

  return (
    <div
      className={`doc-dropzone${dragging ? " doc-dropzone-dragging" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        if (!uploading) setDragging(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        setDragging(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (uploading) return;
        if (e.dataTransfer.files?.length) uploadFiles(e.dataTransfer.files);
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,image/png,image/jpeg,image/tiff,image/webp"
        onChange={(e) => {
          if (e.target.files?.length) uploadFiles(e.target.files);
          e.target.value = "";
        }}
        style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}
        tabIndex={-1}
        aria-hidden="true"
      />
      <UploadCloudIcon />
      <div className="doc-dropzone-title">{uploading ? "Uploading…" : "Drag and drop or"}</div>
      <div className="doc-dropzone-hint">PDF, DOCX, PNG, JPG, TIFF, WEBP</div>
      <button
        type="button"
        className="doc-dropzone-browse-btn"
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
      >
        Upload File
      </button>
      {error && <div className="doc-dropzone-error">{error}</div>}
    </div>
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

function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3v12" />
      <path d="m7 10 5 5 5-5" />
      <path d="M5 21h14" />
    </svg>
  );
}

function PanelDocumentsList({ documents }: { documents: Doc[] }) {
  if (documents.length === 0) {
    return <div className="text-tertiary text-sm">No documents yet.</div>;
  }
  return (
    <div className="stack" style={{ gap: 0 }}>
      {documents.map((d) => {
        const downloadHref = `${JAVA_API_URL_PUBLIC}/api/documents/${d.id}/download`;
        return (
          <div key={d.id} className="panel-list-row">
            <a href={downloadHref} className="panel-download-icon-btn" aria-label={`Download ${d.fileName}`}>
              <DownloadIcon />
              <TooltipBubble label="Download" />
            </a>
            <a href={downloadHref} className="panel-list-row-link">
              <FileIcon />
              <span className="panel-list-row-text">{d.fileName}</span>
              {d.status !== "ready" && <span className="text-tertiary text-xs">{d.status}</span>}
            </a>
          </div>
        );
      })}
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
  addAttention,
}: {
  documents: Doc[];
  matterId: string;
  matterOpen: boolean;
  onUpdated: () => void;
  chatModeOpen: boolean;
  onToggleChat: () => void;
  /** Pulse the "add document" button — set when chat is open but the Matter has no ready Document. */
  addAttention?: boolean;
}) {
  return (
    <div className="doc-tabs-strip">
      <div className="doc-tabs-strip-tabs">
        {documents.length === 0 ? (
          <span className="text-tertiary text-xs">No documents</span>
        ) : (
          // Native title (the tabs clip on overflow); the toggle/add buttons below use TooltipBubble.
          documents.map((d) => (
            <a key={d.id} href={`${JAVA_API_URL_PUBLIC}/api/documents/${d.id}/download`} className="doc-tab" title={d.fileName}>
              <FileIcon />
              <span className="doc-tab-name">{d.fileName}</span>
            </a>
          ))
        )}
      </div>
      {/* Same toggle as the (non-chat-mode) Documents header — kept reachable
          here too, since this strip replaces that header while chat is open. */}
      <button
        type="button"
        className="chat-toggle-btn"
        onClick={onToggleChat}
        aria-pressed={chatModeOpen}
        aria-label={chatModeOpen ? "Close AI Chat" : "Open AI Chat"}
      >
        <AiSparkleIcon />
        <TooltipBubble label={chatModeOpen ? "Close AI Chat" : "Open AI Chat"} below />
      </button>
      {matterOpen && <PanelDocumentAddButton matterId={matterId} onUpdated={onUpdated} attention={addAttention} tooltipBelow />}
    </div>
  );
}

/** Title + status + client line — shared between the normal header and the (narrower) chat-mode header. */
function MatterTitleBlock({ matter, client, onDeleted }: { matter: Matter; client: Client | null; onDeleted: () => void }) {
  return (
    <>
      <div className="row-between">
        <h1 style={{ fontSize: "var(--font-size-2xl)" }}>{matter.title}</h1>
        <div className="row" style={{ gap: "var(--space-2)" }}>
          <StatusBadge status={matter.status} />
          <DeleteMatterModal matterId={matter.id} matterTitle={matter.title} onDeleted={onDeleted} tooltipBelow />
        </div>
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
  onDeleted,
}: {
  matterId: string;
  /** Notified (not required by the standalone page) whenever a deadline's status changes here, so the Matter list's tile can update its "Due X" text live without a full refetch. */
  onDeadlineChange?: (deadline: Deadline) => void;
  onDeleted: () => void;
}) {
  const [matter, setMatter] = useState<Matter | null>(null);
  const [client, setClient] = useState<Client | null>(null);
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [refreshTick, setRefreshTick] = useState(0);
  // Persisted per Matter (sessionStorage) so refreshing the browser while
  // the AI Chat view is open reopens it, instead of dropping back to the
  // Documents/Deadlines view. Keyed by matterId — this component is already
  // remounted per Matter (key={selectedMatterId} upstream), so each Matter
  // keeps its own last chat view.
  const [chatModeOpen, setChatModeOpen] = usePersistedState<boolean>(`matters:${matterId}:chatMode`, false);
  const [chatMaximized, setChatMaximized] = usePersistedState<boolean>(`matters:${matterId}:chatMaximized`, false);
  const prevChatModeOpen = useRef(chatModeOpen);
  // Owned here (not inside ChatPanel) so toggling chatMaximized — which
  // swaps between two structurally different ChatPanel mounts, one portaled
  // to document.body — doesn't discard the conversation or the unsent draft.
  const [chatDraft, setChatDraft] = useState("");

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

  // Closing AI Chat should always land back in the normal (non-maximized)
  // layout next time it's reopened, not resume full-screen — but only on a
  // real open->closed transition, never on mount, where usePersistedState is
  // still hydrating chatMaximized from sessionStorage and a reset here would
  // wipe it before a refresh can restore it.
  useEffect(() => {
    if (prevChatModeOpen.current && !chatModeOpen) setChatMaximized(false);
    prevChatModeOpen.current = chatModeOpen;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatModeOpen]);

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

  const chatModeBlock = (
    <>
      <div className="master-detail-col-header">
        <div className="chat-mode-header-row">
          <div className="chat-mode-title-block">
            <MatterTitleBlock matter={matter} client={client} onDeleted={onDeleted} />
          </div>
          <DocTabsStrip
            documents={documents}
            matterId={matter.id}
            matterOpen={matter.status === "open"}
            onUpdated={refetch}
            chatModeOpen={chatModeOpen}
            onToggleChat={() => setChatModeOpen(!chatModeOpen)}
            addAttention={!hasReadyDocuments}
          />
        </div>
      </div>
      <div className="chat-fullpanel">
        <ChatPanel
          matterId={matter.id}
          messages={messages}
          setMessages={setMessages}
          draft={chatDraft}
          setDraft={setChatDraft}
          hasReadyDocuments={hasReadyDocuments}
          onDocumentsReady={refetch}
          fullHeight
          maximized={chatMaximized}
          onToggleMaximize={() => setChatMaximized(!chatMaximized)}
        />
      </div>
    </>
  );

  if (chatModeOpen && chatMaximized) {
    // Maximized layout is its own thing (30% sidebar + chat filling the
    // rest), not a reuse of chatModeBlock's stacked header-then-chat shape.
    const chatMaximizedBlock = (
      <div className="chat-maximized-layout">
        <div className="chat-maximized-sidebar">
          <MatterTitleBlock matter={matter} client={client} onDeleted={onDeleted} />
          <div>
            <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-3)" }}>Documents</h2>
            <PanelDocumentsList documents={documents} />
          </div>
        </div>
        <div className="chat-maximized-chat">
          <ChatPanel
            matterId={matter.id}
            messages={messages}
            setMessages={setMessages}
            draft={chatDraft}
            setDraft={setChatDraft}
            hasReadyDocuments={hasReadyDocuments}
            onDocumentsReady={refetch}
            fullHeight
            maximized={chatMaximized}
            onToggleMaximize={() => setChatMaximized(!chatMaximized)}
          />
        </div>
      </div>
    );
    // Portaled to document.body: .master-detail-panel-col (an ancestor) keeps
    // a permanent no-op `transform` from its own mount animation's fill-mode,
    // which silently makes it the containing block for any `position: fixed`
    // descendant — an in-place fixed overlay here would only cover that
    // column, not the navbar or the Matter list beside it.
    if (typeof document === "undefined") return null;
    return createPortal(<div className="chat-maximized-overlay">{chatMaximizedBlock}</div>, document.body);
  }

  return (
    <div className="matter-detail-panel" style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      {chatModeOpen ? (
        chatModeBlock
      ) : (
        <>
      <div className="master-detail-col-header">
          <MatterTitleBlock matter={matter} client={client} onDeleted={onDeleted} />
      </div>

        <div className="master-detail-col-scroll">
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)", marginTop: "var(--space-1)" }}>
            <section aria-labelledby="panel-documents-heading" style={{ width: "100%" }}>
              <div className="documents-columns">
                <div className="documents-list-col">
                  <div className="section-header">
                    <h2 id="panel-documents-heading" style={{ fontSize: "var(--font-size-lg)" }}>Documents</h2>
                    <div className="row" style={{ gap: "var(--space-2)" }}>
                      <button
                        type="button"
                        className="ask-ai-btn"
                        onClick={() => setChatModeOpen(!chatModeOpen)}
                        aria-pressed={chatModeOpen}
                        aria-label={chatModeOpen ? "Close AI Chat" : "Open AI Chat"}
                      >
                        <AiSparkleIcon />
                        <span>Ask AI</span>
                        <TooltipBubble label={chatModeOpen ? "Close AI Chat" : "Open AI Chat"} below />
                      </button>
                      {matter.status === "open" && <PanelDocumentAddButton matterId={matter.id} onUpdated={refetch} tooltipBelow />}
                    </div>
                  </div>
                  <PanelDocumentsList documents={documents} />
                </div>
                {matter.status === "open" && (
                  <div className="documents-upload-col">
                    <PanelDocumentDropzone matterId={matter.id} onUpdated={refetch} />
                  </div>
                )}
              </div>
            </section>

            <section id="panel-deadlines" aria-labelledby="panel-deadlines-heading" style={{ maxWidth: "65%" }}>
              <div className="row" style={{ gap: "var(--space-2)", margin: "var(--space-5) 0 var(--space-3)" }}>
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
          </div>
        </div>
        </>
      )}
    </div>
  );
}
