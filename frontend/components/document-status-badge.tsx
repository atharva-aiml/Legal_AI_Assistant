import { Badge } from "@/components/ui/badge";

type DocumentStatus = "uploading" | "processing" | "ready" | "failed";

const LABELS: Record<DocumentStatus, string> = {
  uploading: "Uploading",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

const VARIANTS: Record<DocumentStatus, "info" | "success" | "error"> = {
  uploading: "info",
  processing: "info",
  ready: "success",
  failed: "error",
};

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  return <Badge variant={VARIANTS[status]}>{LABELS[status]}</Badge>;
}
