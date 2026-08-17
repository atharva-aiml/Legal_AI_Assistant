"use client";

import { useMemo, useState } from "react";

type Client = { id: string; name: string };

/**
 * I-27: a searchable combobox replacing the plain <select> — typing filters
 * the option list, but `clientId` (the value actually submitted) only ever
 * changes via an explicit selection, never merely from typing. Abandoning a
 * search (blur/Escape without picking) reverts the visible text back to
 * whatever's still selected, so the displayed name and the submitted
 * `client_id` can never silently disagree.
 */
export function ClientCombobox({ clients, clientId, onChange }: { clients: Client[]; clientId: string; onChange: (id: string) => void }) {
  const [query, setQuery] = useState(() => clients.find((c) => c.id === clientId)?.name ?? "");
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const filtered = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    return trimmed ? clients.filter((c) => c.name.toLowerCase().includes(trimmed)) : clients;
  }, [clients, query]);

  function selectClient(c: Client) {
    onChange(c.id);
    setQuery(c.name);
    setIsOpen(false);
  }

  function revertAndClose() {
    setIsOpen(false);
    setQuery(clients.find((c) => c.id === clientId)?.name ?? "");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setIsOpen(true);
      setHighlightedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      if (isOpen) {
        e.preventDefault();
        if (filtered[highlightedIndex]) selectClient(filtered[highlightedIndex]);
      }
    } else if (e.key === "Escape") {
      revertAndClose();
    }
  }

  return (
    <div className="field" style={{ position: "relative" }}>
      <label className="field-label" htmlFor="clientId-combobox">Client *</label>
      <input
        id="clientId-combobox"
        className="input"
        role="combobox"
        aria-expanded={isOpen}
        aria-controls="clientId-listbox"
        aria-autocomplete="list"
        autoComplete="off"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setIsOpen(true);
          setHighlightedIndex(0);
        }}
        onFocus={() => setIsOpen(true)}
        onKeyDown={handleKeyDown}
        onBlur={revertAndClose}
        required
      />
      {isOpen && (
        <ul
          id="clientId-listbox"
          role="listbox"
          style={{
            position: "absolute",
            zIndex: 10,
            top: "100%",
            left: 0,
            right: 0,
            marginTop: 4,
            maxHeight: 220,
            overflowY: "auto",
            background: "var(--color-bg-surface)",
            border: "1px solid var(--color-border-default)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-md)",
            listStyle: "none",
            padding: 4,
          }}
        >
          {filtered.length === 0 ? (
            <li className="text-tertiary text-sm" style={{ padding: "var(--space-2) var(--space-3)" }}>
              No clients match.
            </li>
          ) : (
            filtered.map((c, i) => (
              <li
                key={c.id}
                role="option"
                aria-selected={c.id === clientId}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => selectClient(c)}
                onMouseEnter={() => setHighlightedIndex(i)}
                style={{
                  padding: "var(--space-2) var(--space-3)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  background: i === highlightedIndex ? "var(--color-bg-selected)" : "transparent",
                }}
              >
                {c.name}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
