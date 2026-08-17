"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";

export function ReopenMatterButton({ matterId }: { matterId: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleReopen() {
    if (!confirm("Reopen this Matter? Upload and New Deadline become available again.")) return;

    setSubmitting(true);
    setError(null);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/reopen`, {
      method: "POST",
      credentials: "include",
    });

    setSubmitting(false);

    if (res.ok) {
      router.refresh();
      return;
    }

    const body = await res.json().catch(() => null);
    setError(body?.error?.message ?? "Couldn't reopen this matter — retry.");
  }

  return (
    <div>
      <Button variant="secondary" onClick={handleReopen} loading={submitting}>
        {submitting ? "Reopening…" : "Reopen Matter"}
      </Button>
      {error && (
        <div style={{ marginTop: "var(--space-3)", maxWidth: 480 }}>
          <ErrorBanner>{error}</ErrorBanner>
        </div>
      )}
    </div>
  );
}
