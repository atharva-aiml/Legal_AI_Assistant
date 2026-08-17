package com.legalai.backend.application.auth;

import com.legalai.backend.domain.Firm;
import com.legalai.backend.domain.Lawyer;
import com.legalai.backend.domain.LawyerRole;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/** I-06: covers AuthService.isEmailAvailable against an in-memory LawyerRepository fake. */
class AuthServiceTest {

    static class InMemoryLawyerRepository implements LawyerRepository {
        final List<LawyerWithHash> lawyers = new ArrayList<>();

        @Override
        public Optional<LawyerWithHash> findByEmailWithHash(String email) {
            return lawyers.stream().filter(l -> l.lawyer().email().equals(email)).findFirst();
        }

        @Override
        public Optional<Lawyer> findById(UUID id) {
            return lawyers.stream().map(LawyerWithHash::lawyer).filter(l -> l.id().equals(id)).findFirst();
        }

        @Override
        public List<Lawyer> listByFirm(UUID firmId) {
            return lawyers.stream().map(LawyerWithHash::lawyer).filter(l -> l.firmId().equals(firmId)).toList();
        }

        @Override
        public LawyerWithHash create(UUID firmId, String name, String email, String passwordHash) {
            Lawyer lawyer = new Lawyer(UUID.randomUUID(), firmId, name, email, LawyerRole.owner, Instant.now());
            LawyerWithHash created = new LawyerWithHash(lawyer, passwordHash);
            lawyers.add(created);
            return created;
        }

        @Override
        public Firm createFirm(String name) {
            return new Firm(UUID.randomUUID(), name, Instant.now());
        }

        @Override
        public Optional<LawyerWithHash> findByIdWithHash(UUID id) {
            return lawyers.stream().filter(l -> l.lawyer().id().equals(id)).findFirst();
        }

        @Override
        public Optional<Lawyer> updateName(UUID id, String name) {
            for (int i = 0; i < lawyers.size(); i++) {
                LawyerWithHash existing = lawyers.get(i);
                if (existing.lawyer().id().equals(id)) {
                    Lawyer renamed = new Lawyer(existing.lawyer().id(), existing.lawyer().firmId(), name,
                            existing.lawyer().email(), existing.lawyer().role(), existing.lawyer().createdAt());
                    LawyerWithHash updated = new LawyerWithHash(renamed, existing.passwordHash());
                    lawyers.set(i, updated);
                    return Optional.of(renamed);
                }
            }
            return Optional.empty();
        }

        @Override
        public void updatePassword(UUID id, String newPasswordHash) {
            for (int i = 0; i < lawyers.size(); i++) {
                LawyerWithHash existing = lawyers.get(i);
                if (existing.lawyer().id().equals(id)) {
                    lawyers.set(i, new LawyerWithHash(existing.lawyer(), newPasswordHash));
                    return;
                }
            }
        }
    }

    /** Unused by isEmailAvailable — throws if AuthService ever calls it for this test's cases. */
    static class UnsupportedSessionRepository implements SessionRepository {
        @Override
        public void create(UUID lawyerId, String tokenHash, Instant expiresAt) {
            throw new UnsupportedOperationException("not needed for AuthServiceTest");
        }

        @Override
        public Optional<Lawyer> findLawyerByValidTokenHash(String tokenHash) {
            throw new UnsupportedOperationException("not needed for AuthServiceTest");
        }

        @Override
        public void deleteByTokenHash(String tokenHash) {
            throw new UnsupportedOperationException("not needed for AuthServiceTest");
        }
    }

    private InMemoryLawyerRepository lawyerRepo;
    private AuthService service;

    @BeforeEach
    void setUp() {
        lawyerRepo = new InMemoryLawyerRepository();
        service = new AuthService(lawyerRepo, new UnsupportedSessionRepository(), new PasswordHasher(), new SessionToken());
    }

    @Test
    void reportsAnUnregisteredEmailAsAvailable() {
        assertTrue(service.isEmailAvailable("nobody@example.com"));
    }

    @Test
    void reportsARegisteredEmailAsUnavailable() {
        UUID firmId = UUID.randomUUID();
        lawyerRepo.create(firmId, "Jane", "jane@example.com", "hash");

        assertFalse(service.isEmailAvailable("jane@example.com"));
    }

    @Test
    void checkIsCaseInsensitiveAndTrimmed_matchesRegisterNormalization() {
        UUID firmId = UUID.randomUUID();
        lawyerRepo.create(firmId, "Jane", "jane@example.com", "hash");

        assertFalse(service.isEmailAvailable("  Jane@Example.com  "));
    }

    @Test
    void treatsAnEmptyOrBlankEmailAsUnavailable_avoidsAFalseAvailableHint() {
        assertFalse(service.isEmailAvailable(""));
        assertFalse(service.isEmailAvailable("   "));
        assertFalse(service.isEmailAvailable(null));
    }

    // --- I-51: updateName() ---

    @Test
    void updatesAndTrimsTheLawyersName() {
        UUID firmId = UUID.randomUUID();
        LawyerRepository.LawyerWithHash created = lawyerRepo.create(firmId, "Jane", "jane@example.com", "hash");

        Lawyer updated = service.updateName(created.lawyer().id(), "  Jane Q. Public  ");

        assertEquals("Jane Q. Public", updated.name());
        assertEquals("Jane Q. Public", lawyerRepo.findById(created.lawyer().id()).orElseThrow().name());
    }

    @Test
    void rejectsABlankNewName() {
        UUID firmId = UUID.randomUUID();
        LawyerRepository.LawyerWithHash created = lawyerRepo.create(firmId, "Jane", "jane@example.com", "hash");

        assertThrows(com.legalai.backend.domain.InvalidLawyerException.class, () -> service.updateName(created.lawyer().id(), "   "));
        assertEquals("Jane", lawyerRepo.findById(created.lawyer().id()).orElseThrow().name(), "a rejected rename must not partially apply");
    }

    // --- I-51: changePassword() ---

    @Test
    void changesThePasswordWhenTheCurrentPasswordIsCorrect() {
        PasswordHasher hasher = new PasswordHasher();
        UUID firmId = UUID.randomUUID();
        LawyerRepository.LawyerWithHash created = lawyerRepo.create(firmId, "Jane", "jane@example.com", hasher.hash("oldpassword"));

        service.changePassword(created.lawyer().id(), "oldpassword", "newpassword123");

        String storedHash = lawyerRepo.findByIdWithHash(created.lawyer().id()).orElseThrow().passwordHash();
        assertTrue(hasher.matches("newpassword123", storedHash));
        assertFalse(hasher.matches("oldpassword", storedHash), "the old password must no longer work");
    }

    @Test
    void rejectsAChangeWithTheWrongCurrentPassword() {
        PasswordHasher hasher = new PasswordHasher();
        UUID firmId = UUID.randomUUID();
        LawyerRepository.LawyerWithHash created = lawyerRepo.create(firmId, "Jane", "jane@example.com", hasher.hash("oldpassword"));

        assertThrows(AuthService.IncorrectPasswordException.class,
                () -> service.changePassword(created.lawyer().id(), "wrongpassword", "newpassword123"));

        String storedHash = lawyerRepo.findByIdWithHash(created.lawyer().id()).orElseThrow().passwordHash();
        assertTrue(hasher.matches("oldpassword", storedHash), "a rejected change must not touch the stored password");
    }

    @Test
    void rejectsANewPasswordShorterThanEightCharacters() {
        PasswordHasher hasher = new PasswordHasher();
        UUID firmId = UUID.randomUUID();
        LawyerRepository.LawyerWithHash created = lawyerRepo.create(firmId, "Jane", "jane@example.com", hasher.hash("oldpassword"));

        assertThrows(com.legalai.backend.domain.InvalidLawyerException.class,
                () -> service.changePassword(created.lawyer().id(), "oldpassword", "short1"));

        String storedHash = lawyerRepo.findByIdWithHash(created.lawyer().id()).orElseThrow().passwordHash();
        assertTrue(hasher.matches("oldpassword", storedHash), "a rejected change must not touch the stored password");
    }
}
