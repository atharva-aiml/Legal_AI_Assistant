"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { NewMatterForm } from "@/app/matters/new/new-matter-form";

type Client = { id: string; name: string };

/**
 * Same NewMatterForm used by /matters/new — opened as a modal instead of a
 * separate page, mirroring EditClientModal. The Client is already known
 * here (pre-filled into the form's Client combobox, which stays editable
 * exactly as it already was when /matters/new was reached via ?clientId=),
 * so this only changes the entry point; field set, validation, and the
 * post-create redirect to /matters/[id] are all unchanged.
 */
export function NewMatterModal({ clientId, clients }: { clientId: string; clients: Client[] }) {
  const [open, setOpen] = useState(false);

  if (!open) {
    return (
      <Button className="btn-hold-bg" onClick={() => setOpen(true)}>
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
