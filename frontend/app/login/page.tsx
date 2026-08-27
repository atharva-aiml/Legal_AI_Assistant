"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";

function EyeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M2 12c1.8-4.2 5.6-7 10-7s8.2 2.8 10 7c-1.8 4.2-5.6 7-10 7s-8.2-2.8-10-7Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M3 3l18 18M10.6 10.6a3 3 0 0 0 4.24 4.24M9.3 5.3C10.16 5.1 11.06 5 12 5c4.4 0 8.2 2.8 10 7-.6 1.4-1.44 2.66-2.47 3.71M6.6 6.6C4.7 7.9 3.2 9.8 2 12c1.8 4.2 5.6 7 10 7 1.27 0 2.48-.23 3.6-.66"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// Shape check only — not full RFC 5322. Good enough to catch an obviously
// malformed address before a round trip; the server remains the real
// authority on whether the address is registered.
const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleEmailBlur() {
    if (email.trim() !== "" && !EMAIL_SHAPE.test(email.trim())) {
      setEmailError("Enter a valid email");
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!EMAIL_SHAPE.test(email.trim())) {
      setEmailError("Enter a valid email");
      return;
    }

    setSubmitting(true);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });

    setSubmitting(false);

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't log in — retry.");
      return;
    }

    router.push("/");
    router.refresh();
  }

  return (
    <main style={{ minHeight: "100dvh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "var(--space-6)" }}>
      <div style={{ marginBottom: "var(--space-6)", textAlign: "center" }}>
        <div style={{ fontFamily: "var(--font-family-heading)", fontWeight: 700, letterSpacing: "-0.01em", fontSize: "var(--font-size-xl)" }}>Legal AI Assistant</div>
        <div className="text-tertiary text-sm" style={{ marginTop: "var(--space-1)" }}>
          Grounded answers from your own case files
        </div>
      </div>

      <form onSubmit={handleSubmit} className="card stack-4" style={{ width: "100%", maxWidth: 380 }}>
        <h1 style={{ fontSize: "var(--font-size-lg)" }}>Log in</h1>

        <div className="field">
          <label className="field-label" htmlFor="email">Email</label>
          <input
            id="email"
            className={emailError ? "input input-error" : "input"}
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (emailError) setEmailError(null);
            }}
            onBlur={handleEmailBlur}
            required
            autoFocus
            autoComplete="email"
            aria-invalid={emailError ? true : undefined}
            aria-describedby={emailError ? "email-error" : undefined}
          />
          {emailError && <span id="email-error" className="field-error">{emailError}</span>}
        </div>
        <div className="field">
          <label className="field-label" htmlFor="password">Password</label>
          <div style={{ position: "relative" }}>
            <input
              id="password"
              className="input"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              style={{ paddingRight: "var(--space-7)" }}
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              aria-pressed={showPassword}
              style={{
                position: "absolute",
                right: 0,
                top: 0,
                height: 40,
                width: 40,
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "var(--color-text-tertiary)",
              }}
            >
              {showPassword ? <EyeOffIcon /> : <EyeIcon />}
            </button>
          </div>
        </div>

        {error && <ErrorBanner>{error}</ErrorBanner>}

        <Button type="submit" loading={submitting} style={{ width: "100%" }}>
          {submitting ? "Logging in…" : "Log in"}
        </Button>

        <div className="text-sm text-secondary" style={{ textAlign: "center" }}>
          No account yet? <Link href="/register">Create one</Link>
        </div>
      </form>
    </main>
  );
}
