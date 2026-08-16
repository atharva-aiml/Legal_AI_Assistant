package com.legalai.backend.domain;

import java.time.LocalDate;

/**
 * REQ-011: "Lawyer can search/filter Clients and Matters by name, status,
 * and date." A search always runs within the caller's Firm (BR-008,
 * enforced by the application layer, not here) and never excludes Closed
 * Matters (BR-007) — this object only validates *what* was asked for, not
 * who's asking or which statuses are allowed through.
 */
public record SearchQuery(String q, MatterStatus status, LocalDate from, LocalDate to) {

    /**
     * Parses and validates raw (possibly null/blank) request input into a
     * SearchQuery. At least one real criterion is required — an entirely
     * empty search isn't a meaningful request, it's a missing one.
     */
    public static SearchQuery parse(String rawQ, String rawStatus, LocalDate from, LocalDate to) {
        String q = rawQ == null ? null : rawQ.trim();
        if (q != null && q.isEmpty()) {
            q = null;
        }

        MatterStatus status = null;
        if (rawStatus != null && !rawStatus.isBlank()) {
            try {
                status = MatterStatus.valueOf(rawStatus.trim());
            } catch (IllegalArgumentException e) {
                throw new InvalidSearchException("Unknown status: '" + rawStatus + "' — expected 'open' or 'closed'.");
            }
        }

        if (q == null && status == null && from == null && to == null) {
            throw new InvalidSearchException("A search needs at least a query, a status, or a date range (REQ-011).");
        }

        if (from != null && to != null && from.isAfter(to)) {
            throw new InvalidSearchException("The date range's start can't be after its end.");
        }

        return new SearchQuery(q, status, from, to);
    }
}
