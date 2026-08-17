"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import { PasswordStrengthMeter } from "@/components/ui/password-strength-meter";

// Shape check only — gates the availability check so we don't fire a
// network request on every keystroke of an obviously-incomplete address.
const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const DEBOUNCE_MS = 500;

type EmailAvailability = "idle" | "checking" | "available" | "taken";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [emailAvailability, setEmailAvailability] = useState<EmailAvailability>("idle");

  useEffect(() => {
    const trimmed = email.trim();
    if (!EMAIL_SHAPE.test(trimmed)) {
      setEmailAvailability("idle");
      return;
    }

    setEmailAvailability("checking");
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/auth/email-available?email=${encodeURIComponent(trimmed)}`, {
          credentials: "include",
        });
        if (!res.ok) {
          setEmailAvailability("idle");
          return;
        }
        const body = await res.json();
        setEmailAvailability(body.available ? "available" : "taken");
      } catch {
        setEmailAvailability("idle");
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [email]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ name, email, password }),
    });

    setSubmitting(false);

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't create your account — retry.");
      return;
    }

    router.push("/");
    router.refresh();
  }

  return (
    <main style={{ minHeight: "100dvh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "var(--space-6)" }}>
      <div style={{ marginBottom: "var(--space-6)", textAlign: "center" }}>
        <div style={{ fontFamily: "var(--font-family-heading)", fontWeight: 600, fontSize: "var(--font-size-xl)" }}>Legal AI Assistant</div>
        <div className="text-tertiary text-sm" style={{ marginTop: "var(--space-1)" }}>
          Grounded answers from your own case files
        </div>
      </div>

      <form onSubmit={handleSubmit} className="card stack-4" style={{ width: "100%", maxWidth: 380 }}>
        <h1 style={{ fontSize: "var(--font-size-lg)" }}>Create your account</h1>

        <div className="field">
          <label className="field-label" htmlFor="name">Name</label>
          <input id="name" className="input" value={name} onChange={(e) => setName(e.target.value)} required autoFocus autoComplete="name" />
        </div>
        <div className="field">
          <label className="field-label" htmlFor="email">Email</label>
          <input
            id="email"
            className={emailAvailability === "taken" ? "input input-error" : "input"}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            aria-invalid={emailAvailability === "taken" ? true : undefined}
            aria-describedby={emailAvailability === "taken" ? "email-taken-error" : undefined}
          />
          {emailAvailability === "checking" && (
            <span className="field-hint">Checking…</span>
          )}
          {emailAvailability === "taken" && (
            <span id="email-taken-error" className="field-error">
              Already registered — <Link href="/login">Log in?</Link>
            </span>
          )}
          {emailAvailability === "available" && (
            <span className="field-hint" style={{ color: "var(--color-success-base)" }}>Available</span>
          )}
        </div>
        <div className="field">
          <label className="field-label" htmlFor="password">Password</label>
          <input
            id="password"
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
            autoComplete="new-password"
          />
          <span className="field-hint">At least 8 characters.</span>
          <PasswordStrengthMeter password={password} />
        </div>

        {error && <ErrorBanner>{error}</ErrorBanner>}

        <Button type="submit" loading={submitting} style={{ width: "100%" }}>
          {submitting ? "Creating account…" : "Create account"}
        </Button>

        <div className="text-sm text-secondary" style={{ textAlign: "center" }}>
          Already have an account? <Link href="/login">Log in</Link>
        </div>
      </form>
    </main>
  );
}
