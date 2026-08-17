import { redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { MattersList } from "./matters-list";

type Lawyer = { name: string; email: string };
type Matter = { id: string; title: string; status: "open" | "closed"; clientId: string };
type Client = { id: string; name: string };
type Deadline = { id: string; matterId: string; dueDate: string; status: "open" | "complete" };

export default async function MattersPage({ searchParams }: { searchParams: Promise<{ status?: string; clientId?: string }> }) {
  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");
  const { lawyer }: { lawyer: Lawyer } = await meRes.json();

  const { status, clientId } = await searchParams;

  // I-23: status/clientId are real server-side filters on the same GET /api/matters endpoint.
  const query = new URLSearchParams();
  if (status) query.set("status", status);
  if (clientId) query.set("clientId", clientId);
  const mattersPath = query.toString() ? `/api/matters?${query}` : "/api/matters";

  const [mattersRes, clientsRes, deadlinesRes] = await Promise.all([
    javaFetch(mattersPath),
    javaFetch("/api/clients"),
    javaFetch("/api/deadlines/upcoming?days=36500"), // I-24: every open Deadline, not just a near-term slice
  ]);
  const { matters }: { matters: Matter[] } = mattersRes.ok ? await mattersRes.json() : { matters: [] };
  const { clients }: { clients: Client[] } = clientsRes.ok ? await clientsRes.json() : { clients: [] };
  const { deadlines }: { deadlines: Deadline[] } = deadlinesRes.ok ? await deadlinesRes.json() : { deadlines: [] };

  const hasAnyMattersAtAll = !status && !clientId && matters.length === 0;

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
        ) : hasAnyMattersAtAll ? (
          <EmptyState
            title="No matters yet"
            body="Create a Matter from a Client's page, or start one here."
            action={<Button href="/matters/new">+ New Matter</Button>}
          />
        ) : (
          <MattersList
            matters={matters}
            clients={clients}
            deadlines={deadlines}
            currentStatus={status ?? ""}
            currentClientId={clientId ?? ""}
          />
        )}
      </main>
    </>
  );
}
