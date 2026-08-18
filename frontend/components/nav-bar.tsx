"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AccountMenu } from "@/components/account-menu";
import { NotificationBell } from "@/components/notification-bell";
import { useListSearch } from "@/components/list-search-context";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";

// Routes where the topbar bar filters that page's own list in place
// instead of submitting to the global cross-entity /search page.
const LIST_FILTER_PLACEHOLDER: Record<string, string> = {
  "/clients": "Filter clients by name…",
};

function isNavLinkActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function navLinkClass(pathname: string, href: string): string {
  return isNavLinkActive(pathname, href) ? "app-nav-link app-nav-link-active" : "app-nav-link";
}

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  );
}

export function NavBar({ lawyerName, lawyerEmail }: { lawyerName: string; lawyerEmail: string }) {
  const pathname = usePathname();
  const { query, setQuery } = useListSearch();
  const filterPlaceholder = LIST_FILTER_PLACEHOLDER[pathname];
  const isListFilterMode = filterPlaceholder !== undefined;

  // I-48: kept uncontrolled (no `value` prop) so the existing native-form
  // GET-submission behavior is never at risk — only `isEmpty` (updated via
  // a plain onChange) drives whether the suggestions dropdown can show.
  const [isEmpty, setIsEmpty] = useState(true);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [recentQueries, setRecentQueries] = useState<string[] | null>(null);

  // Scoped to the page it filters — leaving clears it, so a later visit
  // (or the global search bar elsewhere) doesn't silently start pre-filled.
  useEffect(() => {
    if (!isListFilterMode) setQuery("");
  }, [isListFilterMode, setQuery]);

  function loadRecentSearches() {
    if (recentQueries !== null) return; // fetched once per mount, not on every focus
    fetch(`${JAVA_API_URL_PUBLIC}/api/search/recent`, { credentials: "include" })
      .then((res) => (res.ok ? res.json() : null))
      .then((body: { queries: string[] } | null) => setRecentQueries(body?.queries ?? []))
      .catch(() => setRecentQueries([]));
  }

  return (
    <nav className="app-nav" aria-label="Primary">
      <Link href="/" className="app-nav-brand">
        Legal AI Assistant
      </Link>
      <div className="app-nav-links">
        <Link href="/" className={navLinkClass(pathname, "/")}>
          Dashboard
        </Link>
        <Link href="/clients" className={navLinkClass(pathname, "/clients")}>
          Clients
        </Link>
        <Link href="/matters" className={navLinkClass(pathname, "/matters")}>
          Matters
        </Link>
      </div>

      {isListFilterMode ? (
        <div className="app-nav-search" role="search">
          <span className="app-nav-search-icon" aria-hidden="true">
            <SearchIcon />
          </span>
          <label htmlFor="global-search" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
            {filterPlaceholder}
          </label>
          <input
            id="global-search"
            type="text"
            className="app-nav-search-input"
            placeholder={filterPlaceholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      ) : (
        <form action="/search" method="GET" className="app-nav-search" role="search">
          <span className="app-nav-search-icon" aria-hidden="true">
            <SearchIcon />
          </span>
          <label htmlFor="global-search" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
            Search Clients and Matters
          </label>
          <input
            id="global-search"
            type="text"
            name="q"
            placeholder="Search Clients & Matters…"
            className="app-nav-search-input"
            autoComplete="off"
            defaultValue=""
            onChange={(e) => setIsEmpty(e.target.value.trim() === "")}
            onFocus={() => {
              loadRecentSearches();
              setShowSuggestions(true);
            }}
            onBlur={() => setShowSuggestions(false)}
          />
          {showSuggestions && isEmpty && recentQueries && recentQueries.length > 0 && (
            <ul
              role="listbox"
              aria-label="Recent searches"
              style={{
                position: "absolute",
                zIndex: 10,
                top: "100%",
                left: 0,
                right: 0,
                marginTop: 4,
                maxHeight: 220,
                overflowY: "auto",
                background: "var(--color-bg-surface)",
                border: "1px solid var(--color-border-default)",
                borderRadius: "var(--radius-md)",
                boxShadow: "var(--shadow-md)",
                listStyle: "none",
                padding: 4,
              }}
            >
              {recentQueries.map((q) => (
                <li key={q} role="option" aria-selected={false}>
                  <Link
                    href={`/search?q=${encodeURIComponent(q)}`}
                    onMouseDown={(e) => e.preventDefault()}
                    style={{
                      display: "block",
                      padding: "var(--space-2) var(--space-3)",
                      borderRadius: "var(--radius-sm)",
                      color: "inherit",
                      textDecoration: "none",
                    }}
                  >
                    {q}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </form>
      )}

      <div className="app-nav-actions">
        <NotificationBell />
        <AccountMenu name={lawyerName} email={lawyerEmail} />
      </div>
    </nav>
  );
}
