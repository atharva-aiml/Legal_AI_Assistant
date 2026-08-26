package com.legalai.backend.infrastructure.persistence.jpa;

import com.legalai.backend.domain.DeadlineStatus;
import com.legalai.backend.infrastructure.persistence.entity.DeadlineEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface JpaDeadlineRepository extends JpaRepository<DeadlineEntity, UUID> {

    // Deadline has no firm_id column of its own (only matter_id) — BR-008
    // isolation via a subquery join to matters, same pattern as Document.
    @Query("SELECT d FROM DeadlineEntity d WHERE d.matterId = :matterId " +
            "AND d.matterId IN (SELECT m.id FROM MatterEntity m WHERE m.firmId = :firmId) " +
            "ORDER BY d.dueDate ASC")
    List<DeadlineEntity> findByMatterIdAndFirmId(@Param("matterId") UUID matterId, @Param("firmId") UUID firmId);

    @Query("SELECT d FROM DeadlineEntity d WHERE d.id = :id " +
            "AND d.matterId IN (SELECT m.id FROM MatterEntity m WHERE m.firmId = :firmId)")
    Optional<DeadlineEntity> findByIdAndFirmId(@Param("id") UUID id, @Param("firmId") UUID firmId);

    /** REQ-017: Dashboard Upcoming widget. */
    @Query("SELECT d FROM DeadlineEntity d WHERE d.status = :status AND d.dueDate <= :cutoff " +
            "AND d.matterId IN (SELECT m.id FROM MatterEntity m WHERE m.firmId = :firmId) " +
            "ORDER BY d.dueDate ASC")
    List<DeadlineEntity> findUpcoming(@Param("firmId") UUID firmId, @Param("status") DeadlineStatus status, @Param("cutoff") LocalDate cutoff);

    /** SD-006 scanner only — deliberately unscoped by firm. */
    List<DeadlineEntity> findByStatus(DeadlineStatus status);

    /** Spring Data derived delete query — cascade-delete cleanup only, see DeadlineRepository.deleteByMatter. */
    void deleteByMatterId(UUID matterId);
}
