package com.legalai.backend.infrastructure.persistence;

import com.legalai.backend.application.template.TemplateRepository;
import com.legalai.backend.domain.Template;
import com.legalai.backend.infrastructure.persistence.entity.TemplateEntity;
import com.legalai.backend.infrastructure.persistence.jpa.JpaTemplateRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** Real TemplateRepository, backed by Postgres via Spring Data JPA. */
@Repository
public class TemplateRepositoryImpl implements TemplateRepository {

    private final JpaTemplateRepository jpa;

    public TemplateRepositoryImpl(JpaTemplateRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public List<Template> listAvailable(UUID firmId) {
        return jpa.findAvailable(firmId).stream().map(TemplateRepositoryImpl::toDomain).toList();
    }

    @Override
    public Optional<Template> findAvailable(UUID firmId, UUID id) {
        return jpa.findAvailableById(id, firmId).map(TemplateRepositoryImpl::toDomain);
    }

    private static Template toDomain(TemplateEntity e) {
        return new Template(e.getId(), e.getFirmId(), e.getName(), e.getDescription(), e.getBody(), e.getCreatedAt());
    }
}
