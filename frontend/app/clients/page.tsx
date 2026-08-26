import { redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { ClientsMasterDetail } from "./clients-master-detail";
import { NewClientModal } from "./new/new-client-modal";

type Lawyer = { name: string; email: string };
type Client = { id: string; name: string; contactEmail: string | null };
type Matter = { id: string; clientId: string; status: "open" | "closed"; updatedAt: string };

export default async function ClientsPage() {
  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");
  const { lawyer }: { lawyer: Lawyer } = await meRes.json();

  const [clientsRes, mattersRes] = await Promise.all([javaFetch("/api/clients"), javaFetch("/api/matters")]);
  const { clients }: { clients: Client[] } = clientsRes.ok ? await clientsRes.json() : { clients: [] };
  const { matters }: { matters: Matter[] } = mattersRes.ok ? await mattersRes.json() : { matters: [] };

  return (
    <>
      <NavBar lawyerName={lawyer.name} lawyerEmail={lawyer.email} />
      <main className="page master-detail-shell" style={{ paddingTop: "var(--space-3)" }}>
        <div className="page-header" style={{ flexShrink: 0, marginTop: 0, marginBottom: "var(--space-2)" }}>
          <div className="row">
            <h1 style={{ fontSize: "var(--font-size-2xl)" }}>Clients</h1>
            <NewClientModal buttonClassName="btn-hold-bg btn-xs" />
          </div>
        </div>

        {!clientsRes.ok ? (
          <ErrorBanner>Couldn&apos;t load clients — retry.</ErrorBanner>
        ) : clients.length === 0 ? (
          <EmptyState
            title="No clients yet"
            body="Add your first client to start opening Matters and uploading documents."
            action={<NewClientModal />}
          />
        ) : (
          <ClientsMasterDetail clients={clients} matters={matters} />
        )}
      </main>
    </>
  );
}
