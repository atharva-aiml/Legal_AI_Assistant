package com.legalai.backend.domain;

import java.time.Instant;
import java.util.UUID;

/** Never carries passwordHash — that stays inside the auth infrastructure layer. */
public record Lawyer(UUID id, UUID firmId, String name, String email, LawyerRole role, Instant createdAt) {
}
