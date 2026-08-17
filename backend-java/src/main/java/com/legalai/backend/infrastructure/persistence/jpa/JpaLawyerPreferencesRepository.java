package com.legalai.backend.infrastructure.persistence.jpa;

import com.legalai.backend.infrastructure.persistence.entity.LawyerPreferencesEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;
import java.util.UUID;

public interface JpaLawyerPreferencesRepository extends JpaRepository<LawyerPreferencesEntity, UUID> {

    Optional<LawyerPreferencesEntity> findByLawyerId(UUID lawyerId);

    /** One row per lawyer_id (I-52's unique index) — same atomic upsert shape as matter_views/recent_searches. */
    @Modifying
    @Query(value = "INSERT INTO lawyer_preferences (lawyer_id, deadline_reminders_enabled, updated_at) "
            + "VALUES (:lawyerId, :enabled, now()) "
            + "ON CONFLICT (lawyer_id) DO UPDATE SET deadline_reminders_enabled = :enabled, updated_at = now()",
            nativeQuery = true)
    void upsertPreferences(@Param("lawyerId") UUID lawyerId, @Param("enabled") boolean enabled);
}
