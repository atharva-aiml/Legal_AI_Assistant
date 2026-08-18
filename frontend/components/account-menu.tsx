"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";

export function AccountMenu({ name, email }: { name: string; email: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  async function handleSignOut() {
    await fetch(`${JAVA_API_URL_PUBLIC}/api/auth/logout`, { method: "POST", credentials: "include" });
    router.push("/login");
    router.refresh();
  }

  const initial = name.trim().charAt(0).toUpperCase() || "?";

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Account menu"
        aria-haspopup="menu"
        aria-expanded={open}
        className="account-avatar-btn"
        style={{
          width: 36,
          height: 36,
          borderRadius: "var(--radius-full)",
          border: "1px solid var(--color-brand-700)",
          background: "var(--color-brand-600)",
          color: "var(--color-text-on-brand)",
          fontFamily: "var(--font-family-heading)",
          fontWeight: 600,
          fontSize: "var(--font-size-sm)",
          cursor: "pointer",
        }}
      >
        {initial}
      </button>
      {open && (
        <div
          role="menu"
          className="overlay-panel"
          style={{ right: 0, top: "calc(100% + 8px)", width: 260, padding: "var(--space-2)" }}
        >
          <div style={{ padding: "var(--space-3)" }}>
            <div style={{ fontWeight: 500 }}>{name}</div>
            <div className="text-tertiary text-sm">{email}</div>
          </div>
          <div style={{ borderTop: "1px solid var(--color-neutral-200)", margin: "var(--space-1) 0" }} />
          <Link href="/account" role="menuitem" className="nav-item" style={{ display: "flex", width: "100%", height: 36 }} onClick={() => setOpen(false)}>
            Account settings
          </Link>
          <Link href="/firm" role="menuitem" className="nav-item" style={{ display: "flex", width: "100%", height: 36 }} onClick={() => setOpen(false)}>
            Firm &amp; team
          </Link>
          <div style={{ borderTop: "1px solid var(--color-neutral-200)", margin: "var(--space-1) 0" }} />
          <button
            onClick={handleSignOut}
            role="menuitem"
            className="nav-item"
            style={{ display: "flex", width: "100%", height: 36, border: "none", background: "none", cursor: "pointer", textAlign: "left", color: "var(--color-error-text)" }}
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
