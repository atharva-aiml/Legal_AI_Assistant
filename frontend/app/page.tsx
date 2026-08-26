import { redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorBanner } from "@/components/ui/error-banner";
import { HollowPlusIcon } from "@/components/ui/hollow-plus-icon";
import { DashboardCalendar } from "./dashboard-calendar";
import { ActiveMattersPanel } from "./active-matters-panel";
import { RecentMattersPanel } from "./recent-matters-panel";
import { QuickStatsPanel } from "./quick-stats-panel";

type Lawyer = { name: string; email: string };
type Matter = { id: string; title: string; status: "open" | "closed"; clientId: string };
type Client = { id: string; name: string };
type Deadline = { id: string; matterId: string; title: string; dueDate: string; status: "open" | "complete" };
type NotificationRow = { id: string; deadlineId: string; message: string; readAt: string | null; createdAt: string };

function todayISO(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export default async function DashboardPage() {
  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");
  const { lawyer }: { lawyer: Lawyer } = await meRes.json();

  const [mattersRes, clientsRes, recentMattersRes, weekDeadlinesRes, notificationsRes, allDeadlinesRes] = await Promise.all([
    javaFetch("/api/matters"),
    javaFetch("/api/clients"),
    javaFetch("/api/matters/recent"),
    javaFetch("/api/deadlines/upcoming?days=7"),
    javaFetch("/api/notifications"),
    javaFetch("/api/deadlines/upcoming?days=36500"), // every open Deadline — feeds the Calendar and every "next deadline" lookup below
  ]);
  const { matters }: { matters: Matter[] } = mattersRes.ok ? await mattersRes.json() : { matters: [] };
  const { clients }: { clients: Client[] } = clientsRes.ok ? await clientsRes.json() : { clients: [] };
  const { matters: recentMatters }: { matters: Matter[] } = recentMattersRes.ok ? await recentMattersRes.json() : { matters: [] };
  const { deadlines: weekDeadlines }: { deadlines: Deadline[] } = weekDeadlinesRes.ok ? await weekDeadlinesRes.json() : { deadlines: [] };
  const { notifications }: { notifications: NotificationRow[] } = notificationsRes.ok ? await notificationsRes.json() : { notifications: [] };
  const { deadlines: allDeadlines }: { deadlines: Deadline[] } = allDeadlinesRes.ok ? await allDeadlinesRes.json() : { deadlines: [] };

  const clientNameByIdPlain: Record<string, string> = Object.fromEntries(clients.map((c) => [c.id, c.name]));
  const matterTitleById: Record<string, string> = Object.fromEntries(matters.map((m) => [m.id, m.title]));
  // Full open set, not pre-capped — ActiveMattersPanel sorts client-side (default
  // order or next-deadline) and THEN slices to its display cap, so "next deadline"
  // surfaces the true most-urgent Matters rather than re-ordering a static top-8.
  const activeMatters = matters.filter((m) => m.status === "open");
  const isFirstLogin = clientsRes.ok && clients.length === 0 && matters.length === 0;
  const today = todayISO();

  // Next-deadline-per-Matter, shown on the Active/Recent Matters cards below —
  // /api/deadlines/upcoming already scopes to status=open, so no further filtering needed.
  const nextDeadlineByMatter = new Map<string, string>();
  const nextDeadlineByIdPlain: Record<string, string> = {};
  for (const d of allDeadlines) {
    const current = nextDeadlineByMatter.get(d.matterId);
    if (!current || d.dueDate < current) {
      nextDeadlineByMatter.set(d.matterId, d.dueDate);
      nextDeadlineByIdPlain[d.matterId] = d.dueDate;
    }
  }

  // I-09: three counts a lawyer would otherwise get by reading every list below.
  const statTiles = [
    {
      label: "Open Matters",
      value: matters.filter((m) => m.status === "open").length,
      ok: mattersRes.ok,
      icon: "matters" as const,
      tone: "primary" as const,
      popup: "matters" as const,
    },
    {
      label: "Deadlines this week",
      value: weekDeadlines.length,
      ok: weekDeadlinesRes.ok,
      icon: "deadlines" as const,
      tone: "warning" as const,
      popup: "deadlines" as const,
    },
    {
      label: "Unread notifications",
      value: notifications.filter((n) => n.readAt === null).length,
      ok: notificationsRes.ok,
      icon: "notifications" as const,
      tone: "info" as const,
      popup: "notifications" as const,
    },
  ];

  if (isFirstLogin) {
    return (
      <>
        <NavBar lawyerName={lawyer.name} lawyerEmail={lawyer.email} />
        <main className="page">
          <div className="page-header">
            <h1 style={{ fontSize: "var(--font-size-2xl)" }}>Dashboard</h1>
          </div>
          <EmptyState
            title="Welcome to Legal AI Assistant"
            body="Add your first client to get started — you'll be able to open a Matter and upload documents right after."
            action={<Button href="/clients/new">Add your first client</Button>}
          />
        </main>
      </>
    );
  }

  return (
    <>
      <NavBar lawyerName={lawyer.name} lawyerEmail={lawyer.email} />
      <main className="dashboard-shell">
        <div className="dashboard-header row-between">
          <h1 style={{ fontSize: "var(--font-size-2xl)" }}>Dashboard</h1>
          <div className="row">
            <Button href="/clients?new=1" variant="secondary" className="btn-plain">
              <HollowPlusIcon /> New Client
            </Button>
            <Button href="/matters?new=1" className="btn-hold-bg">
              <span className="btn-plus-icon">+</span> New Matter
            </Button>
          </div>
        </div>

        <div className="dashboard-grid">
          <div className="dashboard-col">
            <QuickStatsPanel
              statTiles={statTiles}
              activeMatters={activeMatters}
              weekDeadlines={weekDeadlines}
              unreadNotifications={notifications.filter((n) => n.readAt === null)}
              clientNameById={clientNameByIdPlain}
              matterTitleById={matterTitleById}
              today={today}
            />

            {!mattersRes.ok ? (
              <ErrorBanner>Couldn&apos;t load matters — retry.</ErrorBanner>
            ) : (
              <ActiveMattersPanel
                matters={activeMatters}
                nextDeadlineById={nextDeadlineByIdPlain}
                clientNameById={clientNameByIdPlain}
                today={today}
              />
            )}
          </div>

          <div className="dashboard-col">
            <DashboardCalendar deadlines={allDeadlines} matterTitleById={matterTitleById} />

            <RecentMattersPanel
              matters={recentMatters}
              nextDeadlineById={nextDeadlineByIdPlain}
              clientNameById={clientNameByIdPlain}
              today={today}
            />
          </div>
        </div>
      </main>
    </>
  );
}
