package com.legalai.backend.infrastructure.persistence.jpa;

import com.legalai.backend.infrastructure.persistence.entity.NotificationEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface JpaNotificationRepository extends JpaRepository<NotificationEntity, UUID> {

    List<NotificationEntity> findByLawyerIdOrderByCreatedAtDesc(UUID lawyerId);

    Optional<NotificationEntity> findByIdAndLawyerId(UUID id, UUID lawyerId);

    /** I-44: a single bulk UPDATE, not a fetch-then-save-each-row loop — only ever touches this Lawyer's still-unread rows. */
    @Modifying
    @Query("UPDATE NotificationEntity n SET n.readAt = :now WHERE n.lawyerId = :lawyerId AND n.readAt IS NULL")
    int markAllReadForLawyer(@Param("lawyerId") UUID lawyerId, @Param("now") Instant now);

    // Deliberately not a DB-side date CAST — Postgres's ::date cast depends
    // on the session TimeZone setting, which is a real, already-documented
    // source of bugs on this machine (CLAUDE.md §4). The "same day" check
    // is done in Java instead (NotificationRepositoryImpl), against a
    // small, bounded result set (at most a handful of rows per pair).
    List<NotificationEntity> findByDeadlineIdAndLawyerId(UUID deadlineId, UUID lawyerId);
}
