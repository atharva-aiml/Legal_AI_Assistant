import Link from "next/link";
import { redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";

type Lawyer = { name: string; email: string };
type Client = { id: string; name: string };
type Matter = { id: string; title: string; status: "open" | "closed"; clientId: string };

export default async function SearchPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");
  const { lawyer }: { lawyer: Lawyer } = await meRes.json();

  const { q } = await searchParams;
  const query = (q ?? "").trim();

  let clients: Client[] = [];
  let matters: Matter[] = [];
  let errored = false;

  if (query) {
    const res = await javaFetch(`/api/search?q=${encodeURIComponent(query)}`);
    if (res.ok) {
      const body: { clients: Client[]; matters: Matter[] } = await res.json();
      clients = body.clients;
      matters = body.matters;
    } else {
      errored = true;
    }
  }

  const hasResults = clients.length > 0 || matters.length > 0;

  return (
    <>
      <NavBar lawyerName={lawyer.name} lawyerEmail={lawyer.email} />
      <main className="page">
        <h1 style={{ fontSize: "var(--font-size-2xl)", margin: "var(--space-5) 0 var(--space-4)" }}>
          {query ? `Results for "${query}"` : "Search"}
        </h1>

        {!query && <EmptyState title="Search Clients &amp; Matters" body="Type a Client or Matter name into the search bar above." />}

        {query && errored && <ErrorBanner>Search failed — retry.</ErrorBanner>}

        {query && !errored && !hasResults && (
          <EmptyState
            title={`No results for "${query}"`}
            body="Check the spelling, or browse Clients / Matters directly."
            action={
              <div className="row" style={{ justifyContent: "center" }}>
                <Link href="/clients">Clients</Link>
                <span aria-hidden="true">·</span>
                <Link href="/matters">Matters</Link>
              </div>
            }
          />
        )}

        {clients.length > 0 && (
          <>
            <h2 style={{ fontSize: "var(--font-size-xl)", margin: "0 0 var(--space-3)" }}>Clients</h2>
            <div className="stack" style={{ marginBottom: "var(--space-5)" }}>
              {clients.map((c) => (
                <Link key={c.id} href={`/clients/${c.id}`} className="card">
                  <div style={{ fontWeight: 500 }}>{c.name}</div>
                  <div className="text-tertiary text-sm">Matched on Client name</div>
                </Link>
              ))}
            </div>
          </>
        )}

        {matters.length > 0 && (
          <>
            <h2 style={{ fontSize: "var(--font-size-xl)", margin: "0 0 var(--space-3)" }}>Matters</h2>
            <div className="stack">
              {matters.map((m) => (
                <Link key={m.id} href={`/matters/${m.id}`} className="card">
                  <div className="row-between">
                    <div>
                      <div style={{ fontWeight: 500 }}>{m.title}</div>
                      <div className="text-tertiary text-sm">Matched on Matter title</div>
                    </div>
                    <StatusBadge status={m.status} />
                  </div>
                </Link>
              ))}
            </div>
          </>
        )}
      </main>
    </>
  );
}
