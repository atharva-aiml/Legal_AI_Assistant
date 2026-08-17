import Link from "next/link";
import { redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { QuickStatCard } from "@/components/ui/quick-stat-card";

type Lawyer = { name: string; email: string };
type Matter = { id: string; title: string; status: "open" | "closed"; clientId: string };
type Client = { id: string; name: string };
type Deadline = { id: string; matterId: string; title: string; dueDate: string; status: "open" | "complete" };
type NotificationRow = { id: string; readAt: string | null };

function formatDueDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default async function DashboardPage() {
  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");
  const { lawyer }: { lawyer: Lawyer } = await meRes.json();

  const [mattersRes, deadlinesRes, clientsRes, recentMattersRes, weekDeadlinesRes, notificationsRes, allDeadlinesRes] = await Promise.all([
    javaFetch("/api/matters"),
    javaFetch("/api/deadlines/upcoming?days=14"),
    javaFetch("/api/clients"),
    javaFetch("/api/matters/recent"),
    javaFetch("/api/deadlines/upcoming?days=7"),
    javaFetch("/api/notifications"),
    javaFetch("/api/deadlines/upcoming?days=36500"), // every open Deadline, not just a near-term slice — same approach as I-19/I-24/I-25
  ]);
  const { matters }: { matters: Matter[] } = mattersRes.ok ? await mattersRes.json() : { matters: [] };
  const { deadlines }: { deadlines: Deadline[] } = deadlinesRes.ok ? await deadlinesRes.json() : { deadlines: [] };
  const { clients }: { clients: Client[] } = clientsRes.ok ? await clientsRes.json() : { clients: [] };
  const { matters: recentMatters }: { matters: Matter[] } = recentMattersRes.ok ? await recentMattersRes.json() : { matters: [] };
  const { deadlines: weekDeadlines }: { deadlines: Deadline[] } = weekDeadlinesRes.ok ? await weekDeadlinesRes.json() : { deadlines: [] };
  const { notifications }: { notifications: NotificationRow[] } = notificationsRes.ok ? await notificationsRes.json() : { notifications: [] };
  const { deadlines: allDeadlines }: { deadlines: Deadline[] } = allDeadlinesRes.ok ? await allDeadlinesRes.json() : { deadlines: [] };

  const matterById = new Map(matters.map((m) => [m.id, m]));
  const clientNameById = new Map(clients.map((c) => [c.id, c.name]));
  const upcomingDeadlines = [...deadlines].sort((a, b) => a.dueDate.localeCompare(b.dueDate));
  const activeMatters = matters.filter((m) => m.status === "open").slice(0, 8);
  const isFirstLogin = clientsRes.ok && clients.length === 0 && matters.length === 0;

  // Next-deadline-per-Matter, shown on the Recent/Active Matters rows below —
  // /api/deadlines/upcoming already scopes to status=open, so no further filtering needed.
  const nextDeadlineByMatter = new Map<string, string>();
  for (const d of allDeadlines) {
    const current = nextDeadlineByMatter.get(d.matterId);
    if (!current || d.dueDate < current) nextDeadlineByMatter.set(d.matterId, d.dueDate);
  }

  // I-09: three counts a lawyer would otherwise get by reading every list below.
  const statTiles = [
    {
      label: "Open Matters",
      value: matters.filter((m) => m.status === "open").length,
      ok: mattersRes.ok,
      icon: "matters" as const,
      tone: "primary" as const,
      seeAllHref: "/matters?status=open",
    },
    {
      label: "Deadlines this week",
      value: weekDeadlines.length,
      ok: weekDeadlinesRes.ok,
      icon: "deadlines" as const,
      tone: "warning" as const,
      seeAllHref: "#upcoming-deadlines",
    },
    {
      label: "Unread notifications",
      value: notifications.filter((n) => n.readAt === null).length,
      ok: notificationsRes.ok,
      icon: "notifications" as const,
      tone: "info" as const,
      seeAllHref: "/notifications",
    },
  ];

  return (
    <>
      <NavBar lawyerName={lawyer.name} lawyerEmail={lawyer.email} />
      <main className="page">
        <div className="page-header">
          <h1 style={{ fontSize: "var(--font-size-2xl)" }}>Dashboard</h1>
          {!isFirstLogin && (
            <div className="row">
              <Button href="/clients/new" variant="secondary">+ New Client</Button>
              <Button href="/matters/new">+ New Matter</Button>
            </div>
          )}
        </div>

        {isFirstLogin ? (
          <EmptyState
            title="Welcome to Legal AI Assistant"
            body="Add your first client to get started — you'll be able to open a Matter and upload documents right after."
            action={<Button href="/clients/new">Add your first client</Button>}
          />
        ) : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--space-3)", margin: "0 0 var(--space-5)" }}>
              {statTiles.map((tile) => (
                <QuickStatCard
                  key={tile.label}
                  value={tile.ok ? tile.value : "—"}
                  label={tile.label}
                  icon={tile.icon}
                  tone={tile.tone}
                  seeAllHref={tile.seeAllHref}
                />
              ))}
            </div>

            <h2 id="upcoming-deadlines" style={{ fontSize: "var(--font-size-xl)", margin: "0 0 var(--space-3)" }}>Upcoming Deadlines</h2>
            {!deadlinesRes.ok ? (
              <ErrorBanner>Couldn&apos;t load deadlines — retry.</ErrorBanner>
            ) : upcomingDeadlines.length === 0 ? (
              <div className="card text-secondary">No deadlines in the next 14 days.</div>
            ) : (
              <div className="stack">
                {upcomingDeadlines.map((d) => {
                  const matter = matterById.get(d.matterId);
                  return (
                    <Link key={d.id} href={`/matters/${d.matterId}#deadlines`} className="card">
                      <div className="row-between">
                        <div>
                          <div style={{ fontWeight: 500 }}>{d.title}</div>
                          <div className="text-tertiary text-sm">{matter?.title ?? "Matter"}</div>
                        </div>
                        <div className="text-tertiary text-sm mono">{formatDueDate(d.dueDate)}</div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}

            {recentMatters.length > 0 && (
              <>
                <h2 style={{ fontSize: "var(--font-size-xl)", margin: "var(--space-5) 0 var(--space-3)" }}>Recent Matters</h2>
                <div className="stack">
                  {recentMatters.map((matter) => {
                    const nextDeadline = nextDeadlineByMatter.get(matter.id);
                    return (
                      <Link key={matter.id} href={`/matters/${matter.id}`} className="card">
                        <div className="row-between">
                          <div>
                            <div style={{ fontWeight: 500 }}>{matter.title}</div>
                            <div className="text-tertiary text-sm">{clientNameById.get(matter.clientId)}</div>
                          </div>
                          <div className="row" style={{ gap: "var(--space-3)" }}>
                            <span className="text-tertiary text-sm mono">{nextDeadline ? formatDueDate(nextDeadline) : "No deadline"}</span>
                            <StatusBadge status={matter.status} />
                          </div>
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </>
            )}

            <h2 style={{ fontSize: "var(--font-size-xl)", margin: "var(--space-5) 0 var(--space-3)" }}>Active Matters</h2>
            {!mattersRes.ok ? (
              <ErrorBanner>Couldn&apos;t load matters — retry.</ErrorBanner>
            ) : activeMatters.length === 0 ? (
              <div className="card text-secondary">
                No active matters — <Link href="/matters/new">start one</Link>.
              </div>
            ) : (
              <div className="stack">
                {activeMatters.map((matter) => {
                  const nextDeadline = nextDeadlineByMatter.get(matter.id);
                  return (
                    <Link key={matter.id} href={`/matters/${matter.id}`} className="card">
                      <div className="row-between">
                        <div>
                          <div style={{ fontWeight: 500 }}>{matter.title}</div>
                          <div className="text-tertiary text-sm">{clientNameById.get(matter.clientId)}</div>
                        </div>
                        <div className="row" style={{ gap: "var(--space-3)" }}>
                          <span className="text-tertiary text-sm mono">{nextDeadline ? formatDueDate(nextDeadline) : "No deadline"}</span>
                          <StatusBadge status={matter.status} />
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </>
        )}
      </main>
    </>
  );
}
