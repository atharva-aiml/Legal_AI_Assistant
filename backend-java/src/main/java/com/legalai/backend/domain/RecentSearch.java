package com.legalai.backend.domain;

import java.time.Instant;
import java.util.UUID;

/**
 * I-48: a lightweight fact — "this Lawyer ran this query at this time" —
 * mirroring MatterView's shape, upserted one row per (lawyerId, query).
 * Unlike MatterView, there is one real invariant worth enforcing before a
 * search is ever recorded: a blank query isn't worth remembering.
 */
public record RecentSearch(UUID lawyerId, String query, Instant searchedAt) {

    public static String validateQuery(String query) {
        String trimmed = query == null ? "" : query.trim();
        if (trimmed.isEmpty()) {
            throw new InvalidSearchException("A recent search needs a non-empty query.");
        }
        return trimmed;
    }
}
