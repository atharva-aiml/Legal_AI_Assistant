import { Badge } from "@/components/ui/badge";

export function StatusBadge({ status }: { status: "open" | "closed" }) {
  return <Badge variant={status === "open" ? "info" : "neutral"}>{status === "open" ? "Open" : "Closed"}</Badge>;
}
