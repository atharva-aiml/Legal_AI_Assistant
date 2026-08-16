package com.legalai.backend.infrastructure.persistence.jpa;

import com.legalai.backend.infrastructure.persistence.entity.TemplateEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface JpaTemplateRepository extends JpaRepository<TemplateEntity, UUID> {

    /** SD-007: system Templates (firm_id null) plus this Firm's own custom ones. */
    @Query("SELECT t FROM TemplateEntity t WHERE t.firmId IS NULL OR t.firmId = :firmId ORDER BY t.name")
    List<TemplateEntity> findAvailable(@Param("firmId") UUID firmId);

    @Query("SELECT t FROM TemplateEntity t WHERE t.id = :id AND (t.firmId IS NULL OR t.firmId = :firmId)")
    Optional<TemplateEntity> findAvailableById(@Param("id") UUID id, @Param("firmId") UUID firmId);
}
