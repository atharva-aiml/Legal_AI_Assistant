"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
          <input id="email" className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
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
