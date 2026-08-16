package com.legalai.backend.application.auth;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Component;

/**
 * Cost 12, cross-verified compatible with the pre-existing Node-`bcrypt`
 * hashes via a real spike against live data (Technology Decision Log) —
 * existing lawyers' passwords keep working after this backend swap.
 */
@Component
public class PasswordHasher {

    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder(12);

    public String hash(String rawPassword) {
        return encoder.encode(rawPassword);
    }

    public boolean matches(String rawPassword, String hash) {
        return encoder.matches(rawPassword, hash);
    }
}
