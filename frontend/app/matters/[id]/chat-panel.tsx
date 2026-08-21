"use client";

import { useEffect, useRef, useState } from "react";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { ErrorBanner } from "@/components/ui/error-banner";

const READY_POLL_INTERVAL_MS = 3000;

type Citation = {
  id: string;
  documentId: string | null;
  fileName: string | null;
  pageNumber: number | null;
  section: string | null;
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

/** Sparkle icon — the same --color-ai-* tokens as .text-ai elsewhere, now as an avatar badge instead of a text label. */
function AiAvatar() {
  return (
    <span className="chat-avatar chat-avatar-ai" aria-hidden="true">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2.5c.4 2.9 1.1 4.9 2.1 5.9s3 1.7 5.9 2.1c-2.9.4-4.9 1.1-5.9 2.1s-1.7 3-2.1 5.9c-.4-2.9-1.1-4.9-2.1-5.9S6.9 11 4 10.6c2.9-.4 4.9-1.1 5.9-2.1S11.6 5.4 12 2.5Z" />
      </svg>
    </span>
  );
}

function StarIcon({ filled }: { filled: boolean }) {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 2 3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2Z" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 2 11 13" />
      <path d="M22 2 15 22l-4-9-9-4 20-7Z" />
    </svg>
  );
}

export function ChatPanel({
  matterId,
  initialMessages,
  hasReadyDocuments: initialHasReadyDocuments,
  fullHeight,
}: {
  matterId: string;
  initialMessages: ChatMsg[];
  hasReadyDocuments: boolean;
  /** Fill the height of its container instead of the viewport-relative max-height
   * used when Chat sits in-flow below Deadlines/Documents — for the toggled
   * full-panel AI Chat view, which has nothing else sharing the space. */
  fullHeight?: boolean;
}) {
  const [messages, setMessages] = useState<ChatMsg[]>(initialMessages);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasReadyDocuments, setHasReadyDocuments] = useState(initialHasReadyDocuments);
  const [pollTick, setPollTick] = useState(0);
  const [togglingPinId, setTogglingPinId] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const prevMessageCount = useRef(initialMessages.length);

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
    // Only scroll when a message was actually appended (send/receive), not
    // on mount — a boolean "have I run yet" ref doesn't survive React 18
    // Strict Mode's dev-only double-invocation of effects (it flips false
    // on the first simulated pass, so the second pass — same mount — still
    // fires). Comparing the real message count is immune to that, since
    // both simulated passes see the same (unchanged) count on mount.
    if (messages.length > prevMessageCount.current) {
      endRef.current?.scrollIntoView({ block: "end" });
    }
    prevMessageCount.current = messages.length;
  }, [messages]);

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
    <div className={`card chat-frame stack-4${fullHeight ? " chat-frame-full" : ""}`}>
      {pinnedMessages.length > 0 && (
        <div className="stack" style={{ gap: "var(--space-2)", paddingBottom: "var(--space-4)", borderBottom: "1px solid var(--color-border-default)" }}>
          <span className="field-label" style={{ margin: 0 }}>Pinned</span>
          {pinnedMessages.map((m) => (
            <div
              key={m.id}
              className="row-between"
              style={{ padding: "var(--space-2) var(--space-3)", background: "var(--color-bg-surface-sunken)", borderRadius: "var(--radius-md)", gap: "var(--space-3)" }}
            >
              <div className="text-sm" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.content}</div>
              <button type="button" className="btn-link" onClick={() => togglePin(m)} disabled={togglingPinId === m.id}>
                Unpin
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="chat-messages-scroll">
      {messages.length === 0 ? (
        <div className="text-tertiary text-sm">Ask a question about this Matter&apos;s Documents.</div>
      ) : (
        <div className="stack-4">
          {messages.map((m) => (
            <div key={m.id} className={`chat-row${m.role === "user" ? " chat-row-user" : ""}`}>
              {m.role === "assistant" && <AiAvatar />}
              <div style={{ minWidth: 0, flex: m.role === "user" ? "0 1 auto" : 1, maxWidth: m.role === "user" ? "min(85%, 640px)" : undefined }}>
                <div className="chat-bubble" style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>

                {m.role === "assistant" && (
                  <div className="row" style={{ gap: "var(--space-1)", marginTop: "var(--space-2)" }}>
                    <button
                      type="button"
                      className="chat-icon-btn"
                      onClick={() => togglePin(m)}
                      disabled={togglingPinId === m.id}
                      aria-pressed={m.pinned}
                      aria-label={m.pinned ? "Unpin this answer" : "Pin this answer"}
                      title={m.pinned ? "Unpin this answer" : "Pin this answer"}
                    >
                      <StarIcon filled={m.pinned} />
                    </button>
                  </div>
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
                            {c.section ? `, ${c.section}` : ""}
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
            </div>
          ))}
          {sending && (
            <div className="chat-row" aria-live="polite">
              <AiAvatar />
              <div className="chat-bubble row" style={{ gap: "var(--space-2)", width: "fit-content" }}>
                <span className="spinner spinner-dark" aria-hidden="true" />
                <span className="text-tertiary text-sm">Thinking…</span>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
      )}
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      <form onSubmit={handleSend} className="chat-input-bar">
        <input
          className="chat-input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Send a message"
          disabled={sending}
          aria-label="Ask a question"
        />
        <button type="submit" className="chat-send-btn" disabled={!question.trim() || sending} aria-label="Send">
          <SendIcon />
        </button>
      </form>
    </div>
  );
}
