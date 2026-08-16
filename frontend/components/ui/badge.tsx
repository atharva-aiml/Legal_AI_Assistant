import type { ReactNode } from "react";

type Variant = "neutral" | "info" | "success" | "warning" | "error";

export function Badge({ variant, children }: { variant: Variant; children: ReactNode }) {
  return <span className={`badge badge-${variant}`}>{children}</span>;
}
