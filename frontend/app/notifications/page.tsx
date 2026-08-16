import { redirect } from "next/navigation";
import { javaFetch } from "@/lib/api/java-client";
import { NavBar } from "@/components/nav-bar";
import { ErrorBanner } from "@/components/ui/error-banner";
import { NotificationsList } from "./notifications-list";

type Lawyer = { name: string; email: string };
type Notification = { id: string; deadlineId: string; message: string; readAt: string | null; createdAt: string };

export default async function NotificationsPage() {
  const meRes = await javaFetch("/api/auth/me");
  if (!meRes.ok) redirect("/login");
  const { lawyer }: { lawyer: Lawyer } = await meRes.json();

  const notificationsRes = await javaFetch("/api/notifications");
  const { notifications }: { notifications: Notification[] } = notificationsRes.ok
    ? await notificationsRes.json()
    : { notifications: [] };

  return (
    <>
      <NavBar lawyerName={lawyer.name} lawyerEmail={lawyer.email} />
      <main className="page">
        <h1 style={{ fontSize: "var(--font-size-2xl)", margin: "var(--space-5) 0 var(--space-4)" }}>Notifications</h1>
        {notificationsRes.ok ? (
          <NotificationsList initialNotifications={notifications} />
        ) : (
          <ErrorBanner>Couldn&apos;t load notifications — retry.</ErrorBanner>
        )}
      </main>
    </>
  );
}
