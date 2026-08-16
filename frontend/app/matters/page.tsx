import Link from "next/link";
import { redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";

type Lawyer = { name: string; email: string };
type Matter = { id: string; title: string; status: "open" | "closed"; clientId: string };
type Client = { id: string; name: string };

export default async function MattersPage() {
  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");
  const { lawyer }: { lawyer: Lawyer } = await meRes.json();

  const [mattersRes, clientsRes] = await Promise.all([javaFetch("/api/matters"), javaFetch("/api/clients")]);
  const { matters }: { matters: Matter[] } = mattersRes.ok ? await mattersRes.json() : { matters: [] };
  const { clients }: { clients: Client[] } = clientsRes.ok ? await clientsRes.json() : { clients: [] };
  const clientNameById = new Map(clients.map((c) => [c.id, c.name]));

  return (
    <>
      <NavBar lawyerName={lawyer.name} lawyerEmail={lawyer.email} />
      <main className="page">
        <div className="page-header">
          <h1 style={{ fontSize: "var(--font-size-2xl)" }}>Matters</h1>
          <Button href="/matters/new">+ New Matter</Button>
        </div>

        {!mattersRes.ok ? (
          <ErrorBanner>Couldn&apos;t load matters — retry.</ErrorBanner>
        ) : matters.length === 0 ? (
          <EmptyState
            title="No matters yet"
            body="Create a Matter from a Client's page, or start one here."
            action={<Button href="/matters/new">+ New Matter</Button>}
          />
        ) : (
          <div className="stack">
            {matters.map((matter) => (
              <Link key={matter.id} href={`/matters/${matter.id}`} className="card">
                <div className="row-between">
                  <div>
                    <div style={{ fontWeight: 500 }}>{matter.title}</div>
                    <div className="text-tertiary text-sm">{clientNameById.get(matter.clientId)}</div>
                  </div>
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
