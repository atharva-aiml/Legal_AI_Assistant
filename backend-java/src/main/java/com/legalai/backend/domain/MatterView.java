package com.legalai.backend.domain;

import java.time.Instant;
import java.util.UUID;

/**
 * I-07: a lightweight fact — "this Lawyer had this Matter open at this
 * time" — not an invariant-bearing entity. No static factory/validation
 * here because there's no business rule to enforce: lawyerId/matterId
 * are always real, already-authorized IDs by the time a view is ever
 * recorded (the controller resolves both first), so there's nothing a
 * domain test would meaningfully cover. The one behavior worth testing —
 * that re-viewing a Matter moves it to the top without duplicating it —
 * is a repository/ordering concern, covered at the application layer
 * (MatterViewServiceTest) instead.
 */
public record MatterView(UUID lawyerId, UUID matterId, Instant viewedAt) {
}
