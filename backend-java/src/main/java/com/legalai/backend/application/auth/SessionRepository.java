package com.legalai.backend.application.auth;

import com.legalai.backend.domain.Lawyer;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

public interface SessionRepository {
    void create(UUID lawyerId, String tokenHash, Instant expiresAt);

    /** Only returns the Lawyer if a matching, unexpired Session row exists — the real per-request check. */
    Optional<Lawyer> findLawyerByValidTokenHash(String tokenHash);

    void deleteByTokenHash(String tokenHash);
}
