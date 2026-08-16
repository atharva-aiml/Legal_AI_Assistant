import { redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";

type Lawyer = { id: string; name: string; email: string; role: string };

export default async function FirmPage() {
  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");
  const { lawyer }: { lawyer: Lawyer } = await meRes.json();

  const lawyersRes = await javaFetch("/api/firm/lawyers");
  const { lawyers }: { lawyers: Lawyer[] } = lawyersRes.ok ? await lawyersRes.json() : { lawyers: [] };

  return (
    <>
      <NavBar lawyerName={lawyer.name} lawyerEmail={lawyer.email} />
      <main className="page" style={{ maxWidth: 640 }}>
        <div className="page-header">
          <h1 style={{ fontSize: "var(--font-size-2xl)" }}>Firm &amp; team</h1>
          <Button variant="secondary" disabled>
            Invite a lawyer
          </Button>
        </div>
        <p className="text-tertiary text-sm" style={{ marginTop: "calc(-1 * var(--space-3))", marginBottom: "var(--space-4)" }}>
          Inviting and removing team members is coming in a future release — this page shows your Firm&apos;s current members.
        </p>

        {!lawyersRes.ok ? (
          <ErrorBanner>Couldn&apos;t load your Firm&apos;s members — retry.</ErrorBanner>
        ) : (
          <div className="stack">
            {lawyers.map((l) => (
              <div key={l.id} className="card">
                <div className="row-between">
                  <div>
                    <div style={{ fontWeight: 500 }}>
                      {l.name} {l.id === lawyer.id && <span className="text-tertiary text-sm">(you)</span>}
                    </div>
                    <div className="text-tertiary text-sm">{l.email}</div>
                  </div>
                  <Badge variant="neutral">{l.role}</Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
