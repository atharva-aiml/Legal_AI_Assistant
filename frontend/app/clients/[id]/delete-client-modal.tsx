"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Modal } from "@/components/ui/modal";
import { TrashIcon } from "@/components/ui/trash-icon";
import { useToast } from "@/components/toast-context";

/**
 * Irreversible, high-blast-radius operation: deleting a Client
 * cascade-deletes every Matter under it, and every Document/Deadline/
 * chat-history under each of those (ClientController's DELETE
 * /api/clients/{id}, backed by ClientService.deleteCascade). No existing
 * confirmation-dialog component in this codebase — CloseMatterButton uses
 * a bare `confirm()` for a *reversible* action (BR-007: closing keeps
 * everything visible), but that's too thin a surface for something this
 * destructive, so this reuses the Modal component instead, same shape as
 * EditClientModal, to show the Client's name and an explicit warning
 * alongside Cancel and a destructive Delete button.
 */
export function DeleteClientModal({ clientId, clientName, onDeleted }: { clientId: string; clientName: string; onDeleted: () => void }) {
  const router = useRouter();
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

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/clients/${clientId}`, {
      method: "DELETE",
      credentials: "include",
    });

    setSubmitting(false);

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't delete this client — retry.");
      return;
    }

    setOpen(false);
    showToast("Client deleted");
    onDeleted();
    router.refresh();
  }

  if (!open) {
    return (
      <button type="button" className="delete-icon-btn" onClick={() => setOpen(true)} aria-label="Delete client">
        <TrashIcon />
      </button>
    );
  }

  return (
    <Modal title="Delete client?" onClose={reset} width={480}>
      <div className="stack-4">
        <p style={{ margin: 0 }}>
          This permanently deletes <strong>{clientName}</strong> and cannot be undone. Every Matter under this
          client — and each Matter&apos;s Documents, Deadlines, and chat history — will be deleted too.
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
