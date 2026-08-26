"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { NewClientForm } from "./new-client-form";

/**
 * Same NewClientForm used by /clients/new — opened as a modal instead of a
 * separate page, mirroring NewMatterModal. Also opens itself automatically
 * when the page is reached as /clients?new=1 (the dashboard's "New Client"
 * button navigates here rather than embedding the modal on the dashboard
 * itself), stripping the param back off once open so it doesn't re-trigger
 * on refresh/back-navigation.
 */
export function NewClientModal({ buttonClassName = "btn-hold-bg" }: { buttonClassName?: string }) {
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
    return (
      <Button className={buttonClassName} onClick={() => setOpen(true)}>
        <span className="btn-plus-icon">+</span> New Client
      </Button>
    );
  }

  return (
    <Modal title="New Client" onClose={() => setOpen(false)} width={480}>
      <NewClientForm />
    </Modal>
  );
}
