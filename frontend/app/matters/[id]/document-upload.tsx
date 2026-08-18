"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";

type UploadItem = {
  id: string;
  fileName: string;
  progress: number; // 0-100, I-38: real bytes-sent progress, not an indeterminate spinner
  status: "uploading" | "error";
  errorMessage?: string;
};

/**
 * I-38: fetch has no upload-progress event — XMLHttpRequest's
 * `upload.onprogress` is the only way to get real bytes-sent percentages
 * for a file this size, so this one call uses XHR instead of the fetch
 * used everywhere else in this codebase.
 */
function uploadWithProgress(matterId: string, file: File, onProgress: (pct: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/documents`);
    xhr.withCredentials = true; // XHR's equivalent of fetch's credentials: "include"
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
        return;
      }
      let message = "Couldn't upload this file — retry.";
      try {
        const body = JSON.parse(xhr.responseText);
        message = body?.error?.message ?? message;
      } catch {
        // non-JSON error body — keep the generic message
      }
      reject(new Error(message));
    };
    xhr.onerror = () => reject(new Error("Couldn't upload this file — retry."));

    const formData = new FormData();
    formData.append("file", file);
    xhr.send(formData);
  });
}

export function DocumentUpload({ matterId, onUpdated }: { matterId: string; onUpdated?: () => void }) {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  // I-37: each file gets its own item and its own request — one file
  // failing (a bad type, a network blip) never blocks or rolls back the rest.
  function uploadFiles(files: FileList | File[]) {
    for (const file of Array.from(files)) {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      setUploads((prev) => [...prev, { id, fileName: file.name, progress: 0, status: "uploading" }]);

      uploadWithProgress(matterId, file, (pct) => {
        setUploads((prev) => prev.map((u) => (u.id === id ? { ...u, progress: pct } : u)));
      })
        .then(() => {
          // The real Document row already exists server-side at this point
          // (DocumentService.upload sets it to "processing" before this
          // response returns) — DocumentsList's own polling takes over the
          // Processing -> Ready progression from here, unchanged.
          setUploads((prev) => prev.filter((u) => u.id !== id));
          if (onUpdated) onUpdated();
          else router.refresh();
        })
        .catch((err: Error) => {
          setUploads((prev) => prev.map((u) => (u.id === id ? { ...u, status: "error", errorMessage: err.message } : u)));
        });
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files.length > 0) uploadFiles(e.target.files);
    e.target.value = "";
  }

  // I-36: drag-and-drop over the whole Documents section, not just the button.
  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDraggingOver(false);
    if (e.dataTransfer.files.length > 0) uploadFiles(e.dataTransfer.files);
  }

  function dismissError(id: string) {
    setUploads((prev) => prev.filter((u) => u.id !== id));
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDraggingOver(true);
      }}
      onDragLeave={() => setIsDraggingOver(false)}
      onDrop={handleDrop}
      data-testid="document-drop-zone"
      style={{
        border: isDraggingOver ? "2px dashed var(--color-brand-500)" : "2px solid transparent",
        borderRadius: "var(--radius-md)",
        padding: "var(--space-2)",
        margin: "calc(-1 * var(--space-2))",
        background: isDraggingOver ? "var(--color-bg-selected)" : "transparent",
        transition: "border-color 120ms ease, background-color 120ms ease",
      }}
    >
      {/* A real, keyboard-operable button drives the file picker — the
          native input stays hidden but is never removed from the tab
          order's reach, since the button (not a `<label>` over a
          display:none input) is what receives focus and Enter/Space. */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,image/png,image/jpeg,image/tiff,image/webp"
        onChange={handleFileChange}
        style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}
        tabIndex={-1}
        aria-hidden="true"
        id="document-upload-input"
      />
      <Button type="button" variant="secondary" onClick={() => fileInputRef.current?.click()}>
        Upload Document
      </Button>
      <span className="text-tertiary text-xs" style={{ marginLeft: "var(--space-2)" }}>
        or drag files here
      </span>

      {uploads.length > 0 && (
        <div className="stack" style={{ marginTop: "var(--space-3)", gap: "var(--space-2)" }}>
          {uploads.map((u) => (
            <div key={u.id} className="card" style={{ padding: "var(--space-2) var(--space-3)" }}>
              <div className="row-between" style={{ gap: "var(--space-3)" }}>
                <span className="text-sm" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {u.fileName}
                </span>
                {u.status === "uploading" ? (
                  <span className="text-tertiary text-sm mono" style={{ flexShrink: 0 }}>{u.progress}%</span>
                ) : (
                  <button type="button" className="btn-link" style={{ flexShrink: 0 }} onClick={() => dismissError(u.id)}>
                    Dismiss
                  </button>
                )}
              </div>
              {u.status === "uploading" ? (
                <div
                  role="progressbar"
                  aria-valuenow={u.progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`Uploading ${u.fileName}`}
                  style={{ height: 4, background: "var(--color-neutral-200)", borderRadius: "var(--radius-full)", marginTop: "var(--space-2)", overflow: "hidden" }}
                >
                  <div style={{ height: "100%", width: `${u.progress}%`, background: "var(--color-brand-600)", transition: "width 120ms ease" }} />
                </div>
              ) : (
                <div className="text-xs" style={{ color: "var(--color-error-text)", marginTop: "var(--space-1)" }}>
                  {u.errorMessage}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
