import { redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { Breadcrumb, type BreadcrumbItem } from "@/components/ui/breadcrumb";
import { NewMatterForm } from "./new-matter-form";

type Client = { id: string; name: string };

export default async function NewMatterPage({
  searchParams,
}: {
  searchParams: Promise<{ clientId?: string }>;
}) {
  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");

  const { clientId } = await searchParams;
  const clientsRes = await javaFetch("/api/clients");
  const { clients }: { clients: Client[] } = clientsRes.ok ? await clientsRes.json() : { clients: [] };

  // I-55: launched from a Client's page (clientId set) gets the real Client → New Matter
  // path; launched from the top-level Matters list falls back to Matters → New Matter.
  const launchingClient = clientId ? clients.find((c) => c.id === clientId) : undefined;
  const breadcrumbItems: BreadcrumbItem[] = launchingClient
    ? [{ label: "Clients", href: "/clients" }, { label: launchingClient.name, href: `/clients/${launchingClient.id}` }, { label: "New Matter" }]
    : [{ label: "Matters", href: "/matters" }, { label: "New Matter" }];

  return (
    <main className="page" style={{ maxWidth: 480 }}>
      <Breadcrumb items={breadcrumbItems} />
      <h1 style={{ fontSize: "var(--font-size-2xl)", margin: "var(--space-3) 0 var(--space-4)" }}>New Matter</h1>
      <NewMatterForm clients={clients} initialClientId={clientId} />
    </main>
  );
}
