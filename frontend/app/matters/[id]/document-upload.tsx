"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";

export function DocumentUpload({ matterId }: { matterId: string }) {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    setUploading(true);

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/documents`, {
      method: "POST",
      credentials: "include",
      body: formData,
    });

    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't upload this file — retry.");
      return;
    }

    router.refresh();
  }

  return (
    <div>
      {/* A real, keyboard-operable button drives the file picker — the
          native input stays hidden but is never removed from the tab
          order's reach, since the button (not a `<label>` over a
          display:none input) is what receives focus and Enter/Space. */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,image/png,image/jpeg,image/tiff,image/webp"
        onChange={handleFileChange}
        disabled={uploading}
        style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}
        tabIndex={-1}
        aria-hidden="true"
        id="document-upload-input"
      />
      <Button type="button" variant="secondary" loading={uploading} onClick={() => fileInputRef.current?.click()}>
        {uploading ? "Uploading…" : "Upload Document"}
      </Button>
      {error && (
        <div style={{ marginTop: "var(--space-2)" }}>
          <ErrorBanner>{error}</ErrorBanner>
        </div>
      )}
    </div>
  );
}
