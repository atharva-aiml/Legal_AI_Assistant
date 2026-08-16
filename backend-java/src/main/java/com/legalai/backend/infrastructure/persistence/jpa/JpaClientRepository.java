package com.legalai.backend.infrastructure.persistence.jpa;

import com.legalai.backend.infrastructure.persistence.entity.ClientEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface JpaClientRepository extends JpaRepository<ClientEntity, UUID> {
    List<ClientEntity> findByFirmId(UUID firmId);

    Optional<ClientEntity> findByIdAndFirmId(UUID id, UUID firmId);

    /**
     * SD-009: Postgres full-text search over Client.name, scoped to the
     * caller's Firm (BR-008). ":q IS NULL" lets a status/date-only search
     * (Matter-only filters, but this query still runs) skip the name filter
     * entirely rather than matching nothing.
     */
    @Query(value = "SELECT * FROM clients c WHERE c.firm_id = :firmId "
            + "AND (CAST(:q AS text) IS NULL OR to_tsvector('english', c.name) @@ plainto_tsquery('english', CAST(:q AS text))) "
            + "AND (CAST(:fromTs AS timestamptz) IS NULL OR c.created_at >= CAST(:fromTs AS timestamptz)) "
            + "AND (CAST(:toTs AS timestamptz) IS NULL OR c.created_at < CAST(:toTs AS timestamptz))",
            nativeQuery = true)
    List<ClientEntity> search(@Param("firmId") UUID firmId, @Param("q") String q, @Param("fromTs") Instant fromTs, @Param("toTs") Instant toTs);
}
