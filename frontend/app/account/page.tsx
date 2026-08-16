import { redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { LogoutButton } from "./logout-button";

type Lawyer = { id: string; name: string; email: string; role: string };

export default async function AccountPage() {
  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");
  const { lawyer }: { lawyer: Lawyer } = await meRes.json();

  const initial = lawyer.name.trim().charAt(0).toUpperCase() || "?";

  return (
    <>
      <NavBar lawyerName={lawyer.name} lawyerEmail={lawyer.email} />
      <main className="page" style={{ maxWidth: 560 }}>
        <h1 style={{ fontSize: "var(--font-size-2xl)", margin: "var(--space-5) 0 var(--space-4)" }}>Account settings</h1>

        <div className="card">
          <div className="row" style={{ marginBottom: "var(--space-5)" }}>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: "var(--radius-full)",
                background: "var(--color-brand-600)",
                color: "var(--color-text-on-brand)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "var(--font-family-heading)",
                fontWeight: 600,
                fontSize: "var(--font-size-lg)",
                flexShrink: 0,
              }}
              aria-hidden="true"
            >
              {initial}
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: "var(--font-size-md)" }}>{lawyer.name}</div>
              <div className="text-tertiary text-sm">{lawyer.email}</div>
            </div>
          </div>

          <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "var(--space-4)" }}>
            <div>
              <dt className="field-label" style={{ marginBottom: "var(--space-1)" }}>Role</dt>
              <dd style={{ margin: 0, textTransform: "capitalize" }}>{lawyer.role}</dd>
            </div>
            <div>
              <dt className="field-label" style={{ marginBottom: "var(--space-1)" }}>Email</dt>
              <dd style={{ margin: 0 }}>{lawyer.email}</dd>
            </div>
          </dl>
        </div>

        <div className="card" style={{ marginTop: "var(--space-4)" }}>
          <div className="row-between">
            <div>
              <div style={{ fontWeight: 500 }}>Sign out</div>
              <div className="text-tertiary text-sm">End your session on this device.</div>
            </div>
            <LogoutButton />
          </div>
        </div>
      </main>
    </>
  );
}
