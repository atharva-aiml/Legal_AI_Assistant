"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

type ListSearchContextValue = {
  query: string;
  setQuery: (query: string) => void;
};

const ListSearchContext = createContext<ListSearchContextValue | null>(null);

/**
 * The one channel connecting the topbar search bar (in NavBar) to a page's
 * own list (e.g. ClientsList) when the bar is acting as an in-list filter
 * instead of the global cross-entity search. Needed because NavBar and the
 * page's list are siblings, not ancestor/descendant, in every page that
 * renders <NavBar/> itself — so the shared state has to live above both,
 * at the root layout.
 */
export function ListSearchProvider({ children }: { children: ReactNode }) {
  const [query, setQuery] = useState("");
  return <ListSearchContext.Provider value={{ query, setQuery }}>{children}</ListSearchContext.Provider>;
}

export function useListSearch(): ListSearchContextValue {
  const ctx = useContext(ListSearchContext);
  if (!ctx) throw new Error("useListSearch must be used within a ListSearchProvider");
  return ctx;
}
