package com.legalai.backend.application.template;

import com.legalai.backend.domain.Template;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * SD-007. "Available" means visible to a Firm: every system Template
 * (firm_id null) plus that Firm's own custom ones — never another Firm's
 * custom Templates (BR-008's spirit, applied to a nullable-tenant table).
 */
public interface TemplateRepository {
    List<Template> listAvailable(UUID firmId);

    Optional<Template> findAvailable(UUID firmId, UUID id);
}
