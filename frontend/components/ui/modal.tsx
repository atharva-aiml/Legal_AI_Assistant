"use client";

import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";

export function Modal({
  title,
  onClose,
  children,
  width = 480,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  width?: number;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    // Move focus into the dialog so keyboard/screen-reader users land inside it immediately.
    panelRef.current?.focus();
    const previouslyFocused = document.activeElement as HTMLElement | null;
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [onClose]);

  if (typeof document === "undefined") return null;

  return createPortal(
    <div
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(26, 32, 41, 0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--space-4)",
        zIndex: 100,
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
        className="card"
        style={{
          width: "100%",
          maxWidth: width,
          maxHeight: "calc(100dvh - var(--space-8))",
          overflowY: "auto",
          boxShadow: "var(--shadow-lg)",
        }}
      >
        <div className="row-between" style={{ marginBottom: "var(--space-4)" }}>
          <h2 id="modal-title" style={{ fontSize: "var(--font-size-lg)" }}>{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="btn btn-ghost btn-sm"
            style={{ width: 32, padding: 0 }}
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>,
    document.body
  );
}
