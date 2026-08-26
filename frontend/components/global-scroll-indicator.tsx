"use client";

import { useEffect } from "react";

const RESET_MS = 500;

/**
 * The single source of "show the scrollbar only while actively scrolling,
 * fade it out ~500ms after the last scroll event" for every scrollable
 * element on every screen (paired with globals.css's `.is-scrolling` rules).
 * Scroll events don't bubble, so a per-component onScroll handler would need
 * wiring into every scrollable container individually — this instead listens
 * once, in the capture phase, at the document level, and tags whichever
 * element actually scrolled.
 */
export function GlobalScrollIndicator() {
  useEffect(() => {
    const timeouts = new WeakMap<Element, ReturnType<typeof setTimeout>>();

    function onScroll(e: Event) {
      const target = e.target === document ? document.documentElement : e.target;
      if (!(target instanceof Element)) return;

      target.classList.add("is-scrolling");
      const existing = timeouts.get(target);
      if (existing) clearTimeout(existing);
      timeouts.set(
        target,
        setTimeout(() => target.classList.remove("is-scrolling"), RESET_MS)
      );
    }

    document.addEventListener("scroll", onScroll, { capture: true, passive: true });
    return () => document.removeEventListener("scroll", onScroll, { capture: true });
  }, []);

  return null;
}
