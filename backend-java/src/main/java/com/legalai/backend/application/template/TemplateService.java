package com.legalai.backend.application.template;

import com.legalai.backend.domain.Template;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class TemplateService {

    private final TemplateRepository repository;

    public TemplateService(TemplateRepository repository) {
        this.repository = repository;
    }

    public List<Template> list(UUID firmId) {
        return repository.listAvailable(firmId);
    }

    public Optional<Template> get(UUID firmId, UUID id) {
        return repository.findAvailable(firmId, id);
    }
}
