"use client";

import { useEffect, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { JAVA_API_URL_PUBLIC } from "@/lib/api/public-config";
import { ErrorBanner } from "@/components/ui/error-banner";
import { ThinkingDots } from "@/components/ui/thinking-dots";
import { AiVoiceVisualizer } from "@/components/ui/ai-voice-visualizer";
import { TooltipBubble } from "@/components/ui/tooltip-bubble";

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
  fullContext: boolean | null;
  pinned: boolean;
  parentId: string | null;
  /** Every sibling id at this message's position (including its own), oldest
   * first — length 1 unless this message has been edited. Present on every
   * message uniformly, but only ever >1 for a user message (only user
   * messages are editable). */
  siblingIds: string[];
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

function CopyIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

function RegenerateIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12a9 9 0 1 1-2.64-6.36" />
      <path d="M21 3v6h-6" />
    </svg>
  );
}

function SpeakerIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M15.5 8.5a5 5 0 0 1 0 7" />
      <path d="M18.5 5.5a9 9 0 0 1 0 13" />
    </svg>
  );
}

function SpeakerOffIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <line x1="23" y1="9" x2="17" y2="15" />
      <line x1="17" y1="9" x2="23" y2="15" />
    </svg>
  );
}

function PencilIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  );
}

function ChevronLeftIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m15 18-6-6 6-6" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m9 18 6-6-6-6" />
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

function MicIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
      <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
      <line x1="12" y1="18" x2="12" y2="22" />
      <line x1="8" y1="22" x2="16" y2="22" />
    </svg>
  );
}

function MaximizeIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 3H5a2 2 0 0 0-2 2v3" />
      <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
      <path d="M3 16v3a2 2 0 0 0 2 2h3" />
      <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
    </svg>
  );
}

function MinimizeIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 3v3a2 2 0 0 1-2 2H4" />
      <path d="M15 3v3a2 2 0 0 0 2 2h3" />
      <path d="M9 21v-3a2 2 0 0 0-2-2H4" />
      <path d="M15 21v-3a2 2 0 0 1 2-2h3" />
    </svg>
  );
}

export function ChatPanel({
  matterId,
  messages,
  setMessages,
  draft,
  setDraft,
  hasReadyDocuments: initialHasReadyDocuments,
  onDocumentsReady,
  fullHeight,
  maximized,
  onToggleMaximize,
}: {
  matterId: string;
  /** Conversation + unsent-draft state is owned by the parent
   * (MatterDetailPanel), not held internally — toggling maximize unmounts
   * this ChatPanel and mounts a structurally different one (portaled to
   * document.body), so internal state would be lost on every maximize /
   * minimize. */
  messages: ChatMsg[];
  setMessages: Dispatch<SetStateAction<ChatMsg[]>>;
  draft: string;
  setDraft: Dispatch<SetStateAction<string>>;
  hasReadyDocuments: boolean;
  /** Fired once when the readiness poll below first sees a ready Document, so
   * the parent can re-sync its own `documents` (and anything derived from it,
   * e.g. the "add a document" attention cue). */
  onDocumentsReady?: () => void;
  /** Fill the height of its container instead of the viewport-relative max-height
   * used when Chat sits in-flow below Deadlines/Documents — for the toggled
   * full-panel AI Chat view, which has nothing else sharing the space. */
  fullHeight?: boolean;
  /** Whether the enclosing full-panel AI Chat view is currently expanded to
   * fill the whole screen — purely presentational here, the parent owns the
   * actual overlay. Omit to hide the maximize button entirely. */
  maximized?: boolean;
  onToggleMaximize?: () => void;
}) {
  // Parent-owned (see props doc above); aliased so the rest of this
  // component keeps referring to `question`/`setQuestion` unchanged.
  const question = draft;
  const setQuestion = setDraft;
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasReadyDocuments, setHasReadyDocuments] = useState(initialHasReadyDocuments);
  const [pollTick, setPollTick] = useState(0);
  const [togglingPinId, setTogglingPinId] = useState<string | null>(null);
  const [listening, setListening] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [readingId, setReadingId] = useState<string | null>(null);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [branchSwitchingId, setBranchSwitchingId] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const prevMessageCount = useRef(messages.length);
  // Web Speech API has no bundled TS types (webkitSpeechRecognition is a
  // non-standard, vendor-prefixed constructor) — `any` is the recognition
  // instance itself, not a stand-in for a type that could've been written.
  const recognitionRef = useRef<any>(null);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  async function copyMessage(message: ChatMsg) {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedId(message.id);
      setTimeout(() => setCopiedId((id) => (id === message.id ? null : id)), 1500);
    } catch {
      setError("Couldn't copy — your browser blocked clipboard access.");
    }
  }

  function readAloud(message: ChatMsg) {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setError("Read aloud isn't supported in this browser.");
      return;
    }
    window.speechSynthesis.cancel();
    if (readingId === message.id) {
      setReadingId(null);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(message.content);
    utterance.onend = () => setReadingId((id) => (id === message.id ? null : id));
    utterance.onerror = () => setReadingId((id) => (id === message.id ? null : id));
    setReadingId(message.id);
    window.speechSynthesis.speak(utterance);
  }

  // Shared by sendQuestion and regenerate — posts a question, returns the
  // assistant's reply, or null (with `error` already set) on failure.
  async function postQuestion(text: string): Promise<ChatMsg | null> {
    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/chat`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't reach the Assistant — retry.");
      return null;
    }
    return res.json();
  }

  // Regenerating is really "re-ask the same preceding question" — that goes
  // through the exact same edit/branch endpoint as a real edit (with the
  // question text unchanged), so the old response isn't lost: it stays
  // reachable as a sibling version via the ‹ › switcher, same as ChatGPT.
  async function regenerate(message: ChatMsg) {
    if (sending || regeneratingId) return;
    const idx = messages.findIndex((m) => m.id === message.id);
    const precedingQuestion = idx > 0 ? messages[idx - 1] : null;
    if (!precedingQuestion || precedingQuestion.role !== "user") return;

    setRegeneratingId(message.id);
    setError(null);
    const newMessages = await postEdit(precedingQuestion.id, precedingQuestion.content);
    setRegeneratingId(null);
    if (newMessages) setMessages(newMessages);
  }

  // Shared by regenerate and submitEdit — creates a sibling version of
  // `messageId` with `question` as its new text, generates its response, and
  // returns the resulting full active conversation path (or null, with
  // `error` already set, on failure).
  async function postEdit(messageId: string, question: string): Promise<ChatMsg[] | null> {
    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/chat/${messageId}/edit`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(body?.error?.message ?? "Couldn't reach the Assistant — retry.");
      return null;
    }
    const { messages: newMessages }: { messages: ChatMsg[] } = await res.json();
    return newMessages;
  }

  function startEdit(message: ChatMsg) {
    setEditingId(message.id);
    setEditText(message.content);
  }

  function cancelEdit() {
    setEditingId(null);
    setEditText("");
  }

  async function submitEdit(message: ChatMsg) {
    const trimmed = editText.trim();
    if (!trimmed || sending) return;

    // Optimistic: submitting an edit replaces this question and everything
    // after it on the active path, so show the new question text in place
    // right away (edit box closed) with the thinking indicator beneath it —
    // don't sit on the pre-edit conversation until the server answers.
    const preEditMessages = messages;
    const editIndex = messages.findIndex((m) => m.id === message.id);
    const priorMessages = editIndex >= 0 ? messages.slice(0, editIndex) : messages;
    const optimisticEdited: ChatMsg = {
      ...message,
      id: `local-${Date.now()}`,
      content: trimmed,
      createdAt: new Date().toISOString(),
      citations: [],
      // Empty so no half-formed "‹ i/N ›" flashes before the real path arrives.
      siblingIds: [],
    };

    setEditingId(null);
    setEditText("");
    setError(null);
    setSending(true);
    setMessages([...priorMessages, optimisticEdited]);
    requestAnimationFrame(() => endRef.current?.scrollIntoView({ block: "end" }));

    const newMessages = await postEdit(message.id, trimmed);
    setSending(false);
    if (newMessages) {
      setMessages(newMessages);
    } else {
      // postEdit already set `error` — put the conversation back exactly as
      // it was and reopen the editor with the attempted text, so nothing
      // (the edit, or the turns that followed it) is silently dropped.
      setMessages(preEditMessages);
      setEditingId(message.id);
      setEditText(trimmed);
    }
  }

  async function switchBranch(message: ChatMsg, direction: "prev" | "next") {
    const idx = message.siblingIds.indexOf(message.id);
    // idx < 0 means siblingIds doesn't actually contain this message — treat
    // it as "no versions" rather than navigating off the start of the array
    // (which would activate an unrelated message).
    if (idx < 0) return;
    const targetId = direction === "prev" ? message.siblingIds[idx - 1] : message.siblingIds[idx + 1];
    if (!targetId || branchSwitchingId) return;

    setBranchSwitchingId(message.id);
    setError(null);
    const res = await fetch(`${JAVA_API_URL_PUBLIC}/api/matters/${matterId}/chat/${targetId}/activate`, {
      method: "PATCH",
      credentials: "include",
    });
    setBranchSwitchingId(null);
    if (!res.ok) {
      setError("Couldn't switch to that version — retry.");
      return;
    }
    const { messages: newMessages }: { messages: ChatMsg[] } = await res.json();
    setMessages(newMessages);
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
          onDocumentsReady?.();
          return;
        }
      }
      if (!cancelled) setPollTick((t) => t + 1);
    }, READY_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // onDocumentsReady is a fire-once notifier — deliberately not a dep, so a
    // new parent callback identity each render doesn't restart the poll timer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasReadyDocuments, pollTick, matterId]);

  useEffect(() => {
    // Only auto-scroll-on-append when a message was actually appended
    // (send/receive), not on mount — a boolean "have I run yet" ref doesn't
    // survive React 18 Strict Mode's dev-only double-invocation of effects
    // (it flips false on the first simulated pass, so the second pass —
    // same mount — still fires). Comparing the real message count is immune
    // to that, since both simulated passes see the same (unchanged) count
    // on mount.
    if (messages.length > prevMessageCount.current) {
      endRef.current?.scrollIntoView({ block: "end" });
    }
    prevMessageCount.current = messages.length;
  }, [messages]);

  // Opening AI Chat (or toggling maximize, which remounts this component —
  // it's portaled to document.body in the maximized case, a structurally
  // different render tree) should land on the latest message, not the top
  // of the conversation.
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function sendQuestion(rawText: string) {
    const trimmed = rawText.trim();
    if (!trimmed || sending) return;

    setQuestion("");
    setError(null);
    setSending(true);

    const optimisticId = `local-${Date.now()}`;
    const optimisticUserMessage: ChatMsg = {
      id: optimisticId,
      role: "user",
      content: trimmed,
      createdAt: new Date().toISOString(),
      citations: [],
      lowConfidence: null,
      fullContext: null,
      pinned: false,
      parentId: null,
      siblingIds: [],
    };
    setMessages((prev) => [...prev, optimisticUserMessage]);

    const assistantMessage = await postQuestion(trimmed);
    setSending(false);
    if (assistantMessage) {
      setMessages((prev) => {
        // The ask endpoint only returns the assistant reply, not the user
        // message it just persisted — but the reply's parentId IS that user
        // message's real id, which the edit/regenerate/branch features need
        // (the optimistic placeholder's id is a throwaway local one).
        const withRealUserId = prev.map((m) =>
          m.id === optimisticId && assistantMessage.parentId
            ? { ...m, id: assistantMessage.parentId, siblingIds: [assistantMessage.parentId] }
            : m
        );
        return [...withRealUserId, assistantMessage];
      });
    }
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    await sendQuestion(question);
  }

  function clearSilenceTimer() {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }

  function stopListening() {
    recognitionRef.current?.stop();
  }

  function startListening() {
    if (listening) {
      stopListening();
      return;
    }

    // Chrome/Edge ship this only under the vendor-prefixed name.
    const SpeechRecognitionCtor = (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setError("Voice input isn't supported in this browser.");
      return;
    }

    const recognition = new SpeechRecognitionCtor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    let transcript = "";

    recognition.onresult = (event: any) => {
      transcript = "";
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      setQuestion(transcript);

      // 3s of silence (no new result) auto-stops — stop() triggers onend,
      // which sends whatever was captured, same as a manual re-click.
      clearSilenceTimer();
      silenceTimerRef.current = setTimeout(() => recognition.stop(), 3000);
    };

    recognition.onerror = (event: any) => {
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        setError("Couldn't access the microphone — check your browser permissions.");
      }
    };

    recognition.onend = () => {
      clearSilenceTimer();
      setListening(false);
      recognitionRef.current = null;
      if (transcript.trim()) sendQuestion(transcript);
    };

    recognitionRef.current = recognition;
    setError(null);
    setListening(true);
    recognition.start();
    silenceTimerRef.current = setTimeout(() => recognition.stop(), 3000);
  }

  useEffect(() => {
    return () => {
      clearSilenceTimer();
      recognitionRef.current?.stop();
      if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
    };
  }, []);

  if (!hasReadyDocuments) {
    return (
      <div className={`chat-frame chat-frame-empty${fullHeight ? " chat-frame-full" : ""}`}>
        <p className="chat-empty-hint">Upload a document first — the Assistant answers from this Matter&apos;s Documents.</p>
      </div>
    );
  }

  const inputForm = (
    <>
      {listening && <AiVoiceVisualizer active={listening} />}
      <form onSubmit={handleSend} className="chat-input-bar">
      <input
        className="chat-input"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder={listening ? "Listening…" : "Send a message"}
        disabled={sending}
        aria-label="Ask a question"
      />
      <button
        type="button"
        className={`chat-mic-btn${listening ? " chat-mic-btn-active" : ""}`}
        onClick={startListening}
        disabled={sending}
        aria-pressed={listening}
        aria-label={listening ? "Stop dictating" : "Dictate your question"}
      >
        <MicIcon />
        <TooltipBubble label={listening ? "Stop dictating" : "Dictate your question"} />
      </button>
      <button type="submit" className="chat-send-btn" disabled={!question.trim() || sending} aria-label="Send">
        <SendIcon />
      </button>
      </form>
    </>
  );

  return (
    <div className={`chat-frame stack-4${fullHeight ? " chat-frame-full" : ""}`}>
      {onToggleMaximize && (
        <button
          type="button"
          className="chat-maximize-btn"
          onClick={onToggleMaximize}
          aria-pressed={maximized}
          aria-label={maximized ? "Minimize chat" : "Maximize chat"}
        >
          {maximized ? <MinimizeIcon /> : <MaximizeIcon />}
          <TooltipBubble label={maximized ? "Minimize chat" : "Maximize chat"} />
        </button>
      )}
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

      {messages.length === 0 ? (
        <div className="chat-hero">
          <div className="chat-hero-heading">What would you like to know about this Matter&apos;s Documents?</div>
          {inputForm}
        </div>
      ) : (
        <>
      <div className="chat-messages-scroll">
        <div className="stack-4">
          {messages.map((m) => (
            <div key={m.id} className={`chat-row${m.role === "user" ? " chat-row-user" : ""}`}>
              {m.role === "assistant" && <AiAvatar />}
              <div style={{ minWidth: 0, flex: m.role === "user" ? "0 1 auto" : 1, maxWidth: m.role === "user" ? "min(85%, 640px)" : undefined }}>
                {editingId === m.id ? (
                  <div className="chat-edit-box">
                    <textarea
                      className="textarea chat-edit-textarea"
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      autoFocus
                      rows={3}
                    />
                    <div className="row" style={{ gap: "var(--space-2)", marginTop: "var(--space-2)", justifyContent: "flex-end" }}>
                      <button type="button" className="btn btn-ghost btn-sm" onClick={cancelEdit} disabled={sending}>
                        Cancel
                      </button>
                      <button type="button" className="btn btn-primary btn-sm" onClick={() => submitEdit(m)} disabled={!editText.trim() || sending}>
                        {sending ? "Sending…" : "Save & submit"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="chat-bubble" style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
                )}

                {m.role === "user" && editingId !== m.id && (
                  <div className="row" style={{ gap: "var(--space-1)", marginTop: "var(--space-2)", justifyContent: "flex-end" }}>
                    {(() => {
                      // Only a real, self-consistent version set gets a switcher:
                      // siblingIds must contain this message. A -1 index here
                      // used to render "0/N" and let the arrows walk onto
                      // unrelated messages.
                      const versionIndex = m.siblingIds.indexOf(m.id);
                      if (versionIndex < 0 || m.siblingIds.length <= 1) return null;
                      return (
                      <div className="chat-branch-switcher">
                        <button
                          type="button"
                          className="chat-branch-btn"
                          onClick={() => switchBranch(m, "prev")}
                          disabled={branchSwitchingId === m.id || versionIndex === 0}
                          aria-label="Previous version"
                        >
                          <ChevronLeftIcon />
                          <TooltipBubble label="Previous version" />
                        </button>
                        <span className="text-xs text-tertiary mono">
                          {versionIndex + 1}/{m.siblingIds.length}
                        </span>
                        <button
                          type="button"
                          className="chat-branch-btn"
                          onClick={() => switchBranch(m, "next")}
                          disabled={branchSwitchingId === m.id || versionIndex === m.siblingIds.length - 1}
                          aria-label="Next version"
                        >
                          <ChevronRightIcon />
                          <TooltipBubble label="Next version" />
                        </button>
                      </div>
                      );
                    })()}
                    <button
                      type="button"
                      className="chat-icon-btn"
                      onClick={() => copyMessage(m)}
                      aria-label={copiedId === m.id ? "Copied" : "Copy question"}
                    >
                      {copiedId === m.id ? <CheckIcon /> : <CopyIcon />}
                      <TooltipBubble label={copiedId === m.id ? "Copied" : "Copy question"} />
                    </button>
                    <button
                      type="button"
                      className="chat-icon-btn"
                      onClick={() => startEdit(m)}
                      disabled={sending}
                      aria-label="Edit question"
                    >
                      <PencilIcon />
                      <TooltipBubble label="Edit question" />
                    </button>
                  </div>
                )}

                {m.role === "assistant" && (
                  <div className="row" style={{ gap: "var(--space-1)", marginTop: "var(--space-2)" }}>
                    <button
                      type="button"
                      className="chat-icon-btn"
                      onClick={() => copyMessage(m)}
                      aria-label={copiedId === m.id ? "Copied" : "Copy response"}
                    >
                      {copiedId === m.id ? <CheckIcon /> : <CopyIcon />}
                      <TooltipBubble label={copiedId === m.id ? "Copied" : "Copy response"} />
                    </button>
                    <button
                      type="button"
                      className="chat-icon-btn"
                      onClick={() => regenerate(m)}
                      disabled={sending || regeneratingId === m.id}
                      aria-label="Regenerate response"
                    >
                      <RegenerateIcon />
                      <TooltipBubble label="Regenerate response" />
                    </button>
                    <button
                      type="button"
                      className="chat-icon-btn"
                      onClick={() => readAloud(m)}
                      aria-pressed={readingId === m.id}
                      aria-label={readingId === m.id ? "Stop reading" : "Read aloud"}
                    >
                      {readingId === m.id ? <SpeakerOffIcon /> : <SpeakerIcon />}
                      <TooltipBubble label={readingId === m.id ? "Stop reading" : "Read aloud"} />
                    </button>
                    <button
                      type="button"
                      className="chat-icon-btn"
                      onClick={() => togglePin(m)}
                      disabled={togglingPinId === m.id}
                      aria-pressed={m.pinned}
                      aria-label={m.pinned ? "Unpin this answer" : "Pin this answer"}
                    >
                      <StarIcon filled={m.pinned} />
                      <TooltipBubble label={m.pinned ? "Unpin this answer" : "Pin this answer"} />
                    </button>
                  </div>
                )}
                {m.lowConfidence && (
                  <div className="text-xs text-tertiary" style={{ marginTop: "var(--space-2)" }}>
                    This answer is based on limited matching content — verify against the source documents.
                  </div>
                )}
                {m.fullContext === false && (
                  <div className="text-xs text-tertiary" style={{ marginTop: "var(--space-2)" }}>
                    This Matter is large — this answer used the most relevant sections rather than the
                    entire document. For a guaranteed complete answer, ask about a specific page, section,
                    table, or image.
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
              <div className="chat-bubble" style={{ width: "fit-content" }}>
                <ThinkingDots />
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      {inputForm}
        </>
      )}
    </div>
  );
}
