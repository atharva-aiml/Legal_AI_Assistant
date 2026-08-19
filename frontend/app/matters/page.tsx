import { redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { NewMatterModal } from "@/app/clients/[id]/new-matter-modal";
import { MattersMasterDetail } from "./matters-master-detail";

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
      <main className="page-wide master-detail-shell" style={{ paddingTop: "var(--space-3)" }}>
        {/* MattersMasterDetail renders its own "Matters" title (aligned with
            the detail panel's Matter title) — this header only covers the
            error/empty states, where that component isn't rendered at all. */}
        {!mattersRes.ok ? (
          <>
            <div className="page-header" style={{ marginTop: 0, marginBottom: "var(--space-2)" }}>
              <div className="row">
                <h1 style={{ fontSize: "var(--font-size-2xl)" }}>Matters</h1>
                <NewMatterModal clients={clients} buttonClassName="btn-hold-bg btn-xs" />
              </div>
            </div>
            <ErrorBanner>Couldn&apos;t load matters — retry.</ErrorBanner>
          </>
        ) : hasAnyMattersAtAll ? (
          <>
            <div className="page-header" style={{ marginTop: 0, marginBottom: "var(--space-2)" }}>
              <div className="row">
                <h1 style={{ fontSize: "var(--font-size-2xl)" }}>Matters</h1>
                <NewMatterModal clients={clients} buttonClassName="btn-hold-bg btn-xs" />
              </div>
            </div>
            <EmptyState
              title="No matters yet"
              body="Create a Matter from a Client's page, or start one here."
              action={<NewMatterModal clients={clients} />}
            />
          </>
        ) : (
          <MattersMasterDetail
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
