import { Breadcrumb } from "@/components/ui/breadcrumb";
import { NewClientForm } from "./new-client-form";

export default function NewClientPage() {
  return (
    <main className="page" style={{ maxWidth: 480 }}>
      <Breadcrumb items={[{ label: "Clients", href: "/clients" }, { label: "New Client" }]} />
      <h1 style={{ fontSize: "var(--font-size-2xl)", margin: "var(--space-3) 0 var(--space-4)" }}>New Client</h1>
      <NewClientForm />
    </main>
  );
}
