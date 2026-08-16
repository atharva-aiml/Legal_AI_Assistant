package com.legalai.backend.domain;

import java.time.Instant;
import java.util.UUID;

public record Matter(
        UUID id,
        UUID firmId,
        UUID clientId,
        String title,
        MatterStatus status,
        Instant closedAt,
        Instant createdAt,
        Instant updatedAt) {

    public record NewMatter(UUID firmId, UUID clientId, String title, MatterStatus status) {
    }

    /**
     * BR-001: a Matter must belong to exactly one Client. Enforced here as
     * "clientId is required" — the domain-layer half of the invariant; the
     * real repository's FK constraint is the storage-layer half.
     * A new Matter always starts "open" (BR-003's closing rules don't apply
     * until Build Plan V0.5).
     */
    public static NewMatter create(UUID firmId, UUID clientId, String title) {
        String trimmed = title == null ? "" : title.trim();
        if (trimmed.isEmpty()) {
            throw new InvalidMatterException("Matter title is required.");
        }
        if (clientId == null) {
            throw new InvalidMatterException("A Matter must belong to a Client (BR-001).");
        }
        if (firmId == null) {
            throw new InvalidMatterException("A Matter must belong to a Firm (BR-008).");
        }
        return new NewMatter(firmId, clientId, trimmed, MatterStatus.open);
    }

    /** Renaming keeps the same "non-empty title" invariant as creation. */
    public static String renameTitle(String title) {
        String trimmed = title == null ? "" : title.trim();
        if (trimmed.isEmpty()) {
            throw new InvalidMatterException("Matter title is required.");
        }
        return trimmed;
    }
}
