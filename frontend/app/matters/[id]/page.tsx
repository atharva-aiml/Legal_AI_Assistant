import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { StatusBadge } from "@/components/status-badge";
import { Breadcrumb, type BreadcrumbItem } from "@/components/ui/breadcrumb";
import { DocumentUpload } from "./document-upload";
import { DocumentsList } from "./documents-list";
import { ChatPanel } from "./chat-panel";
import { DeadlinesList } from "./deadlines-list";
import { NewDeadlineForm } from "./new-deadline-form";
import { CloseMatterButton } from "./close-matter-button";
import { ReopenMatterButton } from "./reopen-matter-button";
import { GenerateDraftModal } from "./generate-draft-modal";

type Lawyer = { name: string; email: string };
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

export default async function MatterDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");
  const { lawyer }: { lawyer: Lawyer } = await meRes.json();

  const matterRes = await javaFetch(`/api/matters/${id}`);
  if (matterRes.status === 404) notFound();
  if (!matterRes.ok) throw new Error("Couldn't load this matter");
  const { matter, client }: { matter: Matter; client: Client | null } = await matterRes.json();

  // I-07: Recent Matters is a nice-to-have widget — a failed view-record
  // must never break the page the lawyer actually asked for.
  await javaFetch(`/api/matters/${id}/view`, { method: "POST" }).catch(() => {});

  const documentsRes = await javaFetch(`/api/matters/${id}/documents`);
  const { documents }: { documents: Doc[] } = documentsRes.ok ? await documentsRes.json() : { documents: [] };
  const hasReadyDocuments = documents.some((d) => d.status === "ready");

  const chatRes = await javaFetch(`/api/matters/${id}/chat`);
  const { messages }: { messages: ChatMsg[] } = chatRes.ok ? await chatRes.json() : { messages: [] };

  const deadlinesRes = await javaFetch(`/api/matters/${id}/deadlines`);
  const { deadlines }: { deadlines: Deadline[] } = deadlinesRes.ok ? await deadlinesRes.json() : { deadlines: [] };

  const activityRes = await javaFetch(`/api/matters/${id}/activity`);
  const { entries: activity }: { entries: ActivityEntry[] } = activityRes.ok ? await activityRes.json() : { entries: [] };

  // I-55: the real multi-level path (Client → Matter), not just "up one level" to /matters.
  const breadcrumbItems: BreadcrumbItem[] = client
    ? [{ label: "Clients", href: "/clients" }, { label: client.name, href: `/clients/${client.id}` }, { label: matter.title }]
    : [{ label: "Matters", href: "/matters" }, { label: matter.title }];

  return (
    <>
      <NavBar lawyerName={lawyer.name} lawyerEmail={lawyer.email} />
      <main className="page-wide">
        {/* I-30: pinned so the title/status/Close-Matter action stay reachable while scrolling a long Chat. */}
        <div
          className="row-between"
          style={{
            position: "sticky",
            top: "var(--nav-height)",
            zIndex: 20,
            background: "var(--color-bg-surface)",
            borderBottom: "1px solid var(--color-border-default)",
            padding: "var(--space-3) 0",
            marginBottom: "var(--space-3)",
          }}
        >
          <div className="row" style={{ gap: "var(--space-3)", minWidth: 0 }}>
            <span style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{matter.title}</span>
            <StatusBadge status={matter.status} />
          </div>
          {matter.status === "open" ? <CloseMatterButton matterId={matter.id} /> : <ReopenMatterButton matterId={matter.id} />}
        </div>

        <Breadcrumb items={breadcrumbItems} />
        <div className="row-between" style={{ marginTop: "var(--space-3)" }}>
          <h1 style={{ fontSize: "var(--font-size-2xl)" }}>{matter.title}</h1>
          <StatusBadge status={matter.status} />
        </div>
        {client && (
          <div className="text-tertiary text-sm" style={{ marginTop: "var(--space-2)" }}>
            Client: <Link href={`/clients/${client.id}`}>{client.name}</Link>
          </div>
        )}

        {/* I-32, moved up + condensed per follow-up request: a compact-glance summary
            before the detail sections, not a full-size section competing with them. */}
        {activity.length > 0 && (
          <section aria-labelledby="activity-heading" style={{ marginTop: "var(--space-4)" }}>
            <h2 id="activity-heading" style={{ fontSize: "var(--font-size-base)", fontWeight: 600, margin: "0 0 var(--space-2)" }}>
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

        <section id="deadlines" aria-labelledby="deadlines-heading">
          <div className="section-header">
            <h2 id="deadlines-heading" style={{ fontSize: "var(--font-size-xl)" }}>Deadlines</h2>
            {/* 03-UX-Product-Design.md J4: a Closed Matter is read-only — create actions are hidden, not just discouraged. */}
            {matter.status === "open" && <NewDeadlineForm matterId={matter.id} />}
          </div>
          <DeadlinesList deadlines={deadlines} />

          <div style={{ marginTop: "var(--space-4)" }}>
            {matter.status === "open" ? <CloseMatterButton matterId={matter.id} /> : <ReopenMatterButton matterId={matter.id} />}
          </div>
        </section>

        <section aria-labelledby="documents-heading">
          <div className="section-header">
            <h2 id="documents-heading" style={{ fontSize: "var(--font-size-xl)", marginRight: "auto" }}>Documents</h2>
            {matter.status === "open" && <DocumentUpload matterId={matter.id} />}
            <GenerateDraftModal matterId={matter.id} matterTitle={matter.title} clientName={client?.name ?? null} />
          </div>
          <DocumentsList matterId={matter.id} initialDocuments={documents} />
        </section>

        <section aria-labelledby="chat-heading">
          <h2 id="chat-heading" style={{ fontSize: "var(--font-size-xl)", margin: "var(--space-5) 0 var(--space-3)" }}>AI Chat</h2>
          <ChatPanel matterId={matter.id} initialMessages={messages} hasReadyDocuments={hasReadyDocuments} />
        </section>
      </main>
    </>
  );
}
