"use client";

import { useEffect, useRef, useState } from "react";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";

const READY_POLL_INTERVAL_MS = 3000;

type Citation = {
  id: string;
  documentId: string | null;
  fileName: string | null;
  pageNumber: number | null;
  excerpt: string | null;
};

type ChatMsg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  citations: Citation[];
  lowConfidence: boolean | null;
  pinned: boolean;
};

export function ChatPanel({
  matterId,
  initialMessages,
  hasReadyDocuments: initialHasReadyDocuments,
}: {
  matterId: string;
  initialMessages: ChatMsg[];
  hasReadyDocuments: boolean;
}) {
  const [messages, setMessages] = useState<ChatMsg[]>(initialMessages);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasReadyDocuments, setHasReadyDocuments] = useState(initialHasReadyDocuments);
  const [pollTick, setPollTick] = useState(0);
  const [togglingPinId, setTogglingPinId] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  // I-34: derived from the same messages already fetched/held in state — no separate "pinned" request.
  const pinnedMessages = messages.filter((m) => m.pinned);

  async function togglePin(message: ChatMsg) {
    setTogglingPinId(message.id);
    const nextPinned = !message.pinned;
    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/chat/${message.id}/pin`, {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pinned: nextPinned }),
    });
    setTogglingPinId(null);
    if (res.ok) {
      setMessages((prev) => prev.map((m) => (m.id === message.id ? { ...m, pinned: nextPinned } : m)));
    }
  }

  useEffect(() => {
    if (hasReadyDocuments) return;

    let cancelled = false;
    const timer = setTimeout(async () => {
      if (cancelled) return;
      const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/documents`, { credentials: "include" });
      if (cancelled) return;
      if (res.ok) {
        const { documents } = await res.json();
        if (documents.some((d: { status: string }) => d.status === "ready")) {
          setHasReadyDocuments(true);
          return;
        }
      }
      if (!cancelled) setPollTick((t) => t + 1);
    }, READY_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [hasReadyDocuments, pollTick, matterId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, sending]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || sending) return;

    setQuestion("");
    setError(null);
    setSending(true);

    const optimisticUserMessage: ChatMsg = {
      id: `local-${Date.now()}`,
      role: "user",
      content: trimmed,
      createdAt: new Date().toISOString(),
      citations: [],
      lowConfidence: null,
      pinned: false,
    };
    setMessages((prev) => [...prev, optimisticUserMessage]);

    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/chat`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: trimmed }),
    });

    setSending(false);

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't reach the Assistant — retry.");
      return;
    }

    const assistantMessage: ChatMsg = await res.json();
    setMessages((prev) => [...prev, assistantMessage]);
  }

  if (!hasReadyDocuments) {
    return <div className="card text-tertiary">Upload a document first — the Assistant answers from this Matter&apos;s Documents.</div>;
  }

  return (
    <div className="card stack-4">
      {pinnedMessages.length > 0 && (
        <div className="stack" style={{ gap: "var(--space-2)", paddingBottom: "var(--space-4)", borderBottom: "1px solid var(--color-border-default)" }}>
          <span className="field-label" style={{ margin: 0 }}>Pinned</span>
          {pinnedMessages.map((m) => (
            <div
              key={m.id}
              className="row-between"
              style={{ padding: "var(--space-2) var(--space-3)", background: "var(--color-bg-selected)", borderRadius: "var(--radius-md)", gap: "var(--space-3)" }}
            >
              <div className="text-sm" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.content}</div>
              <button type="button" className="btn-link" onClick={() => togglePin(m)} disabled={togglingPinId === m.id}>
                Unpin
              </button>
            </div>
          ))}
        </div>
      )}

      {messages.length === 0 ? (
        <div className="text-tertiary text-sm">Ask a question about this Matter&apos;s Documents.</div>
      ) : (
        <div className="stack-4">
          {messages.map((m) => (
            <div key={m.id} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "min(85%, 640px)" }}>
              {m.role === "assistant" && (
                <div className="text-ai text-xs" style={{ fontWeight: 600, letterSpacing: "0.04em", marginBottom: "var(--space-1)" }}>
                  AI
                </div>
              )}
              <div
                style={{
                  padding: "var(--space-3)",
                  borderRadius: "var(--radius-md)",
                  background: m.role === "user" ? "var(--color-bg-selected)" : "var(--color-ai-50)",
                  border: m.role === "user" ? "1px solid var(--color-primary-200)" : "1px solid var(--color-ai-200)",
                  whiteSpace: "pre-wrap",
                }}
              >
                {m.content}
              </div>
              {m.role === "assistant" && (
                <button
                  type="button"
                  className="btn-link"
                  onClick={() => togglePin(m)}
                  disabled={togglingPinId === m.id}
                  aria-pressed={m.pinned}
                  aria-label={m.pinned ? "Unpin this answer" : "Pin this answer"}
                  style={{ fontSize: "var(--font-size-xs)", marginTop: "var(--space-2)" }}
                >
                  {m.pinned ? "★ Pinned" : "☆ Pin"}
                </button>
              )}
              {m.lowConfidence && (
                <div className="text-xs text-tertiary" style={{ marginTop: "var(--space-2)" }}>
                  This answer is based on limited matching content — verify against the source documents.
                </div>
              )}
              {m.citations.length > 0 && (
                <div className="stack" style={{ gap: "var(--space-1)", marginTop: "var(--space-2)" }}>
                  {m.citations.map((c) => (
                    <div key={c.id} className="text-xs mono">
                      {c.documentId ? (
                        <a className="text-citation" href={`${JAVA_API_URL_PUBLIC}/api/documents/${c.documentId}/download`} target="_blank" rel="noreferrer">
                          {c.fileName ?? "source document"}
                          {c.pageNumber != null ? `, p.${c.pageNumber}` : ""}
                        </a>
                      ) : (
                        <span className="text-tertiary">{c.fileName ?? "source document"} (deleted)</span>
                      )}
                      {c.excerpt && <span className="text-tertiary"> — &quot;{c.excerpt}&quot;</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          {sending && (
            <div style={{ alignSelf: "flex-start" }} aria-live="polite">
              <div
                className="row"
                style={{
                  padding: "var(--space-3)",
                  borderRadius: "var(--radius-md)",
                  background: "var(--color-ai-50)",
                  border: "1px solid var(--color-ai-200)",
                  gap: "var(--space-2)",
                }}
              >
                <span className="spinner spinner-dark" aria-hidden="true" />
                <span className="text-ai text-sm">Thinking…</span>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
      )}

      {error && <ErrorBanner>{error}</ErrorBanner>}

      <form onSubmit={handleSend} className="row">
        <input
          className="input"
          style={{ flex: 1 }}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about this Matter's documents…"
          disabled={sending}
          aria-label="Ask a question"
        />
        <Button type="submit" disabled={!question.trim()} loading={sending}>
          {sending ? "Asking…" : "Ask"}
        </Button>
      </form>
    </div>
  );
}
