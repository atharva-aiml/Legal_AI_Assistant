"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { TooltipBubble } from "@/components/ui/tooltip-bubble";

function ChevronIcon() {
  return (
    <svg className="sort-toggle-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

/**
 * Plain-text trigger + chevron that opens an .overlay-panel listbox on click —
 * the one sort-control look shared by the dashboard, Matters list, and Clients
 * list, instead of each screen styling its own <select> or toggle button.
 */
export function SortDropdown<T extends string>({
  value,
  options,
  onChange,
  buttonLabel,
  menuLabel,
  align = "right",
  icon,
  iconOnly,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
  /** Overrides the button text (e.g. a compact "Sort" vs. the full current option label). */
  buttonLabel?: string;
  menuLabel: string;
  align?: "left" | "right";
  /** Leading glyph shown before the label (or alone, when `iconOnly`) — e.g. a filter/sort/person icon. */
  icon?: ReactNode;
  /** Renders as a bare icon button (no text label, no chevron) — used on Clients/Matters list filter & sort controls. */
  iconOnly?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const current = options.find((o) => o.value === value);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        type="button"
        className={`sort-toggle-btn${iconOnly ? " sort-toggle-btn-icon-only" : ""}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={iconOnly ? menuLabel : undefined}
        onClick={() => setOpen((o) => !o)}
      >
        {icon}
        {!iconOnly && (
          <>
            {buttonLabel ?? current?.label ?? "Sort"}
            <ChevronIcon />
          </>
        )}
        {iconOnly && <TooltipBubble label={menuLabel} />}
      </button>
      {open && (
        <div
          role="listbox"
          aria-label={menuLabel}
          className="overlay-panel"
          style={{ [align]: 0, top: "calc(100% + 4px)", width: 200, padding: "var(--space-1)", maxHeight: 320, overflowY: "auto" }}
        >
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="option"
              aria-selected={opt.value === value}
              className="nav-item sort-menu-item"
              style={{ display: "flex", width: "100%", height: 36, border: "none", background: "none", cursor: "pointer", textAlign: "left" }}
              onClick={() => {
                onChange(opt.value);
                setOpen(false);
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
