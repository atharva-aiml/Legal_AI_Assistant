"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Modal } from "@/components/ui/modal";
import { SkeletonRows } from "@/components/ui/skeleton";

type Template = { id: string; name: string; description: string | null; placeholders: string[] };

export function GenerateDraftModal({
  matterId,
  matterTitle,
  clientName,
}: {
  matterId: string;
  matterTitle: string;
  clientName: string | null;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [templates, setTemplates] = useState<Template[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open || templates !== null) return;
    setLoadingTemplates(true);
    fetch(`${JAVA_API_URL_PUBLIC}/api/templates`, { credentials: "include" })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((body: { templates: Template[] }) => setTemplates(body.templates))
      .catch(() => setTemplates([]))
      .finally(() => setLoadingTemplates(false));
  }, [open, templates]);

  function selectTemplate(template: Template) {
    setSelectedId(template.id);
    setError(null);
    const prefilled: Record<string, string> = {};
    for (const placeholder of template.placeholders) {
      if (placeholder === "client_name") prefilled[placeholder] = clientName ?? "";
      else if (placeholder === "matter_title") prefilled[placeholder] = matterTitle;
      else prefilled[placeholder] = "";
    }
    setFields(prefilled);
  }

  function reset() {
    setOpen(false);
    setSelectedId(null);
    setFields({});
    setError(null);
  }

  async function handleGenerate() {
    if (!selectedId) return;
    setSubmitting(true);
    setError(null);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/documents/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ template_id: selectedId, fields }),
    });

    setSubmitting(false);

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't generate document — retry.");
      return; // entered edits are preserved — `fields`/`selectedId` state is untouched
    }

    reset();
    router.refresh();
  }

  const selectedTemplate = templates?.find((t) => t.id === selectedId) ?? null;

  if (!open) {
    return (
      <Button variant="secondary" onClick={() => setOpen(true)}>
        Generate Document
      </Button>
    );
  }

  return (
    <Modal title="Generate Document" onClose={reset} width={520}>
      {loadingTemplates && <SkeletonRows count={2} />}

      {!loadingTemplates && templates !== null && templates.length === 0 && (
        <div className="text-secondary">No templates available.</div>
      )}

      {!loadingTemplates && templates !== null && templates.length > 0 && !selectedTemplate && (
        <div className="stack">
          {templates.map((t) => (
            <button key={t.id} type="button" onClick={() => selectTemplate(t)} className="card" style={{ textAlign: "left", cursor: "pointer" }}>
              <div style={{ fontWeight: 500 }}>{t.name}</div>
              {t.description && <div className="text-tertiary text-sm">{t.description}</div>}
            </button>
          ))}
        </div>
      )}

      {selectedTemplate && (
        <div className="stack-4">
          <div className="text-tertiary text-sm">
            Template: <strong style={{ color: "var(--color-text-primary)" }}>{selectedTemplate.name}</strong> —{" "}
            <button type="button" onClick={() => setSelectedId(null)} className="btn-link">
              choose a different template
            </button>
          </div>

          {selectedTemplate.placeholders.map((placeholder) => (
            <div className="field" key={placeholder}>
              <label className="field-label" htmlFor={`field-${placeholder}`} style={{ textTransform: "capitalize" }}>
                {placeholder.replace(/_/g, " ")} *
              </label>
              <input
                id={`field-${placeholder}`}
                className="input"
                value={fields[placeholder] ?? ""}
                onChange={(e) => setFields((prev) => ({ ...prev, [placeholder]: e.target.value }))}
              />
            </div>
          ))}

          {error && <ErrorBanner>{error}</ErrorBanner>}

          <div className="row">
            <Button type="button" onClick={handleGenerate} loading={submitting}>
              {submitting ? "Generating…" : "Generate"}
            </Button>
            <Button type="button" variant="ghost" onClick={reset} disabled={submitting}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
