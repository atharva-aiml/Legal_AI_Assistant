package com.legalai.backend.infrastructure.persistence.jpa;

import com.legalai.backend.infrastructure.persistence.entity.RecentSearchEntity;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.UUID;

public interface JpaRecentSearchRepository extends JpaRepository<RecentSearchEntity, UUID> {

    /**
     * One row per (lawyer_id, query) — the unique index added by I-48's
     * migration lets Postgres do the "insert, or bump the timestamp if it's
     * already there" dance atomically, rather than a
     * read-then-decide-insert-or-update round trip from the application.
     */
    @Modifying
    @Query(value = "INSERT INTO recent_searches (lawyer_id, query, searched_at) VALUES (:lawyerId, :query, now()) "
            + "ON CONFLICT (lawyer_id, query) DO UPDATE SET searched_at = now()",
            nativeQuery = true)
    void upsertSearch(@Param("lawyerId") UUID lawyerId, @Param("query") String query);

    List<RecentSearchEntity> findByLawyerIdOrderBySearchedAtDesc(UUID lawyerId, Pageable pageable);
}
