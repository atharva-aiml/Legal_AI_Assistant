import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { EditClientModal } from "./edit-client-modal";

type Lawyer = { name: string; email: string };
type Client = { id: string; name: string; contactEmail: string | null; contactPhone: string | null; notes: string | null; createdAt: string };
type Matter = { id: string; title: string; status: "open" | "closed" };
type Deadline = { id: string; matterId: string; dueDate: string; status: "open" | "complete" };

function formatDueDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default async function ClientDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");
  const { lawyer }: { lawyer: Lawyer } = await meRes.json();

  const clientRes = await javaFetch(`/api/clients/${id}`);
  if (clientRes.status === 404) notFound();
  if (!clientRes.ok) throw new Error("Couldn't load this client");
  const { client }: { client: Client } = await clientRes.json();

  const mattersRes = await javaFetch(`/api/matters?clientId=${client.id}`);
  const { matters }: { matters: Matter[] } = mattersRes.ok ? await mattersRes.json() : { matters: [] };

  // I-19: a big-enough window to mean "every open Deadline," not just a near-term slice —
  // /api/deadlines/upcoming already scopes to status=open, so no further filtering needed.
  const deadlinesRes = await javaFetch(`/api/deadlines/upcoming?days=36500`);
  const { deadlines }: { deadlines: Deadline[] } = deadlinesRes.ok ? await deadlinesRes.json() : { deadlines: [] };
  const matterIds = new Set(matters.map((m) => m.id));
  const nextDeadlineByMatter = new Map<string, string>();
  for (const d of deadlines) {
    if (!matterIds.has(d.matterId)) continue;
    const current = nextDeadlineByMatter.get(d.matterId);
    if (!current || d.dueDate < current) nextDeadlineByMatter.set(d.matterId, d.dueDate);
  }

  return (
    <>
      <NavBar lawyerName={lawyer.name} lawyerEmail={lawyer.email} />
      <main className="page">
        <Breadcrumb items={[{ label: "Clients", href: "/clients" }, { label: client.name }]} />
        <div className="row-between" style={{ marginTop: "var(--space-3)" }}>
          <h1 style={{ fontSize: "var(--font-size-2xl)" }}>{client.name}</h1>
          <EditClientModal client={client} />
        </div>

        <div className="card" style={{ marginTop: "var(--space-4)" }}>
          <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "var(--space-4)" }}>
            <div>
              <dt className="field-label" style={{ marginBottom: "var(--space-1)" }}>Contact email</dt>
              <dd style={{ margin: 0 }}>{client.contactEmail || "—"}</dd>
            </div>
            <div>
              <dt className="field-label" style={{ marginBottom: "var(--space-1)" }}>Contact phone</dt>
              <dd style={{ margin: 0 }}>{client.contactPhone || "—"}</dd>
            </div>
            <div>
              <dt className="field-label" style={{ marginBottom: "var(--space-1)" }}>Added</dt>
              <dd style={{ margin: 0 }}>{new Date(client.createdAt).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}</dd>
            </div>
            {client.notes && (
              <div style={{ gridColumn: "1 / -1" }}>
                <dt className="field-label" style={{ marginBottom: "var(--space-1)" }}>Notes</dt>
                <dd style={{ margin: 0, whiteSpace: "pre-wrap" }}>{client.notes}</dd>
              </div>
            )}
          </dl>
        </div>

        <div className="section-header">
          <h2 style={{ fontSize: "var(--font-size-xl)" }}>Matters</h2>
          <Button href={`/matters/new?clientId=${client.id}`}>+ New Matter</Button>
        </div>

        {matters.length === 0 ? (
          <EmptyState title="No matters yet" body="Open the first Matter for this client to start uploading documents." action={<Button href={`/matters/new?clientId=${client.id}`}>+ New Matter</Button>} />
        ) : (
          <div className="stack">
            {matters.map((matter) => {
              const nextDeadline = nextDeadlineByMatter.get(matter.id);
              return (
                <Link key={matter.id} href={`/matters/${matter.id}`} className="card">
                  <div className="row-between">
                    <div style={{ fontWeight: 500 }}>{matter.title}</div>
                    <div className="row" style={{ gap: "var(--space-3)" }}>
                      {nextDeadline && <span className="text-tertiary text-sm mono">Due {formatDueDate(nextDeadline)}</span>}
                      <StatusBadge status={matter.status} />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>
    </>
  );
}
