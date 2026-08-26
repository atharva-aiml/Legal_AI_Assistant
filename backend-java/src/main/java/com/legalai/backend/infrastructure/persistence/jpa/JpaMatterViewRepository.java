package com.legalai.backend.infrastructure.persistence.jpa;

import com.legalai.backend.infrastructure.persistence.entity.MatterViewEntity;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.UUID;

public interface JpaMatterViewRepository extends JpaRepository<MatterViewEntity, UUID> {

    /**
     * One row per (lawyer_id, matter_id) — the unique index added by I-07's
     * migration lets Postgres do the "insert, or bump the timestamp if it's
     * already there" dance atomically, rather than a
     * read-then-decide-insert-or-update round trip from the application.
     */
    @Modifying
    @Query(value = "INSERT INTO matter_views (lawyer_id, matter_id, viewed_at) VALUES (:lawyerId, :matterId, now()) "
            + "ON CONFLICT (lawyer_id, matter_id) DO UPDATE SET viewed_at = now()",
            nativeQuery = true)
    void upsertView(@Param("lawyerId") UUID lawyerId, @Param("matterId") UUID matterId);

    List<MatterViewEntity> findByLawyerIdOrderByViewedAtDesc(UUID lawyerId, Pageable pageable);

    /** Spring Data derived delete query — cascade-delete cleanup only, see MatterViewRepository.deleteByMatter. */
    void deleteByMatterId(UUID matterId);
}
