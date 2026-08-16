"use client";

import { useEffect, useState } from "react";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { DocumentStatusBadge } from "@/components/document-status-badge";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";

type Doc = {
  id: string;
  fileName: string;
  mimeType: string;
  sizeBytes: number;
  status: "uploading" | "processing" | "ready" | "failed";
  isDraft: boolean;
  errorMessage: string | null;
  createdAt: string;
};

const POLL_INTERVAL_MS = 3000;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentsList({ matterId, initialDocuments }: { matterId: string; initialDocuments: Doc[] }) {
  const [documents, setDocuments] = useState<Doc[]>(initialDocuments);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(doc: Doc) {
    if (!confirm(`Delete "${doc.fileName}"? This can't be undone.`)) return;

    setDeletingId(doc.id);
    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/documents/${doc.id}`, {
      method: "DELETE",
      credentials: "include",
    });
    setDeletingId(null);

    if (res.ok) {
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } else {
      alert("Couldn't delete this document — retry.");
    }
  }

  useEffect(() => {
    setDocuments(initialDocuments);
  }, [initialDocuments]);

  useEffect(() => {
    const hasPending = documents.some((d) => d.status === "uploading" || d.status === "processing");
    if (!hasPending) return;

    let cancelled = false;
    const timer = setTimeout(async () => {
      if (cancelled) return;
      const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/documents`, { credentials: "include" });
      if (!cancelled && res.ok) {
        const { documents: fresh } = await res.json();
        setDocuments(fresh);
      }
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [documents, matterId]);

  if (documents.length === 0) {
    return <EmptyState title="No documents yet" body="Upload a file to start asking the Assistant questions about it." />;
  }

  return (
    <div className="stack">
      {documents.map((doc) => (
        <div key={doc.id} className="card">
          <div className="row-between">
            <div>
              <div className="row" style={{ gap: "var(--space-2)" }}>
                <span style={{ fontWeight: 500 }}>{doc.fileName}</span>
                {doc.isDraft && <Badge variant="warning">Draft</Badge>}
              </div>
              <div className="text-tertiary text-sm">{formatBytes(doc.sizeBytes)}</div>
              {doc.status === "failed" && doc.errorMessage && (
                <div className="error-text" style={{ marginTop: "var(--space-2)" }}>
                  {doc.errorMessage}
                </div>
              )}
            </div>
            <div className="row">
              <DocumentStatusBadge status={doc.status} />
              <a href={`${JAVA_API_URL_PUBLIC}/api/documents/${doc.id}/download`} className="text-sm">
                Download
              </a>
              <button onClick={() => handleDelete(doc)} disabled={deletingId === doc.id} className="btn-link" style={{ color: "var(--color-error-text)" }}>
                {deletingId === doc.id ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
