import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

type Lawyer = { name: string; email: string };
type Client = { id: string; name: string; contactEmail: string | null; createdAt: string };
type Matter = { id: string; title: string; status: "open" | "closed" };

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

  return (
    <>
      <NavBar lawyerName={lawyer.name} lawyerEmail={lawyer.email} />
      <main className="page">
        <Link href="/clients" className="text-sm">
          ← Clients
        </Link>
        <h1 style={{ fontSize: "var(--font-size-2xl)", marginTop: "var(--space-3)" }}>{client.name}</h1>

        <div className="card" style={{ marginTop: "var(--space-4)" }}>
          <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "var(--space-4)" }}>
            <div>
              <dt className="field-label" style={{ marginBottom: "var(--space-1)" }}>Contact email</dt>
              <dd style={{ margin: 0 }}>{client.contactEmail || "—"}</dd>
            </div>
            <div>
              <dt className="field-label" style={{ marginBottom: "var(--space-1)" }}>Added</dt>
              <dd style={{ margin: 0 }}>{new Date(client.createdAt).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}</dd>
            </div>
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
            {matters.map((matter) => (
              <Link key={matter.id} href={`/matters/${matter.id}`} className="card">
                <div className="row-between">
                  <div style={{ fontWeight: 500 }}>{matter.title}</div>
                  <StatusBadge status={matter.status} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
