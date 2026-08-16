package com.legalai.backend.infrastructure.persistence.jpa;

import com.legalai.backend.infrastructure.persistence.entity.DocumentEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface JpaDocumentRepository extends JpaRepository<DocumentEntity, UUID> {

    // Document has no firm_id column of its own (only matter_id) — BR-008
    // isolation is enforced here via a subquery join to matters, same
    // invariant as everywhere else, just expressed at the SQL/JPQL level
    // instead of a direct column comparison.
    @Query("SELECT d FROM DocumentEntity d WHERE d.matterId = :matterId " +
            "AND d.matterId IN (SELECT m.id FROM MatterEntity m WHERE m.firmId = :firmId)")
    List<DocumentEntity> findByMatterIdAndFirmId(@Param("matterId") UUID matterId, @Param("firmId") UUID firmId);

    @Query("SELECT d FROM DocumentEntity d WHERE d.id = :id " +
            "AND d.matterId IN (SELECT m.id FROM MatterEntity m WHERE m.firmId = :firmId)")
    Optional<DocumentEntity> findByIdAndFirmId(@Param("id") UUID id, @Param("firmId") UUID firmId);
}
