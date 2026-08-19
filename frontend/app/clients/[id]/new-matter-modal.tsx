"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { NewMatterForm } from "@/app/matters/new/new-matter-form";

type Client = { id: string; name: string };

/**
 * Same NewMatterForm used by /matters/new — opened as a modal instead of a
 * separate page, mirroring EditClientModal. `clientId` pre-fills the form's
 * Client combobox when opened from a specific Client's page (still editable,
 * exactly as it already was when /matters/new was reached via ?clientId=);
 * omitted when opened from the top-level Matters page, where there's no
 * specific Client in context — the combobox just starts blank/first-in-list,
 * same as /matters/new without a query param. Either way, this only changes
 * the entry point; field set, validation, and the post-create redirect to
 * /matters/[id] are all unchanged.
 */
export function NewMatterModal({
  clientId,
  clients,
  buttonClassName = "btn-hold-bg",
}: {
  clientId?: string;
  clients: Client[];
  buttonClassName?: string;
}) {
  const [open, setOpen] = useState(false);

  if (!open) {
    return (
      <Button className={buttonClassName} onClick={() => setOpen(true)}>
        <span className="btn-plus-icon">+</span> New Matter
      </Button>
    );
  }

  return (
    <Modal title="New Matter" onClose={() => setOpen(false)} width={480}>
      <NewMatterForm clients={clients} initialClientId={clientId} />
    </Modal>
  );
}
