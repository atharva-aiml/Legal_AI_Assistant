"use client";

import { useState } from "react";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Modal } from "@/components/ui/modal";
import { TrashIcon } from "@/components/ui/trash-icon";
import { TooltipBubble } from "@/components/ui/tooltip-bubble";
import { useToast } from "@/components/toast-context";

/**
 * Irreversible, cascade-deletes this Matter's own Documents/Deadlines/
 * chat-history (MatterController's DELETE /api/matters/{id}, backed by
 * MatterService.deleteCascade — the same per-Matter cascade
 * ClientService.deleteCascade now delegates to for a whole-Client delete).
 * Same shape as DeleteClientModal: a bare delete-icon-btn trigger, gated by
 * a real confirmation Modal naming what's about to be lost, not a bare
 * confirm().
 */
export function DeleteMatterModal({ matterId, matterTitle, onDeleted, tooltipBelow }: { matterId: string; matterTitle: string; onDeleted: () => void; tooltipBelow?: boolean }) {
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setOpen(false);
    setError(null);
  }

  async function handleDelete() {
    setError(null);
    setSubmitting(true);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}`, {
      method: "DELETE",
      credentials: "include",
    });

    setSubmitting(false);

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't delete this matter — retry.");
      return;
    }

    setOpen(false);
    showToast("Matter deleted");
    onDeleted();
  }

  if (!open) {
    return (
      <button type="button" className="delete-icon-btn" onClick={() => setOpen(true)} aria-label="Delete matter">
        <TrashIcon />
        <TooltipBubble label="Delete matter" below={tooltipBelow} />
      </button>
    );
  }

  return (
    <Modal title="Delete matter?" onClose={reset} width={480}>
      <div className="stack-4">
        <p style={{ margin: 0 }}>
          This permanently deletes <strong>{matterTitle}</strong> and cannot be undone. Its Documents, Deadlines,
          and chat history will be deleted too.
        </p>

        {error && <ErrorBanner>{error}</ErrorBanner>}

        <div className="row">
          <Button type="button" variant="destructive" onClick={handleDelete} loading={submitting}>
            {submitting ? "Deleting…" : "Delete"}
          </Button>
          <Button type="button" variant="ghost" onClick={reset} disabled={submitting}>
            Cancel
          </Button>
        </div>
      </div>
    </Modal>
  );
}
