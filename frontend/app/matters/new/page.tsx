import Link from "next/link";
import { redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
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

  return (
    <main className="page" style={{ maxWidth: 480 }}>
      <Link href="/matters" className="text-sm">
        ← Matters
      </Link>
      <h1 style={{ fontSize: "var(--font-size-2xl)", margin: "var(--space-3) 0 var(--space-4)" }}>New Matter</h1>
      <NewMatterForm clients={clients} initialClientId={clientId} />
    </main>
  );
}
