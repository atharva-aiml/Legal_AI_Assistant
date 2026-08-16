package com.legalai.backend.application.auth;

import org.springframework.stereotype.Component;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Duration;
import java.util.HexFormat;

/**
 * Mirrors the original Node implementation exactly: a 256-bit random raw
 * token that only ever lives in the browser's cookie, and a SHA-256 hash
 * of it that's the only thing ever persisted (System Architecture §5).
 */
@Component
public class SessionToken {

    public static final String COOKIE_NAME = "session";
    public static final Duration SESSION_DURATION = Duration.ofDays(7);

    private final SecureRandom random = new SecureRandom();

    public String generateRawToken() {
        byte[] bytes = new byte[32];
        random.nextBytes(bytes);
        return HexFormat.of().formatHex(bytes);
    }

    public String hash(String rawToken) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hashed = digest.digest(rawToken.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hashed);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 must be available on every JVM", e);
        }
    }
}
