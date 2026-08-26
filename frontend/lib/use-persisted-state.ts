"use client";
import { useEffect, useState } from "react";

/** Like useState, but the value survives navigating away and back within the
 * same tab (sessionStorage-backed) — Next.js unmounts client components on
 * every route change, so plain useState loses selection/filter/sort state
 * the instant you leave a screen. `key` must be unique app-wide (namespace
 * it per screen, e.g. "clients:selectedId"). SSR-safe: renders `defaultValue`
 * on first paint (sessionStorage isn't available server-side), then syncs
 * from storage in an effect — expect a possible one-frame flash of the
 * default value on mount, that's an accepted tradeoff, not a bug to fix. */
export function usePersistedState<T>(key: string, defaultValue: T): [T, (value: T) => void] {
  const [state, setState] = useState<T>(defaultValue);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(key);
      if (raw !== null) setState(JSON.parse(raw));
    } catch {
      // sessionStorage can throw (private browsing, disabled storage) — fall back to defaultValue silently.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  function update(value: T) {
    setState(value);
    try {
      sessionStorage.setItem(key, JSON.stringify(value));
    } catch {}
  }

  return [state, update];
}
