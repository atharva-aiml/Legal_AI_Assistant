import Link from "next/link";
import { AccountMenu } from "@/components/account-menu";
import { NotificationBell } from "@/components/notification-bell";

export function NavBar({ lawyerName, lawyerEmail }: { lawyerName: string; lawyerEmail: string }) {
  return (
    <nav className="app-nav" aria-label="Primary">
      <Link href="/" className="app-nav-brand">
        Legal AI Assistant
      </Link>
      <div className="app-nav-links">
        <Link href="/" className="nav-item">
          Dashboard
        </Link>
        <Link href="/clients" className="nav-item">
          Clients
        </Link>
        <Link href="/matters" className="nav-item">
          Matters
        </Link>
      </div>

      <form action="/search" method="GET" className="app-nav-search" role="search">
        <label htmlFor="global-search" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
          Search Clients and Matters
        </label>
        <input id="global-search" type="text" name="q" placeholder="Search Clients & Matters…" className="input" />
      </form>

      <div className="app-nav-actions">
        <NotificationBell />
        <AccountMenu name={lawyerName} email={lawyerEmail} />
      </div>
    </nav>
  );
}
