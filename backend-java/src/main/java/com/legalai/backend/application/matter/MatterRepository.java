package com.legalai.backend.application.matter;

import com.legalai.backend.domain.Matter;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Port the application layer depends on — the real implementation
 * (Spring Data JPA/Postgres) and any test fake both satisfy this same
 * contract, so MatterService never knows which one it's talking to.
 */
public interface MatterRepository {
    Matter create(Matter.NewMatter record);

    List<Matter> listByFirm(UUID firmId);

    List<Matter> listByClient(UUID firmId, UUID clientId);

    Optional<Matter> findById(UUID firmId, UUID id);

    Optional<Matter> updateTitle(UUID firmId, UUID id, String title);

    /** REQ-010: sets status='closed' and closed_at=now(). Caller (MatterService) has already verified BR-003. */
    Optional<Matter> close(UUID firmId, UUID id);
}
