"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { TooltipBubble } from "@/components/ui/tooltip-bubble";
import { PlusIcon } from "@/components/ui/plus-icon";
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
 *
 * Also opens itself automatically when the page is reached as
 * /matters?new=1 (the dashboard's "New Matter" button navigates here rather
 * than embedding the modal on the dashboard itself), stripping the param
 * back off once open so it doesn't re-trigger on refresh/back-navigation.
 */
export function NewMatterModal({
  clientId,
  clients,
  buttonClassName = "btn-hold-bg",
  iconOnly,
}: {
  clientId?: string;
  clients: Client[];
  buttonClassName?: string;
  /** Renders the trigger as a bare "+" icon (no background/border/text) instead of the "New Matter" button — used on the /clients master-detail panel. */
  iconOnly?: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (searchParams.get("new") === "1") {
      setOpen(true);
      router.replace(pathname);
    }
    // Only ever meant to fire once, off the URL this component mounted with.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!open) {
    if (iconOnly) {
      return (
        <button type="button" className="add-icon-btn" onClick={() => setOpen(true)} aria-label="New Matter">
          <PlusIcon />
          <TooltipBubble label="New Matter" below />
        </button>
      );
    }
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
