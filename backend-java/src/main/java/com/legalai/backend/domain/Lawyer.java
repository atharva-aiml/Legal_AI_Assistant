package com.legalai.backend.domain;

import java.time.Instant;
import java.util.UUID;

/** Never carries passwordHash — that stays inside the auth infrastructure layer. */
public record Lawyer(UUID id, UUID firmId, String name, String email, LawyerRole role, Instant createdAt) {

    /** I-51: same "name is required" invariant as registration — editing can't leave a Lawyer nameless either. */
    public static String validateName(String name) {
        String trimmed = name == null ? "" : name.trim();
        if (trimmed.isEmpty()) {
            throw new InvalidLawyerException("Name is required.");
        }
        return trimmed;
    }

    /** I-51: same 8+ character minimum AuthService.register enforces for a new account's password. */
    public static String validateNewPassword(String newPassword) {
        if (newPassword == null || newPassword.length() < 8) {
            throw new InvalidLawyerException("A new password must be at least 8 characters.");
        }
        return newPassword;
    }
}
