package com.legalai.backend.application.auth;

import com.legalai.backend.domain.Firm;
import com.legalai.backend.domain.Lawyer;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface LawyerRepository {
    /** Includes the password hash — the only place it's ever read back out, for login verification. */
    Optional<LawyerWithHash> findByEmailWithHash(String email);

    Optional<Lawyer> findById(UUID id);

    /** I-51: includes the password hash, keyed by id instead of email — the current-password re-verification step needs it. */
    Optional<LawyerWithHash> findByIdWithHash(UUID id);

    /** SD-006: every Lawyer who should receive Deadline-reminder Notifications for a Firm's Matters (REQ-014's sharing model). */
    List<Lawyer> listByFirm(UUID firmId);

    LawyerWithHash create(UUID firmId, String name, String email, String passwordHash);

    Firm createFirm(String name);

    /** I-51 */
    Optional<Lawyer> updateName(UUID id, String name);

    /** I-51 */
    void updatePassword(UUID id, String newPasswordHash);

    record LawyerWithHash(Lawyer lawyer, String passwordHash) {
    }
}
