package com.legalai.backend.domain;

import java.time.Instant;
import java.util.UUID;

public record Client(
        UUID id,
        UUID firmId,
        String name,
        String contactEmail,
        String contactPhone,
        String notes,
        Instant createdAt,
        Instant updatedAt) {

    public record NewClient(UUID firmId, String name, String contactEmail, String contactPhone, String notes) {
    }

    /** BR-008: every tenant-owned row carries firm_id — enforced here as "firmId is required". */
    public static NewClient create(UUID firmId, String name, String contactEmail, String contactPhone, String notes) {
        String trimmed = name == null ? "" : name.trim();
        if (trimmed.isEmpty()) {
            throw new InvalidClientException("Name is required");
        }
        if (firmId == null) {
            throw new InvalidClientException("A Client must belong to a Firm (BR-008).");
        }
        return new NewClient(firmId, trimmed, blankToNull(contactEmail), blankToNull(contactPhone), blankToNull(notes));
    }

    private static String blankToNull(String value) {
        return (value == null || value.isBlank()) ? null : value;
    }
}
