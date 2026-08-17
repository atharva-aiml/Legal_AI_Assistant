package com.legalai.backend.application.auth;

import com.legalai.backend.domain.Firm;
import com.legalai.backend.domain.Lawyer;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

@Service
public class AuthService {

    private final LawyerRepository lawyers;
    private final SessionRepository sessions;
    private final PasswordHasher passwordHasher;
    private final SessionToken sessionToken;

    public AuthService(LawyerRepository lawyers, SessionRepository sessions, PasswordHasher passwordHasher, SessionToken sessionToken) {
        this.lawyers = lawyers;
        this.sessions = sessions;
        this.passwordHasher = passwordHasher;
        this.sessionToken = sessionToken;
    }

    public static class ValidationException extends RuntimeException {
        public ValidationException(String message) {
            super(message);
        }
    }

    public static class EmailTakenException extends RuntimeException {
        public EmailTakenException(String message) {
            super(message);
        }
    }

    public record AuthResult(Lawyer lawyer, String rawSessionToken) {
    }

    /** Creates a new Firm + Lawyer (role=owner) in one flow — mirrors POST /api/auth/register. */
    public AuthResult register(String name, String email, String password) {
        String trimmedName = name == null ? "" : name.trim();
        String normalizedEmail = email == null ? "" : email.trim().toLowerCase();

        if (trimmedName.isEmpty() || normalizedEmail.isEmpty() || password == null || password.length() < 8) {
            throw new ValidationException("Name, email, and an 8+ character password are required.");
        }

        if (lawyers.findByEmailWithHash(normalizedEmail).isPresent()) {
            throw new EmailTakenException("An account with this email already exists.");
        }

        String passwordHash = passwordHasher.hash(password);
        Firm firm = lawyers.createFirm(trimmedName + "'s Firm");
        LawyerRepository.LawyerWithHash created = lawyers.create(firm.id(), trimmedName, normalizedEmail, passwordHash);

        return new AuthResult(created.lawyer(), issueSession(created.lawyer().id()));
    }

    /** I-06: reuses the same uniqueness check `register` runs, read-only, for a live pre-submit hint. */
    public boolean isEmailAvailable(String email) {
        String normalizedEmail = email == null ? "" : email.trim().toLowerCase();
        if (normalizedEmail.isEmpty()) return false;
        return lawyers.findByEmailWithHash(normalizedEmail).isEmpty();
    }

    /** Mirrors POST /api/auth/login — identical error for "no such email" and "wrong password". */
    public AuthResult login(String email, String password) {
        String normalizedEmail = email == null ? "" : email.trim().toLowerCase();

        Optional<LawyerRepository.LawyerWithHash> found = normalizedEmail.isEmpty()
                ? Optional.empty()
                : lawyers.findByEmailWithHash(normalizedEmail);

        if (found.isEmpty() || password == null || !passwordHasher.matches(password, found.get().passwordHash())) {
            throw new InvalidCredentialsException();
        }

        Lawyer lawyer = found.get().lawyer();
        return new AuthResult(lawyer, issueSession(lawyer.id()));
    }

    public static class InvalidCredentialsException extends RuntimeException {
        public InvalidCredentialsException() {
            super("Incorrect email or password.");
        }
    }

    /** Mirrors POST /api/auth/logout — deletes the Session row, real revocation not just a cleared cookie. */
    public void logout(String rawSessionToken) {
        if (rawSessionToken == null || rawSessionToken.isEmpty()) return;
        sessions.deleteByTokenHash(sessionToken.hash(rawSessionToken));
    }

    /** The real per-request authorization check — System Architecture §5, steps 6-8. */
    public Optional<Lawyer> resolveSession(String rawSessionToken) {
        if (rawSessionToken == null || rawSessionToken.isEmpty()) return Optional.empty();
        return sessions.findLawyerByValidTokenHash(sessionToken.hash(rawSessionToken));
    }

    /** SCR-15: read-only Firm/team roster — invite/remove is V0.7, not built yet. */
    public java.util.List<Lawyer> listFirmMembers(java.util.UUID firmId) {
        return lawyers.listByFirm(firmId);
    }

    /** I-51: PATCH /api/auth/me — the display name shown across the nav bar and account menu. */
    public Lawyer updateName(UUID lawyerId, String name) {
        String validated = Lawyer.validateName(name);
        return lawyers.updateName(lawyerId, validated)
                .orElseThrow(() -> new IllegalStateException("Lawyer " + lawyerId + " not found for an already-authenticated session."));
    }

    /** I-51: requires re-verifying the current password before a new one is ever hashed and stored. */
    public void changePassword(UUID lawyerId, String currentPassword, String newPassword) {
        LawyerRepository.LawyerWithHash found = lawyers.findByIdWithHash(lawyerId)
                .orElseThrow(() -> new IllegalStateException("Lawyer " + lawyerId + " not found for an already-authenticated session."));

        if (currentPassword == null || !passwordHasher.matches(currentPassword, found.passwordHash())) {
            throw new IncorrectPasswordException();
        }

        String validatedNewPassword = Lawyer.validateNewPassword(newPassword);
        lawyers.updatePassword(lawyerId, passwordHasher.hash(validatedNewPassword));
    }

    public static class IncorrectPasswordException extends RuntimeException {
        public IncorrectPasswordException() {
            super("Current password is incorrect.");
        }
    }

    private String issueSession(java.util.UUID lawyerId) {
        String raw = sessionToken.generateRawToken();
        Instant expiresAt = Instant.now().plus(SessionToken.SESSION_DURATION);
        sessions.create(lawyerId, sessionToken.hash(raw), expiresAt);
        return raw;
    }
}
