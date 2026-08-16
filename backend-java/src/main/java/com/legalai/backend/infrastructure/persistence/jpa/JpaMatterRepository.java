package com.legalai.backend.infrastructure.persistence.jpa;

import com.legalai.backend.infrastructure.persistence.entity.MatterEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface JpaMatterRepository extends JpaRepository<MatterEntity, UUID> {
    List<MatterEntity> findByFirmId(UUID firmId);

    List<MatterEntity> findByFirmIdAndClientId(UUID firmId, UUID clientId);

    Optional<MatterEntity> findByIdAndFirmId(UUID id, UUID firmId);

    /**
     * SD-009: Postgres full-text search over Matter.title, scoped to the
     * caller's Firm (BR-008). No status filter here means "any status" —
     * Closed Matters are never excluded by default (BR-007); the status
     * filter is opt-in narrowing, not an opt-out exclusion. Status is
     * compared as text (":status::text") to sidestep binding a plain String
     * parameter against Postgres's native matter_status enum column.
     */
    @Query(value = "SELECT * FROM matters m WHERE m.firm_id = :firmId "
            + "AND (CAST(:q AS text) IS NULL OR to_tsvector('english', m.title) @@ plainto_tsquery('english', CAST(:q AS text))) "
            + "AND (CAST(:status AS text) IS NULL OR m.status::text = CAST(:status AS text)) "
            + "AND (CAST(:fromTs AS timestamptz) IS NULL OR m.created_at >= CAST(:fromTs AS timestamptz)) "
            + "AND (CAST(:toTs AS timestamptz) IS NULL OR m.created_at < CAST(:toTs AS timestamptz))",
            nativeQuery = true)
    List<MatterEntity> search(@Param("firmId") UUID firmId, @Param("q") String q, @Param("status") String status,
                               @Param("fromTs") Instant fromTs, @Param("toTs") Instant toTs);
}
