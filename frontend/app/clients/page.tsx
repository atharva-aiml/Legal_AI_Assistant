import Link from "next/link";
import { redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";

type Lawyer = { name: string; email: string };
type Client = { id: string; name: string; contactEmail: string | null };
type Matter = { id: string; clientId: string; status: "open" | "closed" };

export default async function ClientsPage() {
  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");
  const { lawyer }: { lawyer: Lawyer } = await meRes.json();

  const [clientsRes, mattersRes] = await Promise.all([javaFetch("/api/clients"), javaFetch("/api/matters")]);
  const { clients }: { clients: Client[] } = clientsRes.ok ? await clientsRes.json() : { clients: [] };
  const { matters }: { matters: Matter[] } = mattersRes.ok ? await mattersRes.json() : { matters: [] };

  const matterCounts = new Map<string, { open: number; closed: number }>();
  for (const m of matters) {
    const counts = matterCounts.get(m.clientId) ?? { open: 0, closed: 0 };
    if (m.status === "open") counts.open++;
    else counts.closed++;
    matterCounts.set(m.clientId, counts);
  }

  return (
    <>
      <NavBar lawyerName={lawyer.name} lawyerEmail={lawyer.email} />
      <main className="page">
        <div className="page-header">
          <h1 style={{ fontSize: "var(--font-size-2xl)" }}>Clients</h1>
          <Button href="/clients/new">+ New Client</Button>
        </div>

        {!clientsRes.ok ? (
          <ErrorBanner>Couldn&apos;t load clients — retry.</ErrorBanner>
        ) : clients.length === 0 ? (
          <EmptyState
            title="No clients yet"
            body="Add your first client to start opening Matters and uploading documents."
            action={<Button href="/clients/new">+ New Client</Button>}
          />
        ) : (
          <div className="stack">
            {clients.map((c) => {
              const counts = matterCounts.get(c.id) ?? { open: 0, closed: 0 };
              return (
                <Link key={c.id} href={`/clients/${c.id}`} className="card">
                  <div className="row-between">
                    <div>
                      <div style={{ fontWeight: 500 }}>{c.name}</div>
                      {c.contactEmail && <div className="text-tertiary text-sm">{c.contactEmail}</div>}
                    </div>
                    <div className="text-tertiary text-sm">
                      {counts.open + counts.closed === 0
                        ? "No matters"
                        : `${counts.open} open · ${counts.closed} closed`}
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
