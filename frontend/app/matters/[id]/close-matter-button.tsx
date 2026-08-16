"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";

type OpenDeadline = { id: string; title: string; dueDate: string };

export function CloseMatterButton({ matterId }: { matterId: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [blockingDeadlines, setBlockingDeadlines] = useState<OpenDeadline[]>([]);
  const [submitting, setSubmitting] = useState(false);

  async function handleClose() {
    if (!confirm("Close this Matter? Its Documents, Chat, and Deadlines remain visible afterward (BR-007).")) return;

    setSubmitting(true);
    setError(null);
    setBlockingDeadlines([]);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/close`, {
      method: "POST",
      credentials: "include",
    });

    setSubmitting(false);

    if (res.ok) {
      router.refresh();
      return;
    }

    const body = await res.json().catch(() => null);
    if (res.status === 409) {
      setError(body?.error?.message ?? "This Matter has open Deadlines.");
      setBlockingDeadlines(body?.error?.openDeadlines ?? []);
      return;
    }

    setError(body?.error?.message ?? "Couldn't close this matter — retry.");
  }

  return (
    <div>
      <Button variant="secondary" onClick={handleClose} loading={submitting}>
        {submitting ? "Closing…" : "Close Matter"}
      </Button>
      {error && (
        <div style={{ marginTop: "var(--space-3)", maxWidth: 480 }}>
          <ErrorBanner>
            <div>{error}</div>
            {blockingDeadlines.length > 0 && (
              <ul style={{ margin: "var(--space-2) 0 0", paddingLeft: "var(--space-4)" }}>
                {blockingDeadlines.map((d) => (
                  <li key={d.id}>
                    <Link href="#deadlines">{d.title}</Link>
                  </li>
                ))}
              </ul>
            )}
          </ErrorBanner>
        </div>
      )}
    </div>
  );
}
