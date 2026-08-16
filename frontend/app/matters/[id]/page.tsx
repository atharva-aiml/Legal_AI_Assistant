import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { StatusBadge } from "@/components/status-badge";
import { DocumentUpload } from "./document-upload";
import { DocumentsList } from "./documents-list";
import { ChatPanel } from "./chat-panel";
import { DeadlinesList } from "./deadlines-list";
import { NewDeadlineForm } from "./new-deadline-form";
import { CloseMatterButton } from "./close-matter-button";
import { GenerateDraftModal } from "./generate-draft-modal";

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
type ChatMsg = { id: string; role: "user" | "assistant"; content: string; createdAt: string; citations: Citation[]; lowConfidence: boolean | null };
type Deadline = {
  id: string;
  matterId: string;
  title: string;
  dueDate: string;
  status: "open" | "complete";
  notificationLeadDays: number;
};

export default async function MatterDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");

  const matterRes = await javaFetch(`/api/matters/${id}`);
  if (matterRes.status === 404) notFound();
  if (!matterRes.ok) throw new Error("Couldn't load this matter");
  const { matter, client }: { matter: Matter; client: Client | null } = await matterRes.json();

  const documentsRes = await javaFetch(`/api/matters/${id}/documents`);
  const { documents }: { documents: Doc[] } = documentsRes.ok ? await documentsRes.json() : { documents: [] };
  const hasReadyDocuments = documents.some((d) => d.status === "ready");

  const chatRes = await javaFetch(`/api/matters/${id}/chat`);
  const { messages }: { messages: ChatMsg[] } = chatRes.ok ? await chatRes.json() : { messages: [] };

  const deadlinesRes = await javaFetch(`/api/matters/${id}/deadlines`);
  const { deadlines }: { deadlines: Deadline[] } = deadlinesRes.ok ? await deadlinesRes.json() : { deadlines: [] };

  return (
    <main className="page">
      <Link href="/matters" className="text-sm">
        ← Matters
      </Link>
      <div className="row-between" style={{ marginTop: "var(--space-3)" }}>
        <h1 style={{ fontSize: "var(--font-size-2xl)" }}>{matter.title}</h1>
        <StatusBadge status={matter.status} />
      </div>
      {client && (
        <div className="text-tertiary text-sm" style={{ marginTop: "var(--space-2)" }}>
          Client: <Link href={`/clients/${client.id}`}>{client.name}</Link>
        </div>
      )}

      <section id="deadlines" aria-labelledby="deadlines-heading">
        <div className="section-header">
          <h2 id="deadlines-heading" style={{ fontSize: "var(--font-size-xl)" }}>Deadlines</h2>
          <NewDeadlineForm matterId={matter.id} />
        </div>
        <DeadlinesList deadlines={deadlines} />

        {matter.status === "open" && (
          <div style={{ marginTop: "var(--space-4)" }}>
            <CloseMatterButton matterId={matter.id} />
          </div>
        )}
      </section>

      <section aria-labelledby="documents-heading">
        <div className="section-header">
          <h2 id="documents-heading" style={{ fontSize: "var(--font-size-xl)", marginRight: "auto" }}>Documents</h2>
          <DocumentUpload matterId={matter.id} />
          <GenerateDraftModal matterId={matter.id} matterTitle={matter.title} clientName={client?.name ?? null} />
        </div>
        <DocumentsList matterId={matter.id} initialDocuments={documents} />
      </section>

      <section aria-labelledby="chat-heading">
        <h2 id="chat-heading" style={{ fontSize: "var(--font-size-xl)", margin: "var(--space-5) 0 var(--space-3)" }}>Chat</h2>
        <ChatPanel matterId={matter.id} initialMessages={messages} hasReadyDocuments={hasReadyDocuments} />
      </section>
    </main>
  );
}
