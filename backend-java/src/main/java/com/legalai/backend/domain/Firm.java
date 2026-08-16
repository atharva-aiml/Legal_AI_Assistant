package com.legalai.backend.domain;

import java.time.Instant;
import java.util.UUID;

public record Firm(UUID id, String name, Instant createdAt) {
}
